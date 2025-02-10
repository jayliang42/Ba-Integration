from datetime import datetime
import time
import json
import warnings
from urllib3.exceptions import InsecureRequestWarning

from refresh_date import if_refresh
from daily_check import check_pending_files
from bara_api import get_raw_base64_data, post_request
from data_process_helper import process_base64_data, process_json
from log_helper import write_log
from constants import mexico_city_tz, customer_code, hs_client_id as client_id, hs_client_secret as client_secret, store02_code, store03_code

# Suppress the insecure request warning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)


def process_values(items: list[dict], document_name: str, store_code: str) -> list[dict]:
    """Process the values in the JSON data based on hs_datatype_key_map.json.

    Note: The value on Bara API is all string, so need to covert the value to the correct datatype for hanshow integration.

    strip() all the string values first, then process the values based on the data types.

    Parameters:
    - items: list, the list of JSON data to process.
    - document_name: str, the name of the document being processed.
    - store_code: str, the store code of hanshow allstar which needs to integrate.

    Returns:
    - A list of updated JSON data with values processed according to the hs_datatype_key_map.json.
    """

    # Open the keymap file
    with open("keymap/hs_datatype_keymap.json", "r") as f:
        datatype_keymap = json.load(f)

    processed_items = []

    # Process each item in the list
    for item in items:
        # Remove the key "lineNumber" if it exists
        item.pop("lineNumber", None)

        # if item doesn't have sku, remove it
        if "sku" not in item:
            continue

        # Iterate over a copy of the dictionary's keys to avoid runtime errors
        for key in list(item.keys()):
            # Strip string values
            if isinstance(item[key], str):
                item[key] = item[key].strip()

            # Check if the value is empty, None, or whitespace
            if item[key] in ("", None):
                # Remove the key if the value is empty
                del item[key]

            # Change the datatype of the value based on the keymap
            elif key in datatype_keymap:
                try:
                    if datatype_keymap[key] == "integer":
                        # Handle cases where the value might be a float or string representing a float
                        item[key] = int(float(item[key]))
                    elif datatype_keymap[key] == "number":
                        item[key] = float(item[key])
                    elif datatype_keymap[key] == "startdate":
                        # Convert date format "20210101"00:00am to timestamp in milliseconds

                        # Parse the input date string (YYYYMMDD) to a datetime object (assumes midnight time)
                        dt = datetime.strptime(item[key], "%Y%m%d")

                        # Localize the datetime to Mexico City timezone
                        dt_localized = mexico_city_tz.localize(dt)

                        # Convert to UTC timestamp and then to milliseconds
                        timestamp = int(dt_localized.timestamp() * 1000)

                        item[key] = timestamp
                    elif datatype_keymap[key] == "enddate":
                        # Convert date format "20210101"11:59pm to timestamp in milliseconds
                        # Parse the input date string (YYYYMMDD) to a datetime object (midnight time by default)
                        dt = datetime.strptime(item[key], "%Y%m%d")

                        # Localize the datetime to Mexico City timezone
                        dt_localized = mexico_city_tz.localize(dt)

                        # Convert to UTC timestamp and then to milliseconds
                        timestamp = int(dt_localized.timestamp() * 1000)

                        # Forward the end date by 23 hours 59 minutes 59 seconds (86399000 milliseconds)
                        timestamp = timestamp + 86399000

                        item[key] = timestamp

                except ValueError as e:
                    write_log(document_name, "failed",
                              f"Error processing key {key}: {e}")
                    del item[key]

        item = if_refresh(item, store_code)
        if item:
            # Append the processed item to the list
            processed_items.append(item)

    return processed_items


def send_integration(customer_code: str, store_code: str, client_id: str,
                     client_secret: str, items: list[dict], document_name: str) -> dict:
    """send integration to Hanshow Allstar via integration API.

    Parameters:
    - customer_code: str, the customer code for the integration.
    - store_code: str, the store code for the integration.
    - client_id: str, the client ID for the integration.
    - client_secret: str, the client secret for the integration.
    - items: list, the list of items to integrate.
    - document_name: str, the name of the document being integrated.
    """

    base_url = "https://americas-poc.hanshowcloud.net/integration/"
    endpoint = f"{customer_code}/{store_code}"

    # Headers
    headers = {
        "Content-Type": "application/json",
        "client-id": client_id,
        "client-secret": client_secret
    }

    items_list = []

    # check if the items are more than 1000, hanshow integration only accept 1000 items at a time
    if len(items) > 1000:
        # if more than 1000, split the items into chunks of 1000
        items_list = [items[i:i + 1000] for i in range(0, len(items), 1000)]
    else:
        items_list = [items]

    for item_batch in items_list:
        # remove the item with only sku, don't integrate
        for item in item_batch[:]:
            if len(item) == 1 and "sku" in item:
                item_batch.remove(item)
                print(f"Item {item['sku']} only has sku, removed.")

        body = {
            "storeCode": store_code,
            "customerStoreCode": customer_code,
            "batchNo": datetime.now(mexico_city_tz).strftime("%Y%m%d%H%M%S"),
            "items": item_batch
        }

        response = post_request(base_url, endpoint, headers, body)

        # if the integration is successful, write the document_name to log file for future reference
        if response["storeCode"] == store_code:
            print(f"{document_name} successfully integrated.")
            print(response)
            write_log(document_name, "success", customer_code, store_code)

    return response


def main(customer_code: str, store_code: str, client_id: str, client_secret: str, bara_department_id, bara_store_id, bara_source, fileType) -> dict:
    # Check pending_promo files and integrate the pending_promo items if start date is ready
    check_pending_files(
        customer_code, store_code, client_id, client_secret)

    raw_data_list, document_names_fileType = get_raw_base64_data(
        bara_department_id, bara_store_id, bara_source, fileType, store_code)

    if raw_data_list == 0:
        return "No new documents found"

    document_names = list(document_names_fileType.keys())
    document_fileType = list(document_names_fileType.values())
    json_data_list = process_base64_data(
        raw_data_list, document_names, store_code)

    for i in range(len(json_data_list)):
        # pass a list of items json data
        if document_fileType[i] == "ITM":
            items = json_data_list[i]["items"]
        elif document_fileType[i] == "PRM":
            items = json_data_list[i]["promotions"]
        else:
            write_log(document_names[i], "failed",
                      customer_code, store_code, f"{document_fileType[i]}file type is not supported.")
        # Process the JSON data
        processed_json = process_json(
            items, document_fileType[i])

        processed_json = process_values(
            processed_json, document_names[i], store_code)

        # Send the integration
        if processed_json != []:
            response = send_integration(
                customer_code, store_code, client_id, client_secret, processed_json, document_names[i])
            # if failed
            if "errorCode" in response:
                write_log(document_names[i], "failed", customer_code,
                          store_code, json.dumps(response))

                # remove the document name to historical_files/{store_code}.txt
                historical_file = f"historical_files/{store_code}.txt"

                with open(historical_file, 'r') as file:
                    lines = file.readlines()

                lines = [line for line in lines if line.strip() !=
                         document_names[i]]

                with open(historical_file, 'w') as file:
                    file.writelines(lines)


if __name__ == "__main__":
    now = datetime.now(
        mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
    print("------------------------------------")
    print(f"Now in UTC-6 Mexico City: {now}")

    file_type = ["ITM", "PRM"]

    print(f"Only integrate {file_type} files\n")

    # this store is for testing, use the same data as store 03
    print("Store 01 starts\n")
    try:
        main(customer_code, "01", client_id, client_secret,
             "12NEO", store03_code, "CT", file_type)
    except Exception as e:
        print(f"Error occurred during Store 01 integration: {e}")
        write_log("Store 01 Integration", "failed", error_message=str(e))

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    print("Store 02 starts\n")
    try:
        main(customer_code, "02", client_id, client_secret,
             "12NEO", store02_code, "CT", file_type)\

    except Exception as e:
        print(f"Error occurred during Store 02 integration: {e}")
        write_log("Store 02 Integration", "failed", error_message=str(e))

    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

    print("Store 03 starts\n")
    try:
        main(customer_code, "03", client_id, client_secret,
             "12NEO", store03_code, "CT", file_type)
    except Exception as e:
        print(f"Error occurred during Store 03 integration: {e}")
        write_log("Store 03 Integration", "failed", error_message=str(e))

    print("------------------------------------")
