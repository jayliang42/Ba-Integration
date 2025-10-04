from datetime import datetime
import json
import warnings
import os
import bisect
from urllib3.exceptions import InsecureRequestWarning

from daily_check import check_pending_files
from bara_api import get_raw_base64_data, post_request
from data_process_helper import process_base64_data, process_json, process_values
from log_helper import write_log
from credentials import mexico_city_tz, customer_code, hs_client_id as client_id, hs_client_secret as client_secret, store02_code, store03_code

# Suppress the insecure request warning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)


def add_to_historical_files(document_name: str, store_code: str):
    """Add a successfully integrated document to the historical files list.
    
    Parameters:
    - document_name: str, the name of the document to add
    - store_code: str, the store code
    """
    historical_file = f"historical_files/{store_code}.txt"
    
    # Read existing documents from the historical file
    lines = []
    if os.path.exists(historical_file):
        with open(historical_file, "r") as f:
            lines = [line.strip() for line in f]
    
    # Insert the new document in the correct position (sorted)
    if document_name not in lines:
        bisect.insort(lines, document_name)
        
        # Write the updated list back to the file
        with open(historical_file, "w") as f:
            f.writelines(f"{line}\n" for line in lines)


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
            # Add to historical files only after successful integration
            add_to_historical_files(document_name, store_code)

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

        # Send the integration or handle empty processed items
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
        else:
            # No valid items to process, but mark file as processed to prevent re-download
            print(f"⚠ {document_names[i]} - No valid items to process, marked as processed")
            write_log(document_names[i], "skipped", customer_code, store_code, "No valid items to process")
            add_to_historical_files(document_names[i], store_code)


if __name__ == "__main__":
    now = datetime.now(
        mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
    print("------------------------------------")
    print(f"Now in UTC-6 Mexico City: {now}")

    file_type = ["ITM", "PRM"]

    print(f"Only integrate {file_type} files\n")

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
