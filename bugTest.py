import requests
import json
import sys
import time


def second_time():
    try:
        second = float(input("是否需要增加接口延时？\n如需增加请输入数字,非数字为不设置延时："))
        if isinstance(second, float) or isinstance(second, int):
            pass
        else:
            second = 0
        return second
    except:
        second = 0
        return second

def bug_test(second):
    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, "
                      "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                      "Immersed/34.909092)",
        "X-TOKEN": "",
    }
    server = "139.224.192.36"
    api = "/api/v1/account/login"
    port = "8082"
    url = "http://" + server + ":" + port + api
    username = "15250996938"
    password = "sf123123"
    data = json.dumps({"account": username, "password": password, "areaCode": "+86", "loginType": 2})
    print(f"url：{url}, data：{data}")
    response = requests.post(url=url, data=data, headers=headers)
    if response.status_code == 200:
        s = response.json()
        token = s['data']
        headers['X-TOKEN'] = token
    else:
        input("登录接口异常，按回车退出")
        sys.exit()

    # 重置图片
    api = "/api/v1/host/screen/reset/picture"
    url = "http://" + server + ":" + port + api
    data = json.dumps({"screenId": "AE86GTR1X000233"})
    response = requests.post(url=url, data=data, headers=headers)
    print(response.text)
    if response.status_code == 200:
        s = response.json()
        code = s['code']
        if code == 20:
            print("图片已重置！")
        else:
            print("重置图片失败！")
    else:
        input("图片重置接口异常，按回车退出")
        sys.exit()
    time.sleep(second)
    # 上传图片
    api = "/api/v1/host/screen/update/pictureV3"
    url = "http://" + server + ":" + port + api
    data = json.dumps([{"pictureFileId": "249_u6AX2rih17150688059730", "pictureSeq": 1, "screenDeviceId":
        "AE86GTR1X000233"}])
    response = requests.post(url=url, data=data, headers=headers)
    print(response.text)
    if response.status_code == 200:
        s = response.json()
        code = s['code']
        if code == 20:
            print("图片上传成功！")
        else:
            print("图片上传失败！")
    else:
        input("图片上传接口异常，按回车退出")
        sys.exit()


n = 0
second = second_time()
while True:
    bug_test(second)
    n = n + 1
    print("第" + str(n) + "次测试完成")
    print(f"延时：{second}秒")
    choice = input("按回车键继续，输入q退出，输入time重新设置延时：\n")
    if choice == 'q':
        break
    elif choice == 'time':
        second = second_time()
    else:
        continue
