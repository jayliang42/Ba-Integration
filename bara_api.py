from datetime import datetime
import time
import os
import requests
import warnings
from urllib3.exceptions import InsecureRequestWarning
import retrying
from log_helper import write_log
from credentials import mexico_city_tz

# Suppress the insecure request warning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)


@retrying.retry(wait_fixed=5000, stop_max_attempt_number=3)
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

    try:
        # Make the POST request
        response = requests.post(url, headers=headers,
                                 json=body, auth=auth, verify=False, timeout=30)

        # Check if the request is successful
        if response.status_code != requests.codes.ok:
            error_msg = f"HTTP {response.status_code} error for URL {url}: {response.text}"
            print(f"Error: {response.status_code} - {response.text}")
            write_log("API request", "failed", error_message=error_msg)
            raise Exception(f"Request failed with status {response.status_code}")

        # Return the response in JSON format if successful
        return response.json()
        
    except requests.exceptions.Timeout:
        error_msg = f"Request timeout (30s) for URL: {url}"
        print(f"Error: Request timeout for {url}")
        write_log("API request", "failed", error_message=error_msg)
        raise Exception("Request timeout")
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error for URL {url}: {str(e)}"
        print(f"Error: Connection failed for {url}: {str(e)}")
        write_log("API request", "failed", error_message=error_msg)
        raise Exception("Connection error")
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request exception for URL {url}: {str(e)}"
        print(f"Error: Request failed for {url}: {str(e)}")
        write_log("API request", "failed", error_message=error_msg)
        raise Exception(f"Request exception: {str(e)}")
        
    except ValueError as e:
        error_msg = f"JSON decode error for URL {url}: {str(e)}"
        print(f"Error: Invalid JSON response from {url}: {str(e)}")
        write_log("API request", "failed", error_message=error_msg)
        raise Exception("Invalid JSON response")


def get_Bara_bearer_token() -> str:
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
        "x-Gateway-APIKey": "66001b2d-7410-4588-a404-6db151febc9b",
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
        "x-Gateway-APIKey": "66001b2d-7410-4588-a404-6db151febc9b",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "MyApp/1.0 (Windows NT 10.0; Win64; x64)"
    }

    document_data_list = []

    for document in document_name_list:
        print(f"Downloading {document}...")
        # wait for 1 second before making the next request，to avoid the rate limit
        time.sleep(1)
        
        try:
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
            
            # Check if response contains the expected data
            if "documents" in response and len(response["documents"]) > 0 and "data" in response["documents"][0]:
                # record the base64 data
                document_data_list.append(response["documents"][0]["data"])
                print(f"✓ Successfully downloaded {document}")
                write_log(f"Download {document}", "success", store_id, department_id, f"Document {document} downloaded successfully")
            else:
                error_msg = f"Invalid response format for {document}: {response}"
                print(f"✗ Failed to download {document}: Invalid response format")
                write_log(f"Download {document}", "failed", store_id, department_id, error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            error_msg = f"Error downloading {document}: {str(e)}"
            print(f"✗ Failed to download {document}: {str(e)}")
            write_log(f"Download {document}", "failed", store_id, department_id, error_msg)
            # Re-raise the exception to stop the process
            raise Exception(error_msg)

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

    bearer_token = get_Bara_bearer_token()

    # Base URL
    base_url = "https://api.oxxo.io/xapi-multichannel-outbound/api/v1"

    # url endpoint
    url_endpoint = "/documents"

    # Get the document list
    document_list = get_document_list(
        base_url, url_endpoint, bearer_token, department_id=bara_department_id, source=source, store_id=bara_store_id)

    def filter_documents(documents, store_code=store_code):
        # only get the documents with today's date
        today = datetime.now(mexico_city_tz).strftime("%y%m%d")

        # read historical_files/{store_code}.txt
        # filter documents that are already integrated
        historical_file = f"historical_files/{store_code}.txt"
        existed_documents = []
        if os.path.exists(historical_file):
            with open(historical_file, "r") as f:
                existed_documents = f.readlines()
                existed_documents = [doc.strip() for doc in existed_documents]

        documents = [doc for doc in documents if doc["name"].replace(
            ".gz", "") not in existed_documents]

        print(f"{len(documents)} documents found in Bara DB.\n")
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
            print(
                f"Document {doc['name']} with fileType {doc['fileType']} not in the list. Skipped.")

    # Get the document names based on the file type filtered
    document_names = list(document_names_fileType.keys())

    print(f"\nDocument names going to integrate: {document_names}\n")

    # Get the document base64 data
    document_data_list = get_document_base64_data(base_url, "/documents/downloads",
                                                  bearer_token, document_names, department_id=bara_department_id, source=source, store_id=bara_store_id)

    # return the base64 data and the document names with fileType
    return document_data_list, document_names_fileType
