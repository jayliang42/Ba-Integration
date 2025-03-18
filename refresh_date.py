import concurrent.futures
from datetime import datetime
import json
import os
from allstar_login_credentials import get_token as get_allstar_bearer_token, send_post_request
from credentials import mexico_city_tz


def get_allstar_data(store_code, sku):
    # get allstar data from allstar API
    url = f"https://americas-poc.hanshowcloud.net/proxy/allstar/v3/articles/Bara/{store_code}/complex-with-blob-picture?pageNum=1&pageSize=10"
    data = {"queryType": "SIMPLE", "logic": [], "params": [
        {"key": "articleId", "value": sku, "op": 0}]}
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_allstar_bearer_token()}"}

    response = send_post_request(url, data, headers)

    if response["data"]["pageData"] != []:
        # get the target data from allstar data
        allstar_itemdata = response["data"]["pageData"][0]["attribute"]
        return allstar_itemdata

    # sku not found
    return "SKU not found"


def refresh_by_price(sku, price1="0", rsrvDec1="0", saleMode="-1", store_code="01"):
    price1 = str(price1)
    rsrvDec1 = str(rsrvDec1)
    allstar_data = get_allstar_data(store_code, sku)

    # if not found in allstar, 100% refresh
    if allstar_data == "SKU not found":
        return True

    allstar_price1 = allstar_data.get("price1", "Target data not found")
    allstar_rsrvDec1 = allstar_data.get("rsrvDec1", "Target data not found")
    allstar_saleMode = allstar_data.get("saleMode", "Target data not found")

    # determine if the item is in promotion period
    allstar_isPromo = False

    allstar_promoDateTo = allstar_data.get(
        "promoDateTo", "Target data not found")

    if allstar_promoDateTo != "Target data not found" and allstar_promoDateTo > int(datetime.now(mexico_city_tz).timestamp() * 1000) and allstar_saleMode != "00":
        allstar_isPromo = True
    """-----------------------------------------------------------------"""

    if allstar_isPromo:
        # 在促销模版中
        if rsrvDec1 != allstar_rsrvDec1 and rsrvDec1 != "0":
            # rsrvDec1变动，刷新
            print(
                f"{sku} in promo，rsrvDec1 has changed，ESL refresh by price changing。原:{allstar_rsrvDec1}:现{rsrvDec1}")
            return True
        elif saleMode == "00":
            #  新推进来的saleMode == "00"，切换回正常模版，刷新
            print(
                f"{sku} in promo，saleMode change to 00，stop promo, ESL refresh by price changing。原:{allstar_saleMode}:现{saleMode}")
            return True
    else:
        # 在正常模版
        if price1 != allstar_price1 and price1 != "0":
            # price1 变动，刷新
            print(
                f"{sku} not in promo，price1 has changed，ESL refresh by price changing。原:{allstar_price1}:现{price1}")
            return True
        # 有 salesmode 进来的时候，都是 promo file 对进来的时候，
        # 因为我的 pending file 机制，所以，这个时候肯定是会切换成促销模版的
        if saleMode != "00" and saleMode != "-1":
            # 开始切换成促销模版，刷新
            print(
                f"{sku} not in promo，saleMode has changed to promo，ESL refresh by price changing。原:{allstar_saleMode}:现{saleMode}")
            return True

        # 第 5 种情况，当促销结束，价签刷新回正常模版时，价格刷新。
        # 由 daily check 模块来检查并对接这种情况。

    # 其余情况不刷新
    return False


def append_json_item(file_path: str, item: dict):
    """
    Append a JSON item to a JSON file, ensuring the file contains a valid JSON array.

    Parameters:
    - file_path: str, the path to the JSON file.
    - item: dict, the JSON object to append.
    """
    # Check if the file exists and load its current contents (if any)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            try:
                data = json.load(f)  # Load the existing JSON data
                if not isinstance(data, list):
                    raise ValueError(
                        "JSON file does not contain a valid array")
            except (json.JSONDecodeError, ValueError):
                # If the file is invalid or not a list, start with an empty list
                data = []
    else:
        # If the file doesn't exist, initialize an empty list
        data = []

    # Append the new item
    data.append(item)

    # Write the updated list back to the file
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)


def if_refresh(item, store_code):
    """Determine whether an item needs to be refreshed based on promotion or effective date."""

    pending_file_path = f"current_files/{store_code}/pending_promo/pending_promo.json"
    item_keys = set(item.keys())  # 使用 set 提高查找效率
    now = datetime.now(mexico_city_tz)

    # promoFile
    if "promoDateFrom" in item_keys:
        # Pending promo: Check if promoDateFrom is in the future
        if item["promoDateFrom"] > int(now.timestamp() * 1000):
            promo_date = datetime.fromtimestamp(
                item["promoDateFrom"] / 1000, tz=mexico_city_tz)

            if {"rsrvDec1", "saleMode"} & item_keys:  # 如果包含 rsrvDec1 或 saleMode
                is_refresh = refresh_by_price(
                    item["sku"],
                    rsrvDec1=item.get("rsrvDec1", "0"),
                    saleMode=item.get("saleMode", "0"),
                    store_code=store_code
                )
                if is_refresh:
                    item["rsrvTxt2"] = promo_date.strftime("%Y/%m/%d")

            print(
                f"Promotion {item['sku']} is not ready to start. {promo_date.strftime('%Y/%m/%d')} is in the future.")
            append_json_item(pending_file_path, item)
            return None
        # Immediate promo update scenario
        else:
            is_refresh = refresh_by_price(
                item["sku"],
                rsrvDec1=item.get("rsrvDec1", "0"),
                saleMode=item.get("saleMode", "0"),
                store_code=store_code
            )

            if is_refresh:
                item["rsrvTxt2"] = now.strftime("%Y/%m/%d")

            return item

    # ITM file
    elif "rsrvTxt3" in item_keys:
        rsrv_date = datetime.strptime(item["rsrvTxt3"], "%Y%m%d")
        rsrv_date = mexico_city_tz.localize(rsrv_date)  # 使其具有时区信息
        today_date = now.replace(
            hour=0, minute=0, second=0, microsecond=0)  # 仅保留日期部分

        # pending price change
        if rsrv_date > today_date:
            # Future effective date → Add to pending promo
            if {"price1", "itemName"} & item_keys:
                refresh_date = rsrv_date.strftime("%Y/%m/%d")
                item.pop("rsrvTxt3")
                item["rsrvTxt2"] = refresh_date
                print(
                    f"Item {item['sku']} is not ready to change price. {refresh_date} is in the future.")
                append_json_item(pending_file_path, item)
            return None
        # Immediate price update scenario
        else:
            is_refresh = "price1" in item_keys and refresh_by_price(
                item["sku"], price1=item["price1"], store_code=store_code
            )

            if is_refresh:
                item["rsrvTxt2"] = now.strftime("%Y/%m/%d")
            return item
