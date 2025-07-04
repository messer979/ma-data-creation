from celery import Celery
import concurrent.futures
import sqlite3
import pandas as pd
import math
import requests
import os
import re
import time
from copy import deepcopy
import json
from datetime import datetime
# from pymawm import ActiveWM
from scripts.inventory_transfer import write_inv, write_log
import threading
import queue
from scripts.inventory_transfer_sync import run_transfer_sync  # Import the standalone sync function

celery = Celery(
    'data_import',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

INV_SEARCH_EP = '/dcinventory/api/dcinventory/inventory/inventorysearch'
ITEM_SEARCH_EP = '/item-master/api/item-master/item/search'
ITEM_BULK_EP = '/item-master/api/item-master/item/bulkImport'
ADJUST_EP = '/dcinventory/api/dcinventory/inventory/adjustAbsoluteQuantity'
ITEM_SYNC_EP = '/item-master/api/item-master/item/v2/search'

def db_writer(db_queue, db_name, db_write_done):
    while True:
        item = db_queue.get()
        if item is None:
            break  # Sentinel value to stop the thread
        batch_data, filter_type = item
        time.sleep(1)  # delay before each write to ensure the previous is done 
        write_inv(db_name, f"inventory_transfer_{filter_type}", batch_data)
        db_queue.task_done()
    db_write_done.set()


def upload_inv_batch(to_url, to_headers, log_file, data, batch_start, batch_end, filter_value):
    try:
        res = requests.post(to_url + ADJUST_EP, headers=to_headers, json=data)
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Uploaded batch {batch_start}-{batch_end} for {filter_value}",
            "response_status": res.status_code,
            "response": res.json(),
        })
    except (requests.exceptions.SSLError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        time.sleep(20)
        # Optionally, you could retry here or log a failure

# Download and process items in batches
def download_and_import_item_batch(from_url, from_headers, to_url, to_headers, log_file, item_batches, item_query, batch_num):
    data = {"query": f"ItemId in ({','.join(item_query)})", "size": 50}
    res = requests.post(from_url + ITEM_SEARCH_EP, headers=from_headers, json=data)
    data = res.json()['data']
    res_save = requests.post(to_url + ITEM_BULK_EP, headers=to_headers, json={"data":data})
    write_log(log_file, {
        "timestamp": datetime.now().isoformat(),
        "status": "RUNNING",
        "message": f"Transferred item batch {batch_num+1}/{item_batches}.\nSearch: {res.status_code}, BulkImport: {res_save.status_code}",
        "response_status": res.status_code,
        "response": None,
    })
    return True

def request_failed(res, log_file):
    if res.status_code != 200:
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "FAILED",
            "message": f"Request failed with status {res.status_code}",
            "response_status": res.status_code,
            "response": res.json(),
        })
        return True
    else:
        return False


@celery.task(bind=True)
def run_transfer_task(self, config, log_file):
    log_lines = []
    db_name = log_file.replace('.json', '.db') 
    try:
        # Validate configuration        
        # Extract configuration
        filter_type = config['filter_type']
        filter_value = config['filter_value']
        download_batch_size = int(config['download_batch_size'])
        upload_batch_size = int(config['upload_batch_size'])
        
        from_env = config['from_env']
        from_org = config['from_org']
        from_facility = config['from_facility']
        from_token = config['from_token']
        
        to_env = config['to_env']
        to_org = config['to_org']
        to_facility = config['to_facility']
        to_token = config['to_token']
        
        # Production check
        if to_env.endswith('p'):
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "FAILED",
                "message": "You cannot import to a production environment!",
                "response_status": None,
                "response": None,
            })
            return False

        # Setup environments
        from_url = f"https://{from_env}.sce.manh.com"
        # active_from = ActiveWM(environment = from_environment, default_org=from_org, default_facility=from_facility, manual_token=from_token)
        from_headers = {
            "SelectedOrganization": from_org,
            "SelectedLocation": from_facility,
            "Authorization": f"Bearer {from_token}",
        }
                
        to_url = f"https://{to_env}.sce.manh.com"
        # active_to = ActiveWM(environment = to_environment, default_org=to_org, default_facility=to_facility, manual_token=to_token)
        to_headers = {
            "SelectedOrganization": to_org,
            "SelectedLocation": to_facility,
            "Authorization": f"Bearer {from_token}",
        }
        self.update_state(state='PROGRESS')
        
        # Download inventory data
        data = {
            "LocationQuery": {"Query": f"{filter_type} ={filter_value} and InventoryReservationTypeId=LOCATION"},
            "Size": 1
        }
        res = requests.post(from_url + INV_SEARCH_EP, headers=from_headers, json=data)
        if request_failed(res, log_file):
            return False

        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Initial inventory search for {filter_type}: {filter_value} returned {len(res.json()['data'])} records.",
            "response_status": res.status_code,
            "response": res.json(),
        })
        total = res.json()['header']['totalCount']
        number_of_batches = math.ceil(int(total) / download_batch_size)
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Total batches to download: {number_of_batches}",
            "response_status": None,
            "response": None,
        })
        # Download in batches with async API and sync DB write
        db_queue = queue.Queue()
        db_write_done = threading.Event()
        db_thread = threading.Thread(target=db_writer, args=(db_queue, db_name, db_write_done))
        db_thread.start()

        for i in range(number_of_batches):
            data = {
                "LocationQuery": {"Query": f"{filter_type} ={filter_value} and InventoryReservationTypeId=LOCATION"},
                "Size": download_batch_size,
                "Page": i
            }
            res = requests.post(from_url + INV_SEARCH_EP, headers=from_headers, json=data)
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Downloading batch {i+1}/{number_of_batches} for {filter_type} {filter_value}",
                "response_status": res.status_code,
                "response": res.json(),
            })
            db_queue.put((res.data, zone))  # Queue the data for DB write
            # No need to wait for DB write to finish before next API call
        db_queue.put(None)  # Sentinel value to stop the thread
        db_thread.join()
        
        # Download and sync items
        conn = sqlite3.connect(db_name)
        df = pd.read_sql_query(f"select distinct ItemId from inventory_transfer_{zone}", conn)
        conn.close()
        items = list(df.ItemId)
        
        total_items = len(items)
        item_batches = math.ceil(total_items / 50)
        

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(item_batches):
                item_query = items[50*i:50*(i+1)]
                futures.append(executor.submit(download_and_import_item_batch, from_url, from_headers, to_url, to_headers, log_file, item_batches, item_query, i))
            for future in concurrent.futures.as_completed(futures):
                pass  # Optionally handle exceptions/results

        # Sync items
        
        res = requests.post(to_url + ITEM_SYNC_EP, headers=to_headers, json={})
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Item Sync Run",
            "response_status": res.status_code,
            "response": res.json(),
        })

        # Upload inventory adjustments
        conn = sqlite3.connect(db_name)
        df = pd.read_sql_query(f"select * from inventory_transfer_{filter_attribute}", conn)
        records = df.to_dict(orient='records')
        conn.close()
        
        # Prepare inventory adjustment records
        add_inv_template = {
            "SourceContainerId": "",
            "SourceLocationId": "",
            "SourceContainerType": "LOCATION",
            "TransactionType": "INVENTORY_ADJUSTMENT",
            "ItemId": "",
            "Quantity": "",
            "PixEventName": "INVENTORY_ADJUSTMENT",
            "PixTransactionType": "ADJUST_UI"
        }
        
        out_records = []
        for rec in records:
            add_inv = deepcopy(add_inv_template)
            add_inv["SourceContainerId"] = rec["LocationId"]
            add_inv["SourceLocationId"] = rec["LocationId"]
            add_inv["ItemId"] = rec["ItemId"]
            add_inv["Quantity"] = max(rec["OnHand"],10)
            out_records.append(add_inv)
        
        total_adjustments = len(out_records)
        adjustment_batches = math.ceil(total_adjustments / upload_batch_size)
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Total inventory to upload: {total_adjustments} in {adjustment_batches} batches.",
            "response_status": None,
            "response": None,
        })
        # Upload in batches
        current_start = 0
        current_end = current_start + upload_batch_size
        failed_batches = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            current_start = 0
            current_end = current_start + upload_batch_size
            while current_start < total_adjustments:
                batch_end = min(current_end, total_adjustments)
                data = out_records[current_start:batch_end]
                futures.append(executor.submit(upload_inv_batch, to_url, to_headers, log_file, data, current_start, batch_end, filter_value))
                current_start += upload_batch_size
                current_end += upload_batch_size
            # Optionally, wait for all uploads to finish
            for future in concurrent.futures.as_completed(futures):
                pass  # or handle exceptions/results if needed        
        
    except Exception:
        return False

    write_log(log_file, {
        "timestamp": datetime.now().isoformat(),
        "status": "SUCCESS",
        "message": "Process finished",
        "response_status": None,
        "response": None,
    })
    # Delete any transfer_status files older than a day
    status_dir = os.path.dirname(log_file)
    now = time.time()
    for fname in os.listdir('.'):
        if fname.startswith("transfer_status") and fname.endswith(".json"):
            fpath = os.path.join(status_dir, fname)
            if os.path.isfile(fpath):
                if now - os.path.getmtime(fpath) > 86400:
                    os.remove(fpath)
    os.remove(db_name)  # Clean up log file after completion
    return True

# Non-Celery wrapper function for direct execution
def run_transfer_direct(config, log_file, progress_callback=None):
    """
    Run data transfer without Celery - direct synchronous execution
    
    Args:
        config: Configuration dictionary with all transfer settings
        log_file: Path to log file
        progress_callback: Optional callback function to report progress
    
    Returns:
        bool: True if successful, False if failed
    """
    return run_transfer_sync(config, log_file, progress_callback)

