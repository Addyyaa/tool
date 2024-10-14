import tkinter as tk
from tkinter import filedialog
import logging
import sys
from io import BytesIO
import requests
from PIL import Image

# 定义日志
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s - Line %(lineno)d', level=logging.INFO)

headers = {
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, "
                  "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                  "Immersed/34.909092)",
}

server = "139.224.192.36"
port = "8082"
groupId = ""
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
meta_api = 'http://' + server + ":" + port + '/api/v1/capacity/file/meta'  # 入参列表元素：fileId width height fileType-1
# storageType-1 fileName-fileId contentType-image/jpeg fileSize-bianliang
upload_ok = 'http://' + server + ":" + port + '/api/v1/photo/'  # message成功
user_id_api = 'http://' + server + ":" + port + '/api/v1/user/profile'
get_screen_picture = 'http://' + server + ":" + port + '/api/v1/host/screen'
video_to_commit = 'http://' + server + ":" + port + '/api/v1/screenVideo/publish/increment'
get_album_images = 'http://' + server + ":" + port + '/api/v1/photo/info?albumId='
album_picture_to_screen = 'http://' + server + ":" + port + '/api/v1/screenPicture/publish'


def select_image():
    """
    弹窗让用户选择图片，并输出图片的路径
    """
    # 创建一个隐藏的Tkinter主窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 设置窗口为置顶
    root.wm_attributes("-topmost", 1)

    # 弹出文件选择对话框，选择图片文件
    image_paths = filedialog.askopenfilenames(
        title="选择图片文件",
        filetypes=[("Image files", "*.jpg;*.jpeg;*.png;*.bmp;*.gif")]
    )

    # 关闭主窗口
    root.destroy()

    if image_paths:
        return image_paths  # 返回选择的多个文件路径的元组
    return None  # 如果没有选择文件，返回None



def get_image_resolution():
    """
    读取图片的分辨率（宽度和高度）

    返回:
    tuple: 图片的宽度和高度
    """
    image_paths = select_image()
    if image_paths:  # 检查是否选择了文件
        resolutions = []
        for i in image_paths:
            with Image.open(i) as img:
                width, height = img.size
                resolutions.append((width, height))
        return resolutions  # 返回所有选择图片的分辨率列表
    return None  # 如果没有选择文件，返回None


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


class ResolutionCompute:
    def __init__(self):
        self.min_resolution = 0
        self.max_resolution = 0
        while True:
            try:
                self.min_resolution = int(input("请输入分辨率下限:"))
                self.max_resolution = int(input("请输入分辨率上限:"))
                if self.min_resolution <= 0 or self.max_resolution <= 0:
                    print("分辨率必须是正整数，请重新输入!")
                    continue

                if self.min_resolution >= self.max_resolution:
                    print("分辨率下限必须小于上限，请重新输入!")
                    continue
                break
            except ValueError:
                print("请输入整数!")
                continue

    def scale_to_fit_resolution(self):
        picture_resolutions = get_image_resolution()
        if picture_resolutions is None:
            print("未选择任何图片。")
            return None  # 如果没有选择任何图片，返回None

        scaled_resolutions_list = []  # 重命名局部变量
        for picture_width, picture_height in picture_resolutions:
            longest_side = max(picture_width, picture_height)
            shortest_side = min(picture_width, picture_height)
            longest_side_scale = self.max_resolution / longest_side
            shortest_side_scale = self.min_resolution / shortest_side
            scale = min(longest_side_scale, shortest_side_scale, 1)
            scale_width = int(picture_width * scale)
            scale_height = int(picture_height * scale)
            scaled_resolutions_list.append((scale_width, scale_height))

        return scaled_resolutions_list  # 返回所有缩放后的分辨率


def get_user_id():
    response = requests.get(user_id_api, headers=headers)
    if response.status_code == 200:
        rp = response.json()
        user_id = rp["data"]["userId"]
        return user_id
    else:
        print(response.text)


def get_screens():
    screen_list_api = 'http://' + server + ":" + port + "/api/v1/otaUpgradeRecord/list"
    response = requests.get(screen_list_api, headers=headers)
    if response.status_code == 200:
        rp = response.json()['data']
        screens = []
        for i in rp:
            # 遍历屏幕组中的屏列表
            screens_list = i['screenList']
            # 遍历屏列表中的屏幕
            for j in screens_list:
                screen1 = j['screenId']
                screens.append(screen1)
        return screens


def get_screen_picture1(has_tfcard, screen1):
    pictures_list = []
    if has_tfcard:
        get_screen_picture_api = "http://" + server + ":" + port + '/api/v1/screenPicture/page/list'
        body = {
            "pageNum": 1,
            "pageSize": 1000,
            "screenId": screen1
        }
    else:
        get_screen_picture_api = "http://" + server + ":" + port + '/api/v1/host/screen'
        body = {
            "screenDeviceId": screen1
        }
    response = requests.get(get_screen_picture_api, headers=headers, params=body)
    if response.status_code == 200:
        rp = response.json()["data"]
        if rp:
            if has_tfcard:
                rp = rp["records"]
            else:
                rp = rp["pictures"]
            for i in rp:
                pictures_list.append(i["fileId"])
            pictures_list = [item for item in pictures_list if item]
        else:
            logging.error("json解析失败")
            input("按任回车退出")
            sys.exit(1)
    else:
        print(response.text)
        input("按任回车退出")
        sys.exit(1)
    return pictures_list


def judge_has_tfcard(screen2):
    has_tfcard = False
    pamaters = {
        "screenDeviceId": screen2
    }
    screen_info_api = 'http://' + server + ":" + port + '/api/v1/host/screen'
    response = requests.get(screen_info_api, headers=headers, params=pamaters)
    if response.status_code == 200:
        rp = response.json()["data"]
        if rp:
            is_tfcard = rp["pictures"]
            if is_tfcard:
                print("没有TF卡")
            else:
                has_tfcard = True
                print("有TF卡")
        else:
            logging.error("json解析失败")
            input("按任回车退出")
            sys.exit(1)
    else:
        print(response.text)
        input("按任回车退出")
        sys.exit(1)
    return has_tfcard


def get_url_picture_resolution(pictures_list):
    resolutions_list = []
    picture_url_prefix = "http://files-static-test.austinelec.com/"
    for i in pictures_list:
        picture_url = picture_url_prefix + i
        try:
            # 发送请求获取图片
            response = requests.get(picture_url)
            response.raise_for_status()  # 检查请求是否成功
            # 使用 BytesIO 将获取的内容作为文件对象
            image = Image.open(BytesIO(response.content))
            width, height = image.size
            resolutions_list.append({"width": width, "height": height})
        except Exception as e:
            print(f"获取分辨率时出错: {e}")
    if resolutions_list:
        return resolutions_list
    else:
        logging.error("没有获取到分辨率")
        input("按任回车退出")
        sys.exit(1)


if __name__ == '__main__':
    computed_resolution = []
    resolution_compute = ResolutionCompute()
    scaled_resolutions = resolution_compute.scale_to_fit_resolution()
    if scaled_resolutions:
        for index, (new_width, new_height) in enumerate(scaled_resolutions):
            computed_resolution.append({"width": new_width, "height": new_height})
    login()
    sreens = get_screens()
    print("请选择屏幕:")
    for index, screen in enumerate(sreens):
        print(f"{index + 1}. {screen}")

    while True:
        try:
            index = int(input("请输入序号:")) - 1
            if index < 0 or index >= len(sreens):
                raise ValueError
            break
        except ValueError:
            print("请输入有效的序号")
    print(f"已选择屏幕：{sreens[index]}")
    result = judge_has_tfcard(sreens[index])
    pictures = get_screen_picture1(result, sreens[index])
    if pictures:
        resolution_list = get_url_picture_resolution(pictures)
    else:
        print("没有图片")
        input("按任回车退出")
        sys.exit(1)
    if len(resolution_list) != len(computed_resolution):
        print("屏幕中的图片数量与测试的图片数量不一致！！请检查")
        input("按任回车退出")
        sys.exit(1)
    else:
        test_result = True
        for index, resolution in enumerate(resolution_list):
            width_offeset = abs(resolution["width"] - computed_resolution[index]["width"])
            height_offset = abs(resolution["height"] - computed_resolution[index]["height"])
            if width_offeset > 1 or height_offset > 1:
                print(f"第{index + 1}张图片的分辨率不正确！！\t正确分辨率应为：{computed_resolution[index]}\t实际分辨率为：{resolution}")
                test_result = False
        if test_result:
            print("分辨率一致！\033[32m测试通过\033[0m")
        else:
            print("\033[31m测试不通过！\033[0m")
        input("按任回车退出")
        sys.exit(0)