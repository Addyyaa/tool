import json
import logging
import os
import random
import string
import sys
import telnetlib
import tkinter as tk
from tkinter import filedialog
import cv2
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)

headers = {
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/34.909092)",
}

qiniu_headers = {
    "Accept-Encoding": "gzip",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 (Immersed/34.909092)",
    "host": "up-z2.qiniup.com",
    'Connection': 'Keep-Alive',
    'Charset': 'UTF-8',
}

server = "139.224.192.36"
port = "8082"
groupid = ""
body_data = {
    "account": "",
    "password": "",
    "areaCode": "+86",
    "loginType": "2"
}
login_interface = "http://" + server + ":" + port + "/api/v1/account/login"
get_device = "http://" + server + ":" + port + "/api/v1/host/screen/group/device/list"
screen_list = 'http://' + server + ":" + port + "/api/v1/host/screen/group/list/relationWithVersion?screenGroupId="
display = 'http://' + server + ":" + port + "/api/v1/host/screen/update/display"
album_list = 'http://' + server + ":" + port + '/api/v1/photo/list'
qiniu_filesystem = 'http://up-z2.qiniup.com'
qiniu_token = 'http://' + server + ":" + port + '/api/v1/files/token?code=86'
meta_api = 'http://' + server + ":" + port + '/api/v1/capacity/file/meta'  # 入参列表元素：fileId width height fileType-1 storageType-1 fileName-fileId contentType-image/jpeg fileSize-bianliang
upload_ok = 'http://' + server + ":" + port + '/api/v1/photo/'  # message成功
user_id_api = 'http://' + server + ":" + port + '/api/v1/user/profile'
get_screen_picture = 'http://' + server + ":" + port + '/api/v1/host/screen'
video_to_commit = 'http://' + server + ":" + port + '/api/v1/screenVideo/publish/increment'
get_album_images = 'http://' + server + ":" + port + '/api/v1/photo/info?albumId='
album_picture_to_screen = 'http://' + server + ":" + port + '/api/v1/screenPicture/publish'
qiuniutoken = None
del_album_picture = 'http://' + server + ":" + port + '/api/v1/photo/'


def login(account="shenfeng@austinelec.com", password="sf58595211"):
    if '@' in account:
        body_data.pop('areaCode')
        body_data['loginType'] = '3'
    else:
        body_data['areaCode'] = '+86'
    body_data["account"] = account
    body_data["password"] = password
    response = requests.post(login_interface, json=body_data, headers=headers)
    if response.status_code == 200:
        rp = response.json()
        # 提取token
        token = rp["data"]
        headers['X-TOKEN'] = token
        return True
    else:
        print(response.text)
        return False


def get_user_id():
    response = requests.get(user_id_api, headers=headers)
    if response.status_code == 200:
        rp = response.json()
        user_id = rp["data"]["userId"]
        return user_id
    else:
        print(response.text)


def get_qiniu_token():
    response = requests.get(qiniu_token, headers=headers)
    print(response.text)
    if response.status_code == 200:
        rp = response.json()
        token = rp["data"]
        return token
    else:
        print(response.text)


def get_album_id():
    response = requests.get(album_list, headers=headers)
    if response.status_code == 200:
        rp = response.json()
        albums = rp["data"]
        for index, album in enumerate(albums):
            if album['albumId']:
                print(f"{index + 1}：{album['albumName']}  相册ID：{album['albumId']} coverId：{album['coverFileId']}")
        while True:
            op = input("请选择：")
            if op in [str(i) for i in range(1, len(albums) + 1)]:
                op = int(op) - 1
                break
        album_id, cover_id = albums[op]['albumId'], albums[op]['coverFileId']
        global upload_ok
        upload_ok = upload_ok + str(album_id)
        return album_id, cover_id

    else:
        print(response.text)


# 用户选择图片
def select_images():
    try:
        print("Initializing Tkinter...")
        root = tk.Tk()
        print("Tkinter initialized.")
        root.withdraw()
        print("Root window withdrawn.")
        root.update()  # Ensure root window is fully created
        print("Root window updated.")
        files = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.mp4")]
        )
        print("File dialog opened.")
        root.destroy()
        print("Root window destroyed.")
        if files:
            print(f"选择的文件: {files}")
        else:
            print("未选择任何文件")
        print("文件选择流程完成")
        return files
    except Exception as e:
        print(f"发生错误: {e}")
        return ()


def generate_fileid(user_id, type1):
    letters = string.ascii_letters
    rd_str = ''.join(random.choice(letters) for _ in range(8))
    if type1 == 'image':
        fileid = str(user_id) + "_" + rd_str + str(int(time.time() * 10000))
    elif type1 == 'video':
        fileid = str(user_id) + "_" + rd_str + str(int(time.time() * 10000)) + ".mp4"
    else:
        fileid = str(user_id) + "_" + rd_str
    return fileid


def upload_to_qiniu(file):
    video_extension = ['.mp4']
    ext = os.path.splitext(file)[1].lower()
    if ext in video_extension:
        content_type = 'video/mp4'
        type = 'video'
    else:
        content_type = 'image/jpeg'
        type = 'image'
    userid = get_user_id()
    file_id = generate_fileid(userid, type)
    key = file_id
    global qiuniutoken
    if qiuniutoken is None:
        qiuniutoken = get_qiniu_token()
    print(f"token：{qiuniutoken}")
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            with open(file, 'rb') as f:
                files = {
                    'token': (None, qiuniutoken),
                    'fname': (None, f"user/photos/{userid}/{key}"),
                    'key': (None, key),
                    'file': (file, f, content_type)
                }
                response = requests.post(qiniu_filesystem, files=files, headers=qiniu_headers)
                if response.status_code == 200:
                    rp = response.json()
                    print(f"已上传到七牛{rp}")
                    key = rp["key"]
                    return key, type
                else:
                    qiuniutoken = get_qiniu_token()
                    print(response.text, "tokem失效，但是code200，重新获取token")
                    if attempt < max_retries:
                        # Add a delay before retrying (optional)
                        time.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            print(f"发生错误：{e}")
            qiuniutoken = get_qiniu_token()
            if attempt < max_retries:
                # Add a delay before retrying (optional)
                time.sleep(2 ** attempt)  # Exponential backoff


def commit_photo_to_album(key):
    body = {
        "fileIds": [key],
    }
    try:
        response = requests.post(upload_ok, headers=headers, json=body)
        if response.status_code == 200:
            rp = response.json()
            print(f"图片已上传到相册{rp}")
        else:
            print(response.text)
    except Exception as e:
        print(e)


def album_to_screen(screen_id='PStestScreenL0001', album_id=''):
    # global get_album_images
    try:
        tmp_url = get_album_images + str(album_id)
    except Exception as e:
        print(e)
    response = requests.get(tmp_url, headers=headers)
    if response.status_code == 200:
        rp = response.json()
        file_ids = rp['data']['fileId']
        body_list = []
        for index, value in enumerate(file_ids):
            body_dic = {}
            body_dic['fileId'] = value
            body_dic['screenId'] = screen_id
            body_dic['sortOrder'] = index + 1
            body_dic['thumbnail'] = value
            body_list.append(body_dic)
        body = {
            "screenId": screen_id,
            "screenPictureSet": body_list
        }
        response = requests.post(album_picture_to_screen, headers=headers, json=body)
        print(f"data:{body}, {album_picture_to_screen}, headers:{headers}")
        if response.status_code == 200:
            rp = response.json()
            if rp['code'] == 20:
                print("图片已上传到屏幕")
            else:
                print("提交失败", rp)
        else:
            print(response.text)
    else:
        print(response.text)


def commit_video_to_screen(key, screen_id='PStestScreenL0001', file=''):
    print("开始提交视频到屏幕")
    file_path = get_video_first_frame(file)
    print(f"缩略图位置：{file_path}")
    key2, type1 = upload_to_qiniu(file_path)
    body = {
        "screenId": screen_id,
        "screenVideoSet": [
            {
                "fileId": key,
                "duration": 3,
                "screenId": screen_id,
                "sortOrder": 0,
                "thumbnail": key2
            }
        ]
    }
    print(f"七牛body：{body}")
    try:
        response = requests.post(video_to_commit, headers=headers, json=body)
        print(f"视频上传请求响应：{response.text}")
        if response.status_code == 200:
            rp = response.json()
            print(f"视频上传完成响应：{rp}")
            try:
                os.remove(file_path)
            except FileNotFoundError:
                print("文件不存在")
                sys.exit()
            except PermissionError:
                print("文件被占用")
                sys.exit()
            except Exception as e:
                print(f"删除视频缩略图发生错误：{e}")
                sys.exit()
            return key
        else:
            print(response.text)
    except Exception as e:
        print(e)


def upload_file(file, screen_id):
    print(file)
    print("开始上传文件")
    key, type = upload_to_qiniu(file)
    if key:
        if type == 'image':
            commit_photo_to_album(key)
            print(f"识别为图片")
        elif type == 'video':
            print(f"识别为视频")
            commit_video_to_screen(key=key, file=file, screen_id=screen_id)
            print(f"识别为视频：上传类型：{type}")
        else:
            print(f"{file}上传失败")
            sys.exit()
    print(f"{file}上传完成")
    print(f"上传类型：{type}")
    return key


def picture_to_screen(screen_id='PStestScreenL0001', file=None, fileId=None):
    # global get_album_images
    if file is not None:
        body_list = []
        body_dic = {}
        body_dic['fileId'] = fileId
        body_dic['screenId'] = screen_id
        body_dic['sortOrder'] = 1
        body_dic['thumbnail'] = fileId
        body_list.append(body_dic)
        body = {
            "screenId": screen_id,
            "screenPictureSet": body_list
        }
        response = requests.post(album_picture_to_screen, headers=headers, json=body)
        if response.status_code == 200:
            rp = response.json()
            if rp['code'] == 20:
                print("图片已上传到屏幕")
            else:
                print("提交失败", rp)
        else:
            print(response.text)
    else:
        logging.error("文件不存在")


def get_screen_picture1():
    screen_picture = get_screen_picture
    body = {
        "PStestScreenL0001"
    }
    response = requests.get(screen_picture, headers=headers, data=body)
    print(response.text)


def get_video_first_frame(file_path):
    cap = cv2.VideoCapture(file_path)
    ret, frame = cap.read()
    print("准备读取视频")
    if ret:
        file_path = file_path.replace(".mp4", ".jpg")
        cv2.imwrite(file_path, frame)
        print(f"已完成第一帧画面读取，缩略图位置：{file_path}")
        return file_path
    else:
        return None


def telnet_connect(host):
    connect_port = 23
    try:
        tn = telnetlib.Telnet(host, port=connect_port, timeout=10)
        tn.read_until(b"login: ", timeout=1)
        tn.write(b"root\n")
        tn.read_until(b"Password: ", timeout=2)
        tn.write(b"ya!2dkwy7-934^\n")
        return tn
    except Exception as e:
        print(f"连接异常：{e}")
        return False


def check_file_has_downloaded(file_name, tn, file_type):
    if file_type == 'video':
        suffix = 'ls /mnt/video/'
        cmd1 = suffix + file_name + '.mp4'
    elif file_type == 'jpg':
        suffix = 'ls /mnt/picture/'
        cmd1 = suffix + file_name + '.jpg'
    else:
        print(f"文件类型错误：{file_type}")
        sys.exit()
    cmd2 = 'echo $?'
    cmd_list = [cmd1, cmd2]
    result = cmd_check(tn, cmd_list, '0')
    print(f"检查结果：{result}")
    if result:
        return True
    else:
        start_time = time.time()
        while True:
            end_time = time.time()
            if end_time - start_time > 120:
                logging.error(f"未检测到视频文件{file_name}")
                return file_name
            result = cmd_check(tn, cmd_list, file_name)
            time.sleep(5)
            if result:
                return True


def cmd_check(tn: telnetlib.Telnet, cmd: list, text: str):
    times1 = 0
    text = text.encode('utf-8')
    while True:
        for i in cmd:
            tn.write(i.encode('utf-8') + b'\n')
            time.sleep(0.5)
        result = get_latest_print(tn)
        print(f"telenet 回显：{result}")
        if result:
            if text in result:
                return True
            else:
                if times1 >= 10:
                    return False
                times1 += 1
                continue


def get_latest_print(tn: telnetlib.Telnet):
    times = 0
    while True:
        time.sleep(0.5)
        content = tn.read_very_eager()
        index1 = content.rfind(b"\r\n")
        index = content.rfind(b"\r\n", 0, index1)
        if index != -1:
            content = content[index + 2:index1:1]
            return content
        else:
            times += 1
            if times >= 7:
                logging.error(f"内容为：{content}")
                return False


def main():
    login()
    album_id, cover_id = get_album_id()
    album_picture_api = 'http://' + server + ":" + port + '/api/v1/photo/album/list'
    param = {
        'albumId': album_id,
        'pageNum': 1,
        'pageSize': 1000
    }
    result = requests.get(album_picture_api, headers=headers, params=param)
    if result.status_code == 200:
        rp = result.json()["data"]["records"]
        if rp:
            print(f"接口获取该相册有如下图片地址：{rp}")
        else:
            sys.exit()
    else:
        print(result.text)
        sys.exit()
    print(f"开始删除相册中的图片，文件id为：{rp}")
    pictures_to_del = {
        "fileIds": rp
    }
    del_album_picture1 = del_album_picture + str(album_id)
    result = requests.delete(del_album_picture1, headers=headers, json=pictures_to_del)
    if result.status_code == 200:
        rp = result.json()
        print(rp)
        if rp['code'] == 20:
            print("删除成功")
        else:
            print("删除失败", rp)
if __name__ == "__main__":
    main()