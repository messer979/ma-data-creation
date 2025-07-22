from datetime import datetime, UTC, timedelta
import requests
import time
import logging
import json
import time
from pandas import DataFrame, read_csv
import io

logger = logging.getLogger(__name__)

def query_execution_wrapper(url, headers, query):
    status_code, queryId, error_message, cost = save_query(url, headers, query)
    if error_message:
        print(f'errored out on {query}')
        raise Exception(f"Error: {error_message}")
    execute_query(url, headers, queryId)
    time.sleep(1)
    for i in range(0, 35):
        wiretap_storage_ref, error = search_query_progress(url, headers, queryId)
        if wiretap_storage_ref:
            break
        else:
            time.sleep(2)


    if wiretap_storage_ref == None and error == None:
        print("Query did not return after 60 seconds. Please check wiretap config.")

    full_csv = retrieve_query(url, headers, wiretap_storage_ref)
    df = read_csv(io.StringIO(full_csv), dtype=str)
    df.columns = df.columns.str.replace(' ', '_')
    return df


def get_current_datetime_string():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]

def save_query(url, headers, query):
    queryId = get_current_datetime_string()
    # print(url)
    full_url = url + "/wiretap/api/functionalmetrics/onDemandQuery/save"
    # print(full_url)
    payload = {
        "QueryId": queryId,
        "SqlQuery": query,
        "QueryName": queryId,
        "Description": queryId,
        "QueryExpiryDate": (datetime.now(UTC) + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S')
    }
    response = requests.post(full_url, headers=headers, json=payload)
    if "Access token expired" in response.text:
        logger.error("InvalidTokenException")
        logger.error(response.text)
        error_message = "Access token has expired"
        return response.status_code, queryId, error_message, None
    try:
        error_message = response.json()['exceptions'][0]['message'] + f" TraceId: {response.headers['cp-trace-id']}"
    except Exception as e:
        pass
        # logger.error(e)
        # logger.error(response.text)
        if response.status_code != 200:
            raise Exception(f"Execute query returned with code {response.status_code}  {response.text}")
        error_message = None
    try:
        logger.info(f"execution_plan:\n{response.json()['data']['ExecutionPlan']}")
        plan = response.json()['data']['ExecutionPlan']
        plan = json.loads(plan)
        cost = plan['query_block']['cost_info']['query_cost']
    except TypeError:
        cost = None
    logger.debug(f"Query save result: {response.status_code}: ")
    return response.status_code, queryId, error_message, cost

def execute_query(url, headers, queryId):
    logger.debug(f"Execute query function for {queryId}")
    full_url = url + "/wiretap/api/functionalmetrics/onDemandQuery/execute"
    payload = {
        "QueryId": queryId
    }
    response = requests.post(full_url, headers=headers, json=payload)
    if response.status_code != 200:
        raise Exception(f"Execute query returned with code {response.status_code}")
    logger.debug(response.json())
    return None

def search_query_progress(url, headers, queryId):
    # print(headers)
    full_url = url + "/wiretap/api/functionalmetrics/onDemandQueryExecution/search"
    payload = {
        "Query": f"OnDemandQueryId={queryId}"
    }
    response = requests.post(full_url, headers=headers, json=payload)
    # logger.debug(f"query progress attempt:\n{response.json()}")
    try:
        if response.json()['data'][0]['ResponseLink'] != None:
            # print(response.json())
            logger.info("waiting for query to finish")
            wiretap_storage_ref = response.json()['data'][0]['ResponseLink']
            return wiretap_storage_ref, None
        elif response.json()['data'][0]['Status'] == 'Completed':
            try:
                return None, f"No records - error from wiretap: {response.json()['data'][0]['ErrorDescription']}"
            except (TypeError, KeyError, AttributeError):
                return None, f"No records"

    except IndexError as e:
        logger.error(e)
        logger.error(response.text)

    return None, None


def retrieve_query(url, headers, wiretap_storage_ref):
    if wiretap_storage_ref == None:
        raise Exception("Query was not able to fire.")
        return
    full_url = url + '/' + wiretap_storage_ref
    response = requests.get(full_url, headers=headers)
    return response.text
