import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

headers = {
    "content-type": "application/json",
    "Accept": "*/*",
    "accept-encoding": "gzip, deflate",
    "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "cache-control": "no-cache",
    "cookie": "sidebarStatus=0",
    "Dnt": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 "
                  "Safari/537.36 Edg/131.0.0.0"
}


def login(account="admin", password="1662810347189AHIO"):
    url = "http://139.224.192.36:18083/api/v5/login"
    body = {
        "password": password,
        "username": account
    }
    result = requests.post(url, json=body)
    token = result.json()['token']
    global headers
    headers["Authorization"] = "Bearer " + token
    return token


def get_clients():
    clients_list = []
    url = "http://139.224.192.36:18083/api/v5/clients?limit=1000&page=1"
    result = requests.get(url, headers=headers)
    clients = result.json()["data"]
    for i in clients:
        if "conn_" in i["clientid"]:
            clients_list.append(i["clientid"])
    return clients_list


def del_client(client_id):
    url = f"http://139.224.192.36:18083/api/v5/clients/{client_id}"
    try:
        result = requests.delete(url, headers=headers, timeout=10)
        if result.status_code == 204:
            print(f"{client_id} 删除成功")
        else:
            print(f"{client_id} 删除失败, 状态码: {result.status_code}")
    except requests.RequestException as e:
        print(f"{client_id} 删除失败, 错误: {e}")


def main():
    # 登录并获取token
    login()

    # 获取客户端列表
    client_list = get_clients()

    # 使用多线程删除客户端
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(del_client, client_id) for client_id in client_list]

        # 可选：等待所有任务完成
        for future in as_completed(futures):
            pass


if __name__ == "__main__":
    main()