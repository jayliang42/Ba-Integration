from datetime import datetime
import os
from credentials import mexico_city_tz


def write_log(document_name, status, customer_code="", store_code="", error_message=None):
    # Generate log file name based on current date
    today = datetime.now(mexico_city_tz).strftime("%Y-%m-%d")
    log_filename = f"integration_{today}.log"

    # Ensure the log directory exists (create if not)
    log_directory = "logs/integration"
    os.makedirs(log_directory, exist_ok=True)
    log_path = os.path.join(log_directory, log_filename)

    # Save record of document_names_fileType to log file for future reference
    with open(log_path, "a") as f:  # Append to the log file
        if status == "failed":
            time = datetime.now(
                mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"{time}: ERROR {document_name} failed to integrate to Customer: {customer_code}, Store: {store_code}. {error_message}\n")
        elif status == "success":
            time = datetime.now(
                mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"{time}: {document_name} successfully integrated to Customer: {customer_code}, Store: {store_code}.\n")
        elif status == "skipped":
            time = datetime.now(
                mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
            f.write(
                f"{time}: SKIPPED {document_name} for Customer: {customer_code}, Store: {store_code}. {error_message}\n")
