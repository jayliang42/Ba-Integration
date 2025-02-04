import datetime
from time import sleep
import pytz
from allstar_login_credentials import get_token as get_allstar_bearer_token, send_post_request, send_get_request
from bara_integration import append_json_item

mexico_city_tz = pytz.timezone("America/Mexico_City")


def get_all_items(customer_code: str, store_code: str, headers: dict) -> list[dict]:
    """get all items from allstar API"""
    items = []
    pageNum = 1
    print(
        f"getting items from allstar {customer_code} {store_code}", end="", flush=True)
    while True:
        url = f"https://americas-poc.hanshowcloud.net/proxy/allstar/v3/articles/{customer_code}/{store_code}/complex-with-blob-picture?pageNum={pageNum}&pageSize=1000"
        data = {"queryType": "SIMPLE", "logic": [], "params": []}

        response = send_post_request(url, data, headers).json()
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
            "batchNo": datetime.datetime.now(mexico_city_tz).strftime("%Y%m%d%H%M%S"),
            "items": item_batch
        }

        response = send_post_request(base_url + endpoint, body, headers)

    return response


def check_promo_switch(customer_code: str, store_code: str, headers: dict):
    # Q:如果是促销期结束切换成正常模版的那个日期怎么办？
    # 每天晚上11点检测一下所有的商品，如果是促销期结束，那么就切换成正常模版，rsrvTxt2是促销结束日期
    items = get_all_items(customer_code, store_code, headers)
    timestamp_now = int(datetime.datetime.now(
        mexico_city_tz).timestamp() * 1000)
    print("checking promo switch", flush=True)
    for item in items:
        # 先判断是否在促销
        if "saleMode" in item and "promoDateFrom" in item:
            # item
            if item["saleMode"] != "00" and item["promoDateFrom"] < timestamp_now and item["promoDateTo"] > timestamp_now:
                # 如果目前正在促销，但是促销日期明天就到了，那么就切换成正常模版
                if item["promoDateTo"] < timestamp_now + 86400000:
                    # convert promoDateTo to dd/mm
                    promoDateTo = datetime.datetime.fromtimestamp(
                        item["promoDateTo"] / 1000).strftime("%d/%m")
                    new_item = {"sku": item["sku"], "rsrvTxt2": promoDateTo}
                    # 把它加进 pending promo 就好
                    # Todo: Pending Promo那是通过 promoDateFrom 来判断的，
                    # 这里不加 promoDateFrom，pending promo 那就会卡住。
                    # 需要换一个方法
                    pending_file_path = f"current_files/{store_code}/pending_promo/pending_promo.json"
                    append_json_item(pending_file_path, new_item)
                    print(
                        f"append {new_item} to pending_promo.json", flush=True)


if __name__ == '__main__':
    customer_code = "Bara"
    client_id = "4cd23fb2d459abea9400d216a09071e6"
    client_secret = "1b179f2262c57028c11c74dfac8d9e3d"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {get_allstar_bearer_token()}"}

    store_code = ["01"]
    for store in store_code:
        check_promo_switch(customer_code, store, headers)
