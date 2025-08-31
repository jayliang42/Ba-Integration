from datetime import datetime
import base64
import gzip
import json
import re
from log_helper import write_log
from credentials import mexico_city_tz
from refresh_date import if_refresh


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
        if old_key in key_map and (old_key == "type" or not (value == 0 or value == "" or (isinstance(value, str) and zero_pattern.match(value)))):
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
                        dt = datetime.strptime(item[key], "%Y%m%d")
                        dt = dt.replace(hour=0, minute=0, second=0)
                        dt_localized = mexico_city_tz.localize(dt, is_dst=None)
                        timestamp = int(dt_localized.timestamp() * 1000)
                        item[key] = timestamp
                    elif datatype_keymap[key] == "enddate":
                        # Convert date format "20210101"11:59pm to timestamp in milliseconds
                        dt = datetime.strptime(item[key], "%Y%m%d")
                        dt = dt.replace(hour=23, minute=59, second=59)
                        dt_localized = mexico_city_tz.localize(dt, is_dst=None)
                        timestamp = int(dt_localized.timestamp() * 1000)
                        item[key] = timestamp
                except ValueError as e:
                    write_log(document_name, "failed",
                              f"Error processing key {key}: {e}")
                    del item[key]
        # Todo: add concurrency here. Using python multithreading.
        item = if_refresh(item, store_code)
        if item:
            # Append the processed item to the list
            processed_items.append(item)

    return processed_items
