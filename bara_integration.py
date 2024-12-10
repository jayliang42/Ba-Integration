from datetime import datetime
import time
import datetime
import json
import os
import re
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning
import retrying
import pytz
import bisect

# Suppress the insecure request warning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# Set the timezone to UTC-6 (Mexico City)
mexico_city_tz = pytz.timezone("America/Mexico_City")


@retrying.retry(wait_fixed=5000, stop_max_attempt_number=10)
def post_request(base_url, endpoint, headers, body=None, auth=None):
    """Make a POST request to the specified endpoint with the given headers and body.

    Parameters:
    - base_url: str, the base URL of the API.
    - endpoint: str, the endpoint to which the request is made.
    - headers: dict, the headers to include in the request.
    - body: dict, the JSON body of the request.
    - auth: tuple, the authentication credentials (username, password).

    Returns:
    - The JSON response from the API.
    """
    # Construct the full URL
    url = f"{base_url}{endpoint}"

    # Make the POST request
    response = requests.post(url, headers=headers,
                             json=body, auth=auth, verify=False)

    # Check if the request is successful
    if response.status_code != requests.codes.ok:
        print(f"Error: {response.status_code} - {response.text}")
        write_log("API request", "failed", error_message=response.text)
        raise Exception("Request failed.")

    # Return the response in JSON format if successful
    return response.json()


def get_bearer_token() -> str:
    """get the bearer token for Bara API

    Returns:
    - The bearer token for the Bara API.
    """
    url = "https://ipaas.oxxo.io/integration/rest/oAuth/getToken?grant_type=client_credentials"

    # Basic auth credentials from Bara API
    username = "423f55af3377415b94295cd0544f4f90"
    password = "abd74c50af004cb0b60d872efce6cc73"

    # No additional headers required in this case
    headers = {}

    # HTTP Basic Authentication
    auth = (username, password)

    response = post_request(url, "", headers=headers, auth=auth)

    bearer_token = response.get("access_token")

    return bearer_token


def get_document_list(base_url: str, endpoint: str, bearer_token: str,
                      department_id: str, source: str, store_id: str) -> list:
    """Get the list of documents available for download from Bara API.

    Parameters:
    - base_url: str, the base URL of the API.
    - endpoint: str, the endpoint to which the request is made.
    - bearer_token: str, the bearer token for the API.
    - department_id: str, the department ID.
    - source: str, the source of the documents.
    - store_id: str, the store ID.

    Returns:
    - A list of documents available for download.
    """

    # Headers
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Tracking-Id": "a306ef84-1ba0-4ac4-a782-9d69be3b4f44",
        "Channel-Id": "WEB",
        "Country-Code": "MX",
        "Language": "SPA",
        "x-Gateway-APIKey": "7371052d-ee88-43db-a2eb-48e8a513b60c",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "MyApp/1.0 (Windows NT 10.0; Win64; x64)"
    }

    # JSON body
    body = {
        "departmentId": department_id,
        "source": source,
        "storeId": store_id
    }

    response = post_request(base_url, endpoint, headers, body)

    return response["documents"]


def get_document_base64_data(base_url: str, endpoint: str, bearer_token: str, document_name_list: list,
                             department_id: str, source: str, store_id: str) -> list:
    """get the base64 data of the documents from Bara API

    Parameters:
    - base_url: str, the base URL of the API.
    - endpoint: str, the endpoint to which the request is made.
    - bearer_token: str, the bearer token for the API.
    - document_name_list: list, the list of document names to download.
    - department_id: str, the department ID.
    - source: str, the source of the documents.
    - store_id: str, the store ID.

    Returns:
    - A list of base64 data of the documents
    """

    # Headers
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Tracking-Id": "35e3599f-dbd2-4387-8648-6df6da783a29",
        "Channel-Id": "WEB",
        "Country-Code": "MX",
        "Language": "SPA",
        "x-Gateway-APIKey": "7371052d-ee88-43db-a2eb-48e8a513b60c",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "MyApp/1.0 (Windows NT 10.0; Win64; x64)"
    }

    document_data_list = []

    for document in document_name_list:
        print(f"Downloading {document}...")
        # wait for 1 second before making the next request，to avoid the rate limit
        time.sleep(1)
        # JSON body
        body = {
            "departmentId": department_id,
            "source": source,
            "storeId": store_id,
            "documents": [
                {"name": document, "fileType": document[:3]},
            ]
        }
        response = post_request(base_url, endpoint, headers, body)
        # record the base64 data
        document_data_list.append(response["documents"][0]["data"])

    return document_data_list


def get_raw_base64_data(bara_department_id: str, bara_store_id: str, source: str, fileType: list, store_code: str) -> tuple[list, dict]:
    """Get the raw base64 data of the documents from Bara API.

    Parameters:
    - bara_department_id: str, the department ID for Bara API.
    - bara_store_id: str, the store ID for Bara API.
    - source: str, the source of the documents for Bara API.
    - fileType: list, the list of file types to download.
    - store_code: str, the store code of hanshow allstar which needs to integrate.

    Returns:
    - A tuple containing the list of base64 data of the documents and the document names with fileType.
    """

    bearer_token = get_bearer_token()

    # Base URL
    base_url = "https://api.oxxo.io/xapi-multichannel-outbound/api/v1"

    # url endpoint
    url_endpoint = "/documents"

    # Get the document list
    document_list = get_document_list(
        base_url, url_endpoint, bearer_token, department_id=bara_department_id, source=source, store_id=bara_store_id)

    def filter_documents(documents, store_code=store_code):
        # only get the documents with today's date
        today = datetime.datetime.now(mexico_city_tz).strftime("%y%m%d")

        # read historical_files/{store_code}.txt
        # filter documents that are already integrated
        historical_file = f"historical_files/{store_code}.txt"
        existed_documents = []
        if os.path.exists(historical_file):
            with open(historical_file, "r") as f:
                existed_documents = f.readlines()
                existed_documents = [doc.strip() for doc in existed_documents]

        # documents = [
        #     doc for doc in documents if today in doc["name"] and doc["name"].replace(".gz", "") not in existed_documents]

        documents = [doc for doc in documents if doc["name"].replace(
            ".gz", "") not in existed_documents]

        print(f"{len(documents)} documents found.\n")
        for doc in documents:
            print(doc["name"].replace(".gz", ""))

        return documents

    document_list = filter_documents(document_list)

    # if no new documents found
    if len(document_list) == 0:
        return 0, {}

    # Get the document names with fileType (e.g. ITM, PRM)
    # filter out the documents with fileType not in the list
    document_names_fileType = {}
    for doc in document_list:
        if doc["fileType"] in fileType:
            document_names_fileType[doc["name"]] = doc["fileType"]
        else:
            # Save pending file for reference
            with open(f"current_files/{store_code}/pending_promo/pending_promo.txt", "a+") as f:
                # Move the file cursor to the beginning to read the existing content
                f.seek(0)
                # Read content from pending_promo.txt as a list
                content = f.readlines()
                # Check if the document name is already in the list
                if f"{doc['name']}: {doc['fileType']}\n" not in content:
                    # If not, append the document name to the list
                    f.write(f"{doc['name']}: {doc['fileType']}\n")

    # Get the document names based on the file type filtered
    document_names = list(document_names_fileType.keys())

    print(f"\nDocument names going to integrate: {document_names}\n")

    # Get the document base64 data
    document_data_list = get_document_base64_data(base_url, "/documents/downloads",
                                                  bearer_token, document_names, department_id=bara_department_id, source=source, store_id=bara_store_id)

    # return the base64 data and the document names with fileType
    return document_data_list, document_names_fileType


def convert_base64_to_json(base64_data: str) -> dict:
    """Convert the Base64 data to JSON format.

    Parameters:
    - base64_data: str, the Base64 data to convert.

    Returns:
    - The JSON data decoded from the Base64 string.
    """

    import base64
    import gzip
    import json
    from io import BytesIO

    # Decode the Base64 string
    decoded_data = base64.b64decode(base64_data)

    # Decompress the GZipped data
    with gzip.GzipFile(fileobj=BytesIO(decoded_data)) as gz:
        json_data = json.load(gz)

    return json_data


def process_base64_data(document_data_list: list[dict], document_names: list[dict], store_code) -> list[dict]:
    """process the base64 data to JSON format and save the JSON files to current_files/{store_code} folder

    Parameters:
    - document_data_list: list, the list of base64 data of the documents.
    - document_names: list, the list of document names.
    - store_code: str, the store code of hanshow allstar which needs to integrate.

    Returns:
    - A list of JSON data decoded from the Base64 strings.
    """

    json_data_list = []

    for i in range(len(document_data_list)):
        json_data = convert_base64_to_json(document_data_list[i])
        json_data_list.append(json_data)

        # save Bara json files as reference
        document_names[i] = document_names[i].replace(".gz", "")
        with open(f"current_files/{store_code}/{document_names[i]}", "w") as f:
            json.dump(json_data, f, indent=4)

        # add the document name to historical_files/{store_code}.txt
        historical_file = f"historical_files/{store_code}.txt"
        new_document = document_names[i]
        # Read the existing documents from the historical file
        lines = []
        if os.path.exists(historical_file):
            with open(historical_file, "r") as f:
                lines = [line.strip() for line in f]

        # Insert the new document in the correct position
        bisect.insort(lines, new_document)  # binary search and insert

        # Write the updated list of documents to the historical file
        with open(historical_file, "w") as f:
            f.writelines(f"{line}\n" for line in lines)

    return json_data_list


def replace_keys(original_json, key_map) -> dict:
    """Replace keys in the original JSON to hanshow keys based on the hs_datatype_key_map.json, and remove keys not in the key_map.

    Note: values that are empty, zero or zero-like are also removed.

    Parameters:
    - original_json: dict, the JSON object with original keys.
    - key_map: dict, a mapping of old keys to new keys.

    Returns:
    - A new dictionary with keys replaced according to the key_map, and keys not in the key_map removed.
    """
    new_json = {}

    for old_key, value in original_json.items():
        zero_pattern = re.compile(r'^0+(\.0+)?$')
        # Check if the old_key is in the key_map and the value is not empty or zero-like
        if old_key in key_map and not (value == 0 or value == "" or (isinstance(value, str) and zero_pattern.match(value))):
            new_key = key_map[old_key]
            if isinstance(value, dict):
                # Recursively replace keys in nested dictionaries
                new_json[new_key] = replace_keys(value, key_map)
            elif isinstance(value, list):
                # Replace keys in dictionaries within lists
                new_json[new_key] = [
                    replace_keys(item, key_map) if isinstance(
                        item, dict) else item
                    for item in value
                ]
            else:
                new_json[new_key] = value

    return new_json


def process_json(items: list[dict], file_typ: str) -> list[dict]:
    """process the JSON data based on the file type (ITM or PRM)

    Parameters:
    - items: list, the list of JSON data to process.
    - file_typ: str, the file type (ITM or PRM).

    Returns:
    - A list of updated JSON data with keys replaced from Bara Keys to Hanshow keys according to the hs_datatype_key_map.json.
    """

    key_map = {}

    # change the keys based on the file type
    if file_typ == "ITM":
        # read ITM key map json
        with open("keymap/ITM_keymap.json", "r") as f:
            key_map = json.load(f)
    elif file_typ == "PRM":
        with open("keymap/PRM_keymap.json", "r") as f:
            key_map = json.load(f)
    else:
        write_log("", "Failed when processing JSON data",
                  f"File type {file_typ} not supported.")
        return None

    updated_items = []

    for json_data in items:
        # Replace keys in the JSON data
        json_data = replace_keys(json_data, key_map)
        updated_items.append(json_data)

    return updated_items


def process_values(items: list[dict], document_name: str) -> list[dict]:
    """Process the values in the JSON data based on hs_datatype_key_map.json.

    Note: The value on Bara API is all string, so need to covert the value to the correct datatype for hanshow integration.

    strip() all the string values first, then process the values based on the data types.

    Parameters:
    - items: list, the list of JSON data to process.
    - document_name: str, the name of the document being processed.

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
                        dt = datetime.datetime.strptime(item[key], "%Y%m%d")

                        # Localize the datetime to Mexico City timezone
                        dt_localized = mexico_city_tz.localize(dt)

                        # Convert to UTC timestamp and then to milliseconds
                        timestamp = int(dt_localized.timestamp() * 1000)

                        item[key] = timestamp
                    elif datatype_keymap[key] == "enddate":
                        # Convert date format "20210101"11:59pm to timestamp in milliseconds
                        # Parse the input date string (YYYYMMDD) to a datetime object (midnight time by default)
                        dt = datetime.datetime.strptime(item[key], "%Y%m%d")

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

        # Todo: 在这里可以检查下 startdate，如果 startdate > today, 跳过这个item, 把这个 item 放到 pending_promo 文件里
        # Append the processed item to the list
        processed_items.append(item)

    return items


def send_integration(customer_code: str, store_code: str, client_id: str,
                     client_secret: str, items: list[dict], document_name: str) -> dict:
    """send integration to Hanshow Allstar via integration API.

    """

    base_url = "https://americas-poc.hanshowcloud.net/integration/"
    endpoint = f"{customer_code}/{store_code}"

    # Headers
    headers = {
        "Content-Type": "application/json",
        "client-id": client_id,
        "client-secret": client_secret
    }

    items_list = [items]

    # check if the items are more than 1000
    if len(items) > 1000:
        # if more than 1000, split the items into chunks of 1000
        items_list = [items[i:i + 1000] for i in range(0, len(items), 1000)]

    for item_batch in items_list:
        body = {
            "storeCode": store_code,
            "customerStoreCode": customer_code,
            "batchNo": datetime.datetime.now(mexico_city_tz).strftime("%Y%m%d%H%M%S"),
            "items": item_batch
            # Todo：如果 item_batch只有sku，跳过这个item
        }

        response = post_request(base_url, endpoint, headers, body)

        # if the integration is successful, write the document_name to log file for future reference
        if response["storeCode"] == store_code:
            print(f"{document_name} successfully integrated.")
            write_log(document_name, "success", customer_code, store_code)
        # if failed
        else:
            write_log(document_name, "failed", customer_code,
                      store_code, json.dumps(response))

    return response


def write_log(document_name, status, customer_code="", store_code="", error_message=None):
    # Generate log file name based on current date
    today = datetime.datetime.now(mexico_city_tz).strftime("%Y-%m-%d")
    log_filename = f"integration_{today}.log"

    # Ensure the log directory exists (create if not)
    log_directory = "logs"
    os.makedirs(log_directory, exist_ok=True)
    log_path = os.path.join(log_directory, log_filename)

    # Save record of document_names_fileType to log file for future reference
    with open(log_path, "a") as f:  # Append to the log file
        if status == "failed":
            time = datetime.datetime.now(
                mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"{time}: ERROR {document_name} failed to integrate to Customer: {customer_code}, Store: {store_code}. {error_message}\n")
        elif status == "success":
            time = datetime.datetime.now(
                mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"{time}: {document_name} successfully integrated to Customer: {customer_code}, Store: {store_code}.\n")


def main(customer_code: str, store_code: str, client_id: str, client_secret: str, bara_department_id, bara_store_id, bara_source, fileType) -> dict:
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
        # Process the values
        processed_json = process_values(processed_json, document_names[i])
        # Send the integration
        response = send_integration(
            customer_code, store_code, client_id, client_secret, processed_json, document_names[i])
        print(response)


if __name__ == "__main__":
    while True:
        now = datetime.datetime.now(
            mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
        print("------------------------------------")
        print(f"Now in UTC-6 Mexico City: {now}")

        customer_code = "Bara"
        client_id = "4cd23fb2d459abea9400d216a09071e6"
        client_secret = "1b179f2262c57028c11c74dfac8d9e3d"

        file_type = ["ITM"]
        store02_code = "52DUG"
        store03_code = "52RSW"

        print(f"Only integrate {file_type} files\n")

        print("Store 02 starts\n")
        try:
            main(customer_code, "02", client_id, client_secret,
                 "12NEO", store02_code, "CT", file_type)
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

        sleep_time = 900
        # Sleep for the next iteration
        print(
            f"Sleeping for the next period (in {int(sleep_time/60)} mins...)\n")
        time.sleep(sleep_time)
