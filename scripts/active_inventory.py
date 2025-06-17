from pymawm import ActiveWM
import configparser
import sqlite3
import pandas as pd
import math
import threading
import requests
import os
import re
import sys
import logging
logger = logging.getLogger(__name__)
import time
from copy import deepcopy
import json


def write_inv(table_name, response):
    conn = sqlite3.connect('staging_table.db')
    cursor = conn.cursor()
    try:
        df = pd.DataFrame(response)
        df = df.filter(["OnHand", "LocationId","ItemId"])
        df.to_sql(table_name, conn, index=False, if_exists='append')
    except Exception as e:
        logger.error(repr(e))
        logger.error(df.to_dict(orient='records'))
    conn.close()


def isProduction(url):
    regex = r"\/\/(\w+)"
    match = re.findall(regex, url)
    if len(match) == 1:
        if match[0].endswith('p'):
            return True
        else:
            return False
    else:
        print('no env found')
        return None

config = configparser.ConfigParser()
config.read('config.ini')

# Access values
zone = config['inventory']['zone']
download_batch_size = int(config['inventory']['download_batch_size'])
upload_batch_size = int(config['inventory']['upload_batch_size'])

from_env = config['inventory']['from_env']
from_org = config['inventory']['from_org']
from_facility = config['inventory']['from_facility']
from_token = config['inventory']['from_token']

to_env = config['inventory']['to_env']
to_org = config['inventory']['to_org']
to_facility = config['inventory']['to_facility']
to_token = config['inventory']['to_token']

required_keys = [
    'zone', 'download_batch_size', 'upload_batch_size',
    'from_env', 'from_org', 'from_facility',
    'to_env', 'to_org', 'to_facility',
    'to_token', 'from_token', 
]

missing_keys = [key for key in required_keys if key not in config['inventory']]
if missing_keys:
    raise ValueError(f"Missing required config keys: {', '.join(missing_keys)}")


## get tokens for from env and to env
from_environment = f"https://{from_env}.sce.manh.com"
active_from = ActiveWM(environment = from_environment, default_org=from_org, default_facility=from_facility, manual_token=from_token)
active_from.verbose = False

to_environment = f"https://{to_env}.sce.manh.com"
active_to = ActiveWM(environment = to_environment, default_org=to_org, default_facility=to_facility, manual_token=to_token)
active_to.verbose = False

if isProduction(active_to.wm_app):
    logger.error("cannot import to production")
    sys.exit()



# begin downloading from env api to sqlite file 

data = {"LocationQuery":{"Query":f"Zone ={zone} and InventoryReservationTypeId=LOCATION"}, "Size":1}
res = active_from.dci.post_inv_search(data)

# download_batch_size = args.download_batch_size
download_batch_size = 200
total = res.header['totalCount']
number_of_batches = math.ceil(int(total)/download_batch_size)

print('downloading inventory files to staging_table.db')
for i in range(0,number_of_batches):
    print(f'downloading batch {i} of {number_of_batches}')
    data = {"LocationQuery":{"Query":f"Zone ={zone} and InventoryReservationTypeId=LOCATION"}, "Size":download_batch_size, "Page":i}
    res = active_from.dci.post_inv_search(data)
    write_inv(f"inventory_transfer_{zone}", res.data)
    time.sleep(2)



## download items
conn = sqlite3.connect('staging_table.db')
cursor = conn.cursor()
df = pd.read_sql_query(f"select distinct ItemId from inventory_transfer_{zone}", conn)
records = df.to_dict(orient='records')
conn.close()
items = list(df.ItemId)


download_batch_size = 50
total = len(items)
number_of_batches = math.ceil(int(total)/download_batch_size)
print(f'processing items')
for i in range(0,number_of_batches):
    print(f'running batch {i}')
    item_query = items[download_batch_size*i:download_batch_size*(i+1)]
    data = {"query":f"ItemId in ({','.join(item_query)})", "size":50}
    res = active_from.itm.search_item(**data)
    print(f"search request: {res}")
    res_save = active_to.itm.bulk_import_item(res.data)
    print(f"bulk import: {res_save}")

print(f"running sync")
res = active_to.itm.custom_search('POST', '/item-master/api/item-master/item/v2/sync', data={})
print(f"sync res: {res}")


# begin importing to env from sqlite file to api 
conn = sqlite3.connect('staging_table.db')
cursor = conn.cursor()
df = pd.read_sql_query(f"select * from inventory_transfer_{zone}", conn)
records = df.to_dict(orient='records')
conn.close()

# upload_batch_size = args.batch_size
upload_batch_size = 50
total = len(df)
number_of_batches = math.ceil(total/upload_batch_size)

add_inv_template = {
    "SourceContainerId": "DMG-RTN-SORT",
    "SourceLocationId": "DMG-RTN-SORT",
    "SourceContainerType": "LOCATION",
    "TransactionType": "INVENTORY_ADJUSTMENT",
    "ItemId": "32480V4",
    "Quantity": "200",
    "TransactionType": "INVENTORY_ADJUSTMENT",
    "PixEventName": "INVENTORY_ADJUSTMENT",
    "PixTransactionType": "ADJUST_UI"
}
out_records = []
for rec in records:
    add_inv = deepcopy(add_inv_template)
    add_inv["SourceContainerId"] = rec["LocationId"]
    add_inv["SourceLocationId"] = rec["LocationId"]
    add_inv["ItemId"] = rec["ItemId"]
    add_inv["Quantity"] = rec["OnHand"]
    out_records.append(add_inv)
total = len(out_records)

with open('output_inventory.json', 'w') as f:
    json.dump(out_records, f, indent=4)

current_start = 0 # this is saying we will start from the first record (note that first record is '0', not '1')
current_end = current_start + upload_batch_size
while current_start < total:
    print(f'running batch {current_start}-{min(current_end,total)}')
    # this grabs the batch out of all the data
    data = out_records[current_start:min(current_end,total)]
    try:
        # this calls the function we defined 
        res = active_to.dci.post_absolute_adjust_inventory(json.dumps(data))
    # if we have an internet problem, we will wait 20 seconds to hope it resolves itself, continue means try the same batch again
    except (requests.exceptions.SSLError, requests.exceptions.ConnectTimeout,requests.exceptions.ConnectionError):
        print('SSLError')
        time.sleep(20)
        continue
    # if we don't get a 200 response, it will print to the terminal
    if res.full_response.status_code != 200:
        print(res)
    try:
        # if we get a 200 res, but there are failed records, these will write to a document in a 'Failed' directory
        if res.full_response.json()['data']['FailedRecords'] != []:
            os.makedirs('Failed', exist_ok=True)
            # print(res.json()['data']['FailedRecords'])
            with open(rf'Failed\batch_{current_start}-{min(current_end,total)}.log', 'w') as f:
                json.dump(res.full_response.json()['data']['FailedRecords'], f, indent=4)
    except TypeError:
        pass
    current_start += upload_batch_size
    current_end += upload_batch_size