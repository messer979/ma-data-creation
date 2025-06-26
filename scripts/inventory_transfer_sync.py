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
import threading
import queue
import traceback

from scripts.inventory_transfer import write_inv, write_log
from data_creation.sync_funcs import get_failed_count

# API Endpoints
INV_SEARCH_EP = '/dcinventory/api/dcinventory/inventory/inventorysearch'
ITEM_SEARCH_EP = '/item-master/api/item-master/item/search'
ITEM_BULK_EP = '/item-master/api/item-master/item/bulkImport'
ADJUST_EP = '/dcinventory/api/dcinventory/inventory/adjustAbsoluteQuantity'
LPN_CREATE_EP = '/dcinventory/api/dcinventory/ilpn/createIlpnAndInventory'
ITEM_SYNC_EP = '/item-master/api/item-master/item/v2/sync'
PALLETIZE_EP = '/dcinventory/api/dcinventory/ilpn/palletizeLpns'

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

def upload_inv_batch(to_url, to_headers, log_file, data, filter_value, batch_run, total_batches, endpoint):
    """Upload inventory batch function"""
    try:
        res = requests.post(to_url + endpoint, headers=to_headers, json=data)
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Uploaded batch {batch_run+1} of {total_batches} for {filter_value}",
            "response_status": res.status_code,
            "trace": res.headers['cp-trace-id'],
            "env": res.request.url.split('/')[2],
            "response": res.json(),
        })
    except (requests.exceptions.SSLError, requests.exceptions.ConnectTimeout, requests.exceptions.ConnectionError):
        time.sleep(20)
        # Optionally, you could retry here or log a failure

def palletize_lpns(to_url, to_headers, data, batch_run, total_batches, filter_value, log_file):
    """Palletize LPNs"""
    try:
        res = requests.post(to_url + PALLETIZE_EP, headers=to_headers, json=data)
        write_log(log_file, {
            "timestamp": datetime.now().isoformat(),
            "status": "RUNNING",
            "message": f"Uploaded batch {batch_run+1} of {total_batches} for {filter_value}",
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
        inventory_type = config['inventory_type']
        
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
        if inventory_type == "Active":
            inv_res_type = 'LOCATION'
        else:
            inv_res_type = 'LPN'
        data = {
            "LocationQuery": {"Query": f"{filter_type} ={filter_value} and InventoryReservationTypeId={inv_res_type}"},
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
        
        progress_callback(f"Downloading {total} records in {number_of_batches} batches...")
        
        # Download in batches with async API and sync DB write
        db_queue = queue.Queue()
        db_write_done = threading.Event()
        db_thread = threading.Thread(target=db_writer, args=(db_queue, db_name, db_write_done))
        db_thread.start()

        for i in range(number_of_batches):
            data = {
                "LocationQuery": {"Query": f"{filter_type} ={filter_value} and InventoryReservationTypeId={inv_res_type}"},
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
            
            progress_callback(f"Downloaded batch {i+1}/{number_of_batches}")
        
        db_queue.put(None)  # Sentinel value to stop the thread
        db_thread.join()
        
        if progress_callback:
            progress_callback("Processing items...")
        
        # Download and sync items
        if config['skip_items']:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping item download.",
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
        if config['skip_inventory']:
            write_log(log_file, {
                "timestamp": datetime.now().isoformat(),
                "status": "RUNNING",
                "message": f"Skipping inventory adjustments.",
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
            df['Extended'] = df['Extended'].apply(json.loads)
            records = df.to_dict(orient='records')

            conn.close()
            
            # Prepare inventory adjustment records
            if inv_res_type == 'LOCATION':
                endpoint = ADJUST_EP
                add_inv_template = {
                    "SourceContainerId": "",
                    "SourceLocationId": "",
                    "SourceContainerType": "LOCATION",
                    "TransactionType": "INVENTORY_ADJUSTMENT",
                    "ItemId": "",
                    "Quantity": "",
                    "PixEventName": "INVENTORY_ADJUSTMENT",
                    "PixTransactionType": "ADJUST_UI",
                    "Extended": {}
                }
                out_records = []
                for rec in records:
                    add_inv = deepcopy(add_inv_template)
                    add_inv["SourceContainerId"] = rec["LocationId"]
                    add_inv["SourceLocationId"] = rec["LocationId"]
                    add_inv["ItemId"] = rec["ItemId"]
                    add_inv["Quantity"] = max(rec["OnHand"], 10) # Ensure minimum quantity, WM errors on 0
                    add_inv["Extended"] = rec["Extended"]
                    out_records.append(add_inv)

            else: # lpn and pallet are the same 
                endpoint = LPN_CREATE_EP
                add_inv_template = {
                    "IlpnTypeId": "ILPN",
                    "IlpnId": "",
                    "Status": "3000",
                    "CurrentLocationId": "CS-102-D",
                    "Inventory": [
                        {
                            "InventoryContainerTypeId": "ILPN",
                            "InventoryContainerId": "",
                            "ItemId": "",
                            "OnHand": 50,
                            "Extended": {}
                        }
                    ]
                }
                out_records = []
                for rec in records:
                    add_inv = deepcopy(add_inv_template)
                    add_inv["IlpnId"] = rec["IlpnId"]
                    add_inv["Inventory"][0]["InventoryContainerId"] = rec["IlpnId"]
                    add_inv["CurrentLocationId"] = rec["LocationId"]
                    add_inv["Inventory"][0]["ItemId"] = rec["ItemId"]
                    add_inv["Inventory"][0]["OnHand"] = int(rec["OnHand"])
                    add_inv["Inventory"][0]["Extended"] = rec["Extended"]
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
                data = out_records[current_start:batch_end]
                upload_inv_batch(to_url, to_headers, log_file, data, filter_value, batch_run=i, total_batches=adjustment_batches, endpoint=endpoint)
                progress_callback(f"Imported inventory batch {i+1} of {adjustment_batches}")

            if inventory_type == "Palletized":
                # Palletize LPNs if inventory type is Palletized
                if progress_callback:
                    progress_callback("Palletizing LPNs...")
                
                # Query database to group LPNs by ParentLpnId and LocationId
                conn = sqlite3.connect(db_name)
                query = f"""
                SELECT ParentLpnId, LocationId, IlpnId, ItemId, OnHand, Extended
                FROM inventory_transfer_{filter_type} 
                WHERE ParentLpnId IS NOT NULL 
                GROUP BY ParentLpnId, LocationId, IlpnId
                ORDER BY ParentLpnId, LocationId
                """
                lpn_df = pd.read_sql_query(query, conn)
                conn.close()
                
                if lpn_df.empty:
                    write_log(log_file, {
                        "timestamp": datetime.now().isoformat(),
                        "status": "RUNNING",
                        "message": "No LPNs with ParentLpnId found for palletization.",
                        "response_status": None,
                        "response": None,
                    })
                else:
                    # Group by ParentLpnId and LocationId
                    pallet_groups = lpn_df.groupby(['ParentLpnId', 'LocationId'])
                    
                    palletize_records = []
                    for (parent_lpn_id, location_id), group in pallet_groups:
                        # Create pallet record with child LPNs
                        child_lpns = []
                        for _, row in group.iterrows():
                            extended_data = json.loads(row['Extended']) if row['Extended'] else {}
                            child_lpn = {
                                "IlpnId": row['IlpnId'],
                                "IlpnTypeId": "ILPN",
                                "Status": 3000,
                                "CurrentLocationId": location_id,
                                "PhysicalEntityCodeId": "ILPN",
                                "CurrentLocationTypeId": "STORAGE",
                                "Inventory": [
                                    {
                                        "InventoryContainerId": row['IlpnId'],
                                        "IlpnId": row['IlpnId'],
                                        "InventoryContainerTypeId": "ILPN",
                                        "OnHand": int(row['OnHand']),
                                        "LocationId": location_id,
                                        "ItemId": row['ItemId'],
                                        "Extended": extended_data
                                    }
                                ]
                            }
                            child_lpns.append(child_lpn)
                        
                        # Create pallet record
                        pallet_record = {
                            "IlpnId": parent_lpn_id,
                            "IlpnTypeId": "PALLET",
                            "CurrentLocationId": location_id,
                            "InheritIlpnLocation": True,
                            "Status": 3000,
                            "CalculateLpnSizeType": True,
                            "ChildLpns": child_lpns
                        }
                        palletize_records.append(pallet_record)
                    
                    total_pallets = len(palletize_records)
                    palletize_batches = math.ceil(total_pallets / upload_batch_size)
                    
                    write_log(log_file, {
                        "timestamp": datetime.now().isoformat(),
                        "status": "RUNNING",
                        "message": f"Creating {total_pallets} pallets in {palletize_batches} batches.",
                        "response_status": None,
                        "response": None,
                    })
                    
                    for i in range(palletize_batches):
                        current_start = i * upload_batch_size
                        batch_end = min((i + 1) * upload_batch_size, total_pallets)
                        batch_data = palletize_records[current_start:batch_end]
                        palletize_lpns(to_url, to_headers, batch_data, batch_run=i, total_batches=palletize_batches, filter_value=filter_value, log_file=log_file)
                        if progress_callback:
                            progress_callback(f"Palletized batch {i+1} of {palletize_batches}")
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
