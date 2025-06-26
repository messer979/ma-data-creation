"""
Active Inventory Transfer Module
Converts the active_inventory.py script into a callable function
"""

import sqlite3
import pandas as pd
import re
import time
from copy import deepcopy
from typing import Dict, List, Any
import json

def is_production(url: str) -> bool:
    """Check if environment is production"""
    regex = r"//(\w+)"
    match = re.findall(regex, url)
    if len(match) == 1:
        return match[0].endswith('p')
    return False

def write_inv(db_name, table_name: str, response: List[Dict]):
    """Write inventory data to SQLite database"""
    conn = sqlite3.connect(db_name)
    try:
        df = pd.DataFrame(response)
        # df = df.filter(["OnHand", "LocationId", "ItemId"])
        df['Extended'] = df['Extended'].apply(json.dumps)
        df.drop(columns=['ItemExtended', 'InventoryConditionCodeList', 'IlpnConditionCodeList', 'IlpnLabels'], 
                inplace=True, 
                errors='ignore')
        df.to_sql(table_name, conn, index=False, if_exists='append')
    except Exception:
        raise
        pass
    finally:
        conn.close()

def write_log(log_file: str, log_entry: Dict[str, Any]):
    """Append log entry to log file"""
    with open(log_file, "a") as f:
        json.dump(log_entry, f)
        f.write('\n')