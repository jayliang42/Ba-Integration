import json
from bara_integration import get_bearer_token, get_document_base64_data, convert_base64_to_json


def check_files(bara_store_id, document_names):
    bearer_token = get_bearer_token()

    # Base URL
    base_url = "https://api.oxxo.io/xapi-multichannel-outbound/api/v1"

    bara_department_id = "12NEO"

    source = "CT"

    # Get document base64 data
    document_base64_data = get_document_base64_data(base_url, "/documents/downloads",
                                                    bearer_token, document_names, bara_department_id, source, bara_store_id)

    for i, document in enumerate(document_base64_data):
        document_name = document_names[i].replace(".json.gz", "")
        # convert base64 to json
        document = convert_base64_to_json(document)
        # save document to json file
        with open(f"z_checkfiles/{document_name}.json", "w") as file:
            # dump dict to json file
            json.dump(document, file, indent=4)


def main(store_code, document_list):
    # store02_code = "52DUG"
    # store03_code = "52RSW"
    check_files(store_code, document_list)


main("52DUG", ["PRM12NEO52DUG241204135245.json.gz"])
# main("52RSW", ["PRM12NEO52RSW241204135246.json.gz"])
