# read historical_files/store_id.txt
import os

store_code = "02"

historical_file = f"historical_files/{store_code}.txt"
existed_documents = []
if os.path.exists(historical_file):
    with open(historical_file, "r") as f:
        existed_documents = f.readlines()
        existed_documents = [doc.strip() for doc in existed_documents]


print(existed_documents)
