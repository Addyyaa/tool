import requests
import json
import sys
import time
import ast
import re


def getApi():
    while True:
        api = input("请输入接口地址(如：http://101.132.97.199:8082/api/v1/manage/materialLibrary：")
        if 'api' in api:
            break
        else:
            print("请输入正确的接口地址")
    return api


def getData():
    while True:
        data1 = input("请输入参数体，参数值后方添加*号则自动给该参数值添加后缀-根据数量自动添加，如：\n方式一、username:admin "
                      "password:test123\n方式二、username:admin* password:test123\n方式二主要应用于创建多条数据时使用\n请输入参数体：")
        # 分解参数
        data_dict = {}
        if data1 != "":

            for pair in data1.split():
                if ':' in pair:
                    key, value = pair.split(':', 1)
                    # 处理列表格式的值
                    if value.startswith('[') and value.endswith(']'):
                        try:
                            # 使用 ast.literal_eval 安全地将字符串转换为列表
                            value = ast.literal_eval(value)
                        except (ValueError, SyntaxError):
                            # 如果转换失败，保留原始值
                            pass
                    data_dict[key] = value
            break
        else:
            print("请输入正确的数据")
    return json.dumps(data_dict)


def num_of_create():
    num = 0
    while True:
        try:
            num = int(input("请输入创建数量："))
            if num != "":
                break
            else:
                print("请输入正确的创建数量")
        except:
            print("请输入正确的创建数量")
            continue

    return num


def get_token():
    login_api = 'http://101.132.97.199:8082/api/v1/manage/system/auth/login'
    login_data = json.dumps({"username": "sysadmin", "password": "OST139.224.192.36"})
    header = {
        "Content-Type": "application/json"
    }
    response = requests.post(url=login_api, data=login_data, headers=header)
    if response.status_code == 200:
        s = response.json()
        token = s['data']
        return token
    else:
        print(response.text)
        input("登录接口异常，按回车退出")
        sys.exit()


def request():
    token = get_token()
    api = getApi()
    data = getData()
    num = num_of_create()
    datas = []
    if '*' in data:
        for i in range(num):
            datas.append(data.replace('*', str(i)))
    else:
        for i in range(num):
            datas.append(data)
    headers = {
        "Content-Type": "application/json",
        "X-Token": token
    }
    for i in datas:
        print(i)
        response = requests.post(url=api, data=i, headers=headers)
        if response.status_code == 200:
            if response.json()['code'] == 20:
                print("创建成功！")
            else:
                print("创建失败！")
                print(response.text)
        else:
            print(response.text)
            input("创建接口异常，按回车退出")
            sys.exit()
        time.sleep(1)


if __name__ == '__main__':
    request()
