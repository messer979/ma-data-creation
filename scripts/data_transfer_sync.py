"""
Standalone Data Import Module
Runs data import process without Celery or Redis dependencies
"""

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
from scripts.inventory_transfer import write_inv, write_log
import threading
import queue
import traceback

# API Endpoints
INV_SEARCH_EP = '/dcinventory/api/dcinventory/inventory/inventorysearch'
ITEM_SEARCH_EP = '/item-master/api/item-master/item/search'
ITEM_BULK_EP = '/item-master/api/item-master/item/bulkImport'
ADJUST_EP = '/dcinventory/api/dcinventory/inventory/adjustAbsoluteQuantity'
ITEM_SYNC_EP = '/item-master/api/item-master/item/v2/sync'

def db_writer(db_queue, db_name, db_write_done):
    """Database writer function - runs in separate thread"""
    while True:
        item = db_queue.get()
        if item is None:
            break  # Sentinel value to stop the thread
        batch_data, filter_type = item
        time.sleep(1)  # delay before each write to ensure the previous is done 
        write_inv(db_name, f"inventory_transfer_{filter_type}", batch_data)
        db_queue.task_done()
    db_write_done.set()

def upload_inv_batch(to_url, to_headers, log_file, data, filter_value, batch_run, total_batches):
    """Upload inventory batch function"""
    try:
        res = requests.post(to_url + ADJUST_EP, headers=to_headers, json=data)
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Uploaded batch {batch_run} of {total_batches} for {filter_value}",
            "response_status": res.status_code,
            "trace": res.headers['cp-trace-id'],
            "env": res.request.url.split('/')[2],
            "response": res.json(),
        })
    except (requests.exceptions.SSLError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        time.sleep(20)
        # Optionally, you could retry here or log a failure

def download_and_import_item_batch(from_url, from_headers, to_url, to_headers, log_file, item_batches, item_query, batch_num):
    """Download and process items in batches"""
    data = {"Query": f"ItemId in ('{'\',\''.join(item_query)}')", "Size": 200}
    res = requests.post(from_url + ITEM_SEARCH_EP, headers=from_headers, json=data)
    data = res.json()['data']
    res_save = requests.post(to_url + ITEM_BULK_EP, headers=to_headers, json={"data":data})
    write_log(log_file, {
        "timestamp": datetime.now().isoformat(),
        "status": "RUNNING",
        "message": f"Transferred item batch {batch_num+1}/{item_batches}.\nSearch: {res.status_code}, BulkImport: {res_save.status_code}",
        "response_status": res_save.status_code,
        "trace": res_save.headers['cp-trace-id'],
        "env": res_save.request.url.split('/')[2],
        "response": res_save.json(),
    })
    return True

def request_failed(res, log_file):
    """Check if request failed and log error"""
    if res.status_code != 200:
        if 'Access token expired' in res.text:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "FAILED",
                "message": "Access token expired.",
                "response_status": res.status_code,
                "trace": res.headers['cp-trace-id'],
                "env": res.request.url.split('/')[2],
                "response": res.text,

            })
            return True
        write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "FAILED",
                "message": "Request Failed.",
                "response_status": res.status_code,
                "trace": res.headers['cp-trace-id'],
                "env": res.request.url.split('/')[2],
                "response": res.json() if res.headers.get('Content-Type') == 'application/json' else res.text,
            })
        return True
    else:
        return False

def run_transfer_sync(config, log_file, progress_callback=None):
    """
    Run data transfer synchronously without Celery
    
    Args:
        config: Configuration dictionary with all transfer settings
        log_file: Path to log file
        progress_callback: Optional callback function to report progress
    
    Returns:
        bool: True if successful, False if failed
    """
    db_name = log_file.replace('.json', '.db') 
    
    try:
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
                "env": to_env,
                "response": None,
            })
            return False

        # Setup environments
        from_url = f"https://{from_env}.sce.manh.com"
        from_headers = {
            "SelectedOrganization": from_org,
            "SelectedLocation": from_facility,
            "Authorization": f"Bearer {from_token}",
        }
                
        to_url = f"https://{to_env}.sce.manh.com"
        to_headers = {
            "SelectedOrganization": to_org,
            "SelectedLocation": to_facility,
            "Authorization": f"Bearer {to_token}",  # Fixed: was using from_token
        }
        
        if progress_callback:
            progress_callback("Starting data transfer...")
        
        # Download inventory data
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": "Starting inventory data download...",
            "response_status": None,
            "response": None,
        })
        
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
            "message": f"Initial inventory search for {filter_type}: {filter_value} shows {res.json()['header']['totalCount']} records.",
            "response_status": res.status_code,
            "trace": res.headers['cp-trace-id'],
            "env": res.request.url.split('/')[2],
            "response": res.json(),
        })
        
        total = res.json()['header']['totalCount']
        number_of_batches = math.ceil(int(total) / download_batch_size)
        if number_of_batches == 0:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "FAILED",
                "message": f"No records found for {filter_type} = {filter_value}.",
                "response_status": res.status_code,
                "trace": res.headers['cp-trace-id'],
                "env": res.request.url.split('/')[2],
                "response": res.json(),
            })
            return False
        else:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Total batches to download: {number_of_batches}",
                "response_status": None,
                "response": None,
            })
        
        if progress_callback:
            progress_callback(f"Downloading {total} records in {number_of_batches} batches...")
        
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
                "trace": res.headers['cp-trace-id'],
                "env": res.request.url.split('/')[2],
                "response": res.json(),
            })
            db_queue.put((res.json()['data'], filter_type))  # Fixed: was using res.data and zone
            
            if progress_callback:
                progress_callback(f"Downloaded batch {i+1}/{number_of_batches}")
        
        db_queue.put(None)  # Sentinel value to stop the thread
        db_thread.join()
        
        if progress_callback:
            progress_callback("Processing items...")
        
        # Download and sync items
        if config['inventory_only']:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping item download as inventory_only is set to True.",
                "response_status": None,
                "trace": None,
                "env": None,
                "response": None,
            })
        else:
            conn = sqlite3.connect(db_name)
            df = pd.read_sql_query(f"select distinct ItemId from inventory_transfer_{filter_type}", conn)
            conn.close()
            items = list(df.ItemId)
            
            total_items = len(items)
            item_batches = math.ceil(total_items / 50)
            
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Processing {total_items} items in {item_batches} batches",
                "response_status": None,
                "response": None,
            })        # Process items synchronously instead of using concurrent.futures
            for i in range(item_batches):
                item_query = items[50*i:50*(i+1)]
                download_and_import_item_batch(from_url, from_headers, to_url, to_headers, log_file, item_batches, item_query, i)
                progress_callback(f"Uploaded item batch {i+1}")

        # Commented out concurrent processing to avoid errors:
        # with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        #     futures = []
        #     for i in range(item_batches):
        #         item_query = items[50*i:50*(i+1)]
        #         futures.append(executor.submit(download_and_import_item_batch, from_url, from_headers, to_url, to_headers, log_file, item_batches, item_query, i))
        #     for future in concurrent.futures.as_completed(futures):
        #         pass  # Optionally handle exceptions/results

        # Sync items
            if progress_callback:
                progress_callback("Syncing items and waiting 5s...")
            
            res = requests.post(to_url + ITEM_SYNC_EP, headers=to_headers, json={})
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Item Sync Run",
                "response_status": res.status_code,
                "trace": res.headers['cp-trace-id'],
                "env": res.request.url.split('/')[2],
                "response": res.json(),
            })
            time.sleep(5)  # Wait for sync to complete

        # Upload inventory adjustments

        if config['items_only']:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping inventory adjustments as items_only is set to True.",
                "response_status": None,
                "trace": None,
                "env": None,
                "response": None,
            })
            return True
        else:
            if progress_callback:
                progress_callback("Preparing inventory adjustments...")
            
            conn = sqlite3.connect(db_name)
            df = pd.read_sql_query(f"select * from inventory_transfer_{filter_type}", conn)  # Fixed: was using filter_attribute
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
                add_inv["Quantity"] = max(rec["OnHand"], 10)
                out_records.append(add_inv)
            
            total_adjustments = len(out_records)
            adjustment_batches = math.ceil(total_adjustments / upload_batch_size)
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Total inventory to upload: {total_adjustments} records in {adjustment_batches} batches.",
                "response_status": None,
                "response": None,
            })
            
            if progress_callback:
                progress_callback(f"Uploading {total_adjustments} inventory adjustments...")
            # Upload in batches synchronously instead of using concurrent.futures
            current_start = 0
            # while current_start < total_adjustments:
            for i in range(adjustment_batches):
                current_start = i * upload_batch_size
                batch_end = min((i + 1) * upload_batch_size, total_adjustments)
                # batch_end = min(current_start + upload_batch_size, total_adjustments)
                data = out_records[current_start:batch_end]
                upload_inv_batch(to_url, to_headers, log_file, data, filter_value, batch_run=i, total_batches = adjustment_batches)
                # current_start += upload_batch_size
                progress_callback(f"Imported inventory batch {i+1} of {adjustment_batches}")

        
        # Commented out concurrent processing to avoid errors:
        # with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        #     futures = []
        #     current_start = 0
        #     while current_start < total_adjustments:
        #         batch_end = min(current_start + upload_batch_size, total_adjustments)
        #         data = out_records[current_start:batch_end]
        #         futures.append(executor.submit(upload_inv_batch, to_url, to_headers, log_file, data, current_start, batch_end, filter_value))
        #         current_start += upload_batch_size
        #     
        #     # Wait for all uploads to finish
        #     for future in concurrent.futures.as_completed(futures):
        #         pass  # or handle exceptions/results if needed
        
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS",
            "message": "Process finished successfully",
            "response_status": None,
            "response": None,
        })
        
        if progress_callback:
            progress_callback("Transfer completed successfully!")
        
        # Clean up
        cleanup_old_files(log_file)
        if os.path.exists(db_name):
            os.remove(db_name)
        
        return True
        
    except Exception as e:
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "FAILED",
            "message": f"Process failed with error: {str(e)}",
            "response_status": None,
            "response": traceback.format_exc(),
        })
        
        if progress_callback:
            progress_callback(f"Transfer failed: {str(e)}")
        
        return False

def cleanup_old_files(log_file):
    """Clean up old transfer status files and database files"""
    status_dir = os.path.dirname(log_file)
    if not status_dir:
        status_dir = '.'
    
    now = time.time()
    for fname in os.listdir(status_dir):
        fpath = os.path.join(status_dir, fname)
        if os.path.isfile(fpath):
            # Clean up old JSON log files
            if fname.startswith("transfer_status") and fname.endswith(".json"):
                if now - os.path.getmtime(fpath) > 86400:  # 24 hours
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass  # Ignore if file can't be removed
            
            # Clean up old database files
            elif fname.startswith("transfer_status") and fname.endswith(".db"):
                if now - os.path.getmtime(fpath) > 86400:  # 24 hours
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass  # Ignore if file can't be removed
