import warnings
import requests
import json
import retrying
from urllib3.exceptions import InsecureRequestWarning


warnings.filterwarnings('ignore', category=InsecureRequestWarning)


'''get token'''


@retrying.retry(wait_fixed=2000, stop_max_attempt_number=5)
def send_post_request(url, data, headers):
    response = requests.post(url, json=data, headers=headers, verify=False)
    # check if the request is successful
    if response.status_code != requests.codes.ok:
        print(response.status_code)
        raise Exception("request failed.")
    return response.json()


def send_get_request(url, headers):
    response = requests.get(url, headers=headers, verify=False)
    # check if the request is successful
    if response.status_code != requests.codes.ok:
        print(response.status_code)
        raise Exception("request failed.")
    return response.json()


def get_token(username="admin", password="5E811B934DC5B6465A2B9E482DC06D5B"):
    # request from as to get token
    loginResponse = send_post_request("https://americas-poc.hanshowcloud.net/proxy/allstar/user/login", {"username": username, "password": password},
                                      {"Content-Type": "application/json"})
    access_token = loginResponse['data']['access_token']

    # refresh_token = json.loads(loginResponse.text)['data']['refresh_token']
    return access_token


def get_saasprd_token(username="superuser-douhongjie", password="b7fefafbb876eb8adcc16d8a4ccc2ff7"):
    # request from ps to get token
    loginResponse = send_post_request("https://saas-poc-usa.hanshowcloud.net/prismart/weblogin", {"username": username, "password": password},
                                      {"Content-Type": "application/json"})
    access_token = json.loads(loginResponse.text)['data']['jsessionid']
    # refresh_token = json.loads(loginResponse.text)['data']['refresh_token']
    return access_token


def send_delete_request(url, headers, body):
    response = requests.delete(url, headers=headers, json=body, verify=False)
    # check if the request is successful
    if response.status_code != requests.codes.ok:
        print(response.status_code)
        raise Exception("request failed.")
    return response.json()
