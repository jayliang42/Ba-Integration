from datetime import datetime, timedelta
import json
import os
from time import sleep

import pytz
from allstar_login_credentials import get_token as get_allstar_bearer_token, send_post_request
from refresh_date import append_json_item
from credentials import mexico_city_tz, customer_code
from log_helper import write_log


def get_all_items(customer_code: str, store_code: str, headers: dict) -> list[dict]:
    """get all items from allstar API"""
    items = []
    pageNum = 1
    print(
        f"getting items from allstar {customer_code} {store_code}")
    while True:
        url = f"https://americas-poc.hanshowcloud.net/proxy/allstar/v3/articles/{customer_code}/{store_code}/complex-with-blob-picture?pageNum={pageNum}&pageSize=1000"
        data = {"queryType": "SIMPLE", "logic": [], "params": []}

        response = send_post_request(url, data, headers)
        if response["data"]["pageData"] != []:
            # get the target data from allstar data
            allstar_itemdata = response["data"]["pageData"]
            for item in allstar_itemdata:
                items.append(item["attribute"])
        else:
            break
        pageNum += 1

    return items


def send_integration(customer_code: str, store_code: str, client_id: str,
                     client_secret: str, items: list[dict]) -> dict:
    """send integration to Hanshow Allstar via integration API."""

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

        response = send_post_request(base_url + endpoint, body, headers)
        # if the integration is successful, write the document_name to log file for future reference
        if response["storeCode"] == store_code:
            print(f"pending files successfully integrated.")
            print(response)
            write_log("pending files", "success", customer_code, store_code)

    return response


def check_promo_switch(customer_code: str, store_code: str, headers: dict):
    # Q:如果是促销期结束切换成正常模版的那个日期怎么办？
    # 每天晚上11点检测一下所有的商品，如果是促销期结束，那么就切换成正常模版，rsrvTxt2是促销结束日期
    items = get_all_items(customer_code, store_code, headers)
    timestamp_now = int(datetime.now(
        mexico_city_tz).timestamp() * 1000)
    print("checking promo switch\n")

    pending_file_path = f"current_files/{store_code}/pending_promo/pending_promo.json"

    # read all skus in pending promo.
    if os.path.exists(pending_file_path):
        with open(pending_file_path, "r", encoding="utf-8") as f:
            try:
                pending_data = json.load(f)
            except json.JSONDecodeError:
                pending_data = []
    else:
        pending_data = []

    pending_skus = {item["sku"] for item in pending_data}

    oneday_duration_tsms = 86400000

    for item in items:
        if "saleMode" in item and "promoDateFrom" in item:
            # It is in promotion
            if item["saleMode"] != "00" and item["promoDateFrom"] < timestamp_now and item["promoDateTo"] > timestamp_now:
                # Promo ends within a day.
                if item["promoDateTo"] < timestamp_now + oneday_duration_tsms:
                    dt_promo_to = datetime.fromtimestamp(
                        item["promoDateTo"] / 1000, tz=pytz.utc)
                    dt_in_mexico = dt_promo_to.astimezone(mexico_city_tz)
                    refresh_date = (
                        dt_in_mexico + timedelta(days=1)).strftime("%Y/%m/%d")
                    new_item = {"sku": item["sku"], "rsrvTxt2": refresh_date}

                    # make sure there's no dulicate sku.
                    if new_item["sku"] not in pending_skus:
                        append_json_item(pending_file_path, new_item)
                        print(
                            f"append {new_item} to pending_promo.json")
                        print(
                            f"[{item['sku']}] promo ends on (MX): {dt_in_mexico.strftime('%Y-%m-%d %H:%M:%S')}, switch to normal on {refresh_date}")


def check_pending_files(customer_code: str, store_code: str, client_id: str, client_secret: str):
    """ Check pending_promo files and integrate the pending_promo items

    Parameters:
    - customer_code: str, the customer code for the integration.
    - store_code: str, the store code for the integration.
    - client_id: str, the client ID for the integration.
    - client_secret: str, the client secret for the integration.

    """
    pending_items = []
    now = int(datetime.now().timestamp() * 1000)
    file_path = f"current_files/{store_code}/pending_promo/pending_promo.json"

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            pending_promo = json.load(f)
            print(f"Found {len(pending_promo)} pending items.")

            for promo in pending_promo[:]:
                if "promoDateFrom" in promo and promo["promoDateFrom"] <= now:
                    pending_items.append(promo)
                # promo结束刷新日期, 或者 itm 变价日期
                elif "promoDateFrom" not in promo and "rsrvTxt2" in promo:
                    rsrvTxt2_time = int(datetime.strptime(
                        promo["rsrvTxt2"], "%Y/%m/%d").timestamp() * 1000)
                    if rsrvTxt2_time <= now:
                        pending_items.append(promo)

        if pending_items:
            print(f"Integrating {len(pending_items)} pending files...\n")
            response = send_integration(
                customer_code, store_code, client_id, client_secret, pending_items)

            if "errorCode" not in response:  # if integration success, delete the pending items.
                pending_promo = [
                    promo for promo in pending_promo if promo not in pending_items]
                with open(file_path, "w") as f:
                    json.dump(pending_promo, f, indent=4)
            else:
                print("Integration failed. Keeping pending items.")
        else:
            print("No pending files to integrate.")


if __name__ == '__main__':
    now = datetime.now(
        mexico_city_tz).strftime("%Y-%m-%d %H:%M:%S")
    print("------------------------------------")
    print(f"Now in UTC-6 Mexico City: {now}")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_allstar_bearer_token()}"}

    store_code = ["01", "02", "03"]
    for store in store_code:
        print(f"store: {store}")
        check_promo_switch(customer_code, store, headers)
    print("------------------------------------")
