import json

import requests
import time

server = "139.224.192.36"
login_api = "/api/v1/account/login"
port = "8082"
url = "http://" + server + ":" + port
test_api = 'http://139.224.192.36:8082/api/v1/pay/aliPaySign'
token = 'eyJhbGciOiJIUzI1NiJ9' \
        '.eyJhY2NvdW50SWQiOjI5MSwiYWNjb3VudCI6InRlc3QyIiwibG9naW5U ' \
        'eXBlIjozLCJ1c2VyVHlwZSI6MSwiaWF0IjoxNzQ0MjU1NDM5LCJuYmYiO' \
        'jE3NDQyNTU0MzksImV4cCI6MTc0Njg0NzQzOX0.q0Z_KZWT-NoA0L' \
        '6TVVVTAxOw3wKTHRLp5fOwJP7y7x8'
userAgent = 'Mozilla/5.0 (Linux; Android 15; SM-S9380 Build/AP3A.240905.0' \
            '15.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 ' \
            'Chrome/134.0.6998.135 Mobile Safari/537.36 uni-app Html5Plu' \
            's/1.0 (Immersed/30.133333)'
content_type = 'application/json'

header = {
    "User-Agent": userAgent,
    "Content-Type": content_type,
    "X-TOKEN": token
}


def login():
    api = login_api
    login_url = url + api
    data = json.dumps({"account": "test2@tester.com", "password": "sf123123", "areaCode": "+86", "loginType": 3})
    response = requests.post(url=login_url, data=data, headers=header)
    tx = response.json()['data']
    header['X-TOKEN'] = tx
    print(header)


login()

payload = {
    "paymentClientType": 2,
    "orderNo": "S25041110494884",
    "payAmount": 0.01,
    "orderId": 0,
    "ordersState": 0,
    "orderTitle": "Pintura Life ¥0.01/month,100GB云空间",
    "outOrdersNo": "string",
    "ordersType": 1
}

start_time = time.time()
response = requests.post(url=test_api, headers=header, json=payload)

end_time = time.time()
consume_time = round((end_time - start_time) * 1000, 2)

print(f"consume_time: {consume_time} ms")
