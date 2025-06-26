"""
Standalone Order Transfer Module
Runs order transfer process without Celery or Redis dependencies
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
import threading
import queue
import traceback
from typing import Dict, List, Any

from scripts.inventory_transfer import write_log
from data_creation.order_import_funcs import scrub_order_data
from data_creation.sync_funcs import get_failed_count
# API Endpoints
ORDER_SEARCH_EP = '/dcorder/api/dcorder/originalOrder/search'
ORDER_BULK_EP = '/dcorder/api/dcorder/originalOrder/bulkImport'
ITEM_SEARCH_EP = '/item-master/api/item-master/item/search'
ITEM_BULK_EP = '/item-master/api/item-master/item/bulkImport'
ITEM_SYNC_EP = '/item-master/api/item-master/item/v2/sync'
FACILITY_SEARCH_EP = '/facility/api/facility/facility/search'
FACILITY_BULK_EP = '/facility/api/facility/facility/bulkImport'

def write_order_items(db_name, table_name: str, orders: List[Dict]):
    """Extract ItemIds, OriginalOrderIds, and DestinationFacilityIds from orders and write to SQLite database"""
    conn = sqlite3.connect(db_name)
    try:
        records = []
        for order in orders:
            original_order_id = order.get('OriginalOrderId')
            destination_facility_id = order.get('DestinationFacilityId')
            for order_line in order['OriginalOrderLine']:
                if 'ItemId' in order_line:
                    records.append({
                        'ItemId': order_line['ItemId'],
                        'OriginalOrderId': original_order_id,
                        'DestinationFacilityId': destination_facility_id
                    })
        
        if records:
            df = pd.DataFrame(records)
            df.to_sql(table_name, conn, index=False, if_exists='append')
    except Exception:
        raise
        pass
    finally:
        conn.close()

def db_writer(db_queue, db_name, db_write_done):
    """Database writer function - runs in separate thread"""
    while True:
        item = db_queue.get()
        if item is None:
            time.sleep(1)  # delay before each write to ensure the previous is done 
            break  # Sentinel value to stop the thread
        batch_data, filter_type = item
        time.sleep(1)  # delay before each write to ensure the previous is done 
        write_order_items(db_name, f"order_transfer_{filter_type}", batch_data)
        db_queue.task_done()
    db_write_done.set()

def download_and_import_order_batch(from_url, from_headers, to_url, to_headers, log_file, order_batches, order_query, batch_num):
    """Download and process orders in batches"""
    data = {"Query": f"OriginalOrderId in ('{'\',\''.join(order_query)}')", "Size": 500}
    res = requests.post(from_url + ORDER_SEARCH_EP, headers=from_headers, json=data)
    data = res.json()['data']
    data = scrub_order_data(data, to_headers)  # Ensure data is scrubbed before upload
    res_save = requests.post(to_url + ORDER_BULK_EP, headers=to_headers, json={"data": data})
    write_log(log_file, {
        "timestamp": datetime.now().isoformat(),
        "status": "RUNNING",
        "message": f"Transferred order batch {batch_num+1}/{order_batches}.\nSearch: {res.status_code}, BulkImport: {res_save.status_code}. FailedCount:{get_failed_count(res_save)}",
        "response_status": res_save.status_code,
        "trace": res_save.headers['cp-trace-id'],
        "env": res_save.request.url.split('/')[2],
        "response": res_save.json(),
    })
    return True

def download_and_import_facility_batch(from_url, from_headers, to_url, to_headers, log_file, facility_batches, facility_query, batch_num):
    """Download and process facilities in batches"""
    data = {"Query": f"FacilityId in ('{'\',\''.join(facility_query)}')", "Size": 500}
    res = requests.post(from_url + FACILITY_SEARCH_EP, headers=from_headers, json=data)
    data = res.json()['data']
    res_save = requests.post(to_url + FACILITY_BULK_EP, headers=to_headers, json={"data": data})
    write_log(log_file, {
        "timestamp": datetime.now().isoformat(),
        "status": "RUNNING",
        "message": f"Transferred facility batch {batch_num+1}/{facility_batches}.\nSearch: {res.status_code}, BulkImport: {res_save.status_code}. FailedCount:{get_failed_count(res_save)}",
        "response_status": res_save.status_code,
        "trace": res_save.headers['cp-trace-id'],
        "env": res_save.request.url.split('/')[2],
        "response": res_save.json(),
    })
    return True

def download_and_import_item_batch(from_url, from_headers, to_url, to_headers, log_file, item_batches, item_query, batch_num):
    """Download and process items in batches"""
    data = {"Query": f"ItemId in ('{'\',\''.join(item_query)}')", "Size": 500}
    res = requests.post(from_url + ITEM_SEARCH_EP, headers=from_headers, json=data)
    data = res.json()['data']
    res_save = requests.post(to_url + ITEM_BULK_EP, headers=to_headers, json={"data":data})
    write_log(log_file, {
        "timestamp": datetime.now().isoformat(),
        "status": "RUNNING",
        "message": f"Transferred item batch {batch_num+1}/{item_batches}.\nSearch: {res.status_code}, BulkImport: {res_save.status_code}. FailedCount:{get_failed_count(res_save)}",
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

def run_transfer_sync(config, log_file, progress_callback):
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
            progress_callback("Starting order transfer...")
        
        # Download order data
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": "Starting order data download...",
            "response_status": None,
            "response": None,
        })
        
        data = {
            "Query": f"{filter_type} = '{filter_value}'",
            "Size": 1
        }
        res = requests.post(from_url + ORDER_SEARCH_EP, headers=from_headers, json=data)
        if request_failed(res, log_file):
            return False

        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Initial order search for {filter_type}: {filter_value} shows {res.json()['header']['totalCount']} records.",
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
        
        progress_callback(f"Downloading {total} records in {number_of_batches} batches...")
        
        # Download in batches with async API and sync DB write
        db_queue = queue.Queue()
        db_write_done = threading.Event()
        db_thread = threading.Thread(target=db_writer, args=(db_queue, db_name, db_write_done))
        db_thread.start()

        for i in range(number_of_batches):
            data = {
                "Query": f"{filter_type} = '{filter_value}'",
                "Size": download_batch_size,
                "Page": i
            }
            res = requests.post(from_url + ORDER_SEARCH_EP, headers=from_headers, json=data)
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Downloading batch {i+1}/{number_of_batches} for {filter_type} {filter_value}",
                "response_status": res.status_code,
                "trace": res.headers['cp-trace-id'],
                "env": res.request.url.split('/')[2],
                "response": res.json(),
            })
            db_queue.put((res.json()['data'], filter_type))
            
            if progress_callback:
                progress_callback(f"Downloaded batch {i+1}/{number_of_batches}")
        
        db_queue.put(None)  # Sentinel value to stop the thread
        db_thread.join()
        
        if progress_callback:
            progress_callback("Processing items...")
        
        # Download and sync items
        if config.get('skip_items', False):
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping item conversion.",
                "response_status": None,
                "trace": None,
                "env": None,
                "response": None,
            })
        else:
            conn = sqlite3.connect(db_name)
            # Get unique items from order line items
            df = pd.read_sql_query(f"select distinct ItemId from order_transfer_{filter_type}", conn)
            conn.close()
            items = list(df.ItemId)
            
            total_items = len(items)
            item_batches = math.ceil(total_items / upload_batch_size)
            
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Processing {total_items} items in {item_batches} batches",
                "response_status": None,
                "response": None,
            })        # Process items synchronously instead of using concurrent.futures
            for i in range(item_batches):
                item_query = items[upload_batch_size*i:upload_batch_size*(i+1)]
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

# Download and sync facilities
        if config.get('skip_facilities', False):
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping facility conversion.",
                "response_status": None,
                "trace": None,
                "env": None,
                "response": None,
            })
        else:
            if progress_callback:
                progress_callback("Processing facilities...")
            
            conn = sqlite3.connect(db_name)
            # Get unique facilities from orders
            df = pd.read_sql_query(f"select distinct DestinationFacilityId from order_transfer_{filter_type} where DestinationFacilityId is not null", conn)
            conn.close()
            facilities = list(df.DestinationFacilityId)
            
            total_facilities = len(facilities)
            facility_batches = math.ceil(total_facilities / upload_batch_size)  # Process 50 facilities at a time
            
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Processing {total_facilities} facilities in {facility_batches} batches",
                "response_status": None,
                "response": None,
            })
            
            # Process facilities synchronously
            for i in range(facility_batches):
                facility_query = facilities[upload_batch_size*i:upload_batch_size*(i+1)]
                download_and_import_facility_batch(from_url, from_headers, to_url, to_headers, log_file, facility_batches, facility_query, i)
                if progress_callback:
                    progress_callback(f"Uploaded facility batch {i+1}")

# Upload orders
        if config.get('skip_orders', False):
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping order upload.",
                "response_status": None,
                "trace": None,
                "env": None,
                "response": None,
            })
            return True
        else:
            progress_callback("Preparing order upload...")
            
            # Get unique OriginalOrderIds from the database
            conn = sqlite3.connect(db_name)
            df = pd.read_sql_query(f"select distinct OriginalOrderId from order_transfer_{filter_type}", conn)
            conn.close()
            original_order_ids = list(df.OriginalOrderId)
            
            total_orders = len(original_order_ids)
            order_batches = math.ceil(total_orders / upload_batch_size)  # Process 50 orders at a time
            
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Total orders to upload: {total_orders} records in {order_batches} batches.",
                "response_status": None,
                "response": None,
            })
            
            progress_callback(f"Uploading {total_orders} orders...")
            
            # Upload orders in batches using the download_and_import_order_batch function
            for i in range(order_batches):
                order_query = original_order_ids[upload_batch_size*i:upload_batch_size*(i+1)]
                download_and_import_order_batch(from_url, from_headers, to_url, to_headers, log_file, order_batches, order_query, i)
                
                progress_callback(f"Imported order batch {i+1} of {order_batches}")

        
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "SUCCESS",
            "message": "Process finished successfully",
            "response_status": None,
            "response": None,
        })
        
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
            "message": f"Process failed with error: {traceback.format_exc()}",
            "response_status": None,
            "response": traceback.format_exc(),
        })
        progress_callback(f"Transfer failed: {str(e)}")
        raise
        
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
