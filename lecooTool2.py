import logging
import os
import sys
import requests
import base64
import pandas as pd
from tkinter import filedialog
import datetime
from typing import Tuple, Iterable, Hashable
import tkinter as tk
from tkinter import Toplevel

# 配置日志记录器
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s [in %(filename)s:%(lineno)d]',
                    datefmt='%Y-%m-%d %H:%M:%S')
batach_size = 4

token = None
df_row = 0
counter = 0
txt_name = None
factory_code = 'LecooTN'
sn_key = '装箱条码'
motherboard_key = '主板'
inverter_board_key = '逆变板'
wireless_network_card_key = '无线网卡'
memory_key = "内存"
hard_disk_key = "硬盘"
lcd_key = 'LCD'
lcd_screen_cable_key = 'LCD屏线'
lcd_back_cover_key = 'LCD后盖'
adapt_key = "适配器"
power_cable_key = "电源线"
batch_number_key = "批次号"
host_production_time_key = "主机生产日期"
factory_type_key = "工厂类型"
factory_name_key = "工厂名称"
ship_date_key = "购机日期"
sale_region_key = "销售区域"
shop_key = "店铺"
uwip_barcode_key = "主机条码"
# 如果缺少信息的字段使用下面的内容
loss_tip = "data_missing_temporarily"
no_factory_name_key = "LecooTN"
no_factory_type_key = "ODM"
null_info = ""
progress_bar = 0


# 自定义一个异常类用于token失效是抛出
class TokenExpired(Exception):
    """自定义异常类"""

    def __init__(self, message="token失效"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'Error: {self.message}'


# 异常处理
def handle_200(response):
    global progress_bar
    progress_bar += 1


def handle_400(response):
    msg = response.json()["ErrorMessage"]
    if "payload to long" in msg:
        show_popup("数据过大，请联系工具制作人！")
    elif "missing some field in the payload header" in msg:
        show_popup("头部缺少字段，请联系工具制作人")
    elif "missing some field in the payload body" in msg:
        show_popup("缺少部分数据，请检查表格")
    else:
        show_popup(f"未知错误：{msg}")


def handle_401(response):
    get_token()
    raise TokenExpired


def handle_500(response):
    show_popup("服务器500异常，请联系来酷、欧讯！")


def handle_default(response):
    print(f"未处理的响应状态码：{response.status_code}")
    print("响应内容：", response.text)
    return None


status_code_handlers = {
    200: handle_200,
    400: handle_400,
    401: handle_401,
    500: handle_500
}


def show_popup(message: str):
    # 创建主窗口，但不显示
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 定义一个函数来处理关闭操作
    def on_closing():
        popup.destroy()
        if not any(w.winfo_exists() for w in root.winfo_children()):
            root.quit()

    # 创建弹窗
    popup = Toplevel(root)
    popup.title("提示")

    # 设置弹窗总是位于最上层
    popup.attributes('-topmost', True)

    # 创建标签显示消息
    label = tk.Label(popup, text=message)
    label.pack(padx=20, pady=20)

    # 获取屏幕宽度和高度
    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()

    # 计算弹出窗口的位置，使其居中
    popup.update_idletasks()  # 强制更新以获取准确的宽度和高度
    width = popup.winfo_width()
    height = popup.winfo_height()
    x_position = (screen_width - width) // 2
    y_position = (screen_height - height) // 2

    popup.geometry(f"{width}x{height}+{x_position}+{y_position}")

    # 添加一个按钮用于关闭窗口
    button = tk.Button(popup, text="关闭", command=on_closing)
    button.pack(pady=10)

    # 监听关闭事件
    popup.protocol("WM_DELETE_WINDOW", on_closing)

    # 运行主循环
    root.mainloop()


def get_token():
    api = 'https://api-cn-t.lenovo.com/uat/token'
    consumer_key = 'CrjifR54rsPeirvatCMBi8oRnUMa'
    consumer_secret = 'T3C5Xwtt9Jn_pPv2PIBhs0q8mDwa'
    auth_str = f"{consumer_key}:{consumer_secret}"
    auth_byte = auth_str.encode("utf-8")
    auth_base64 = base64.b64encode(auth_byte).decode("utf-8")
    header = {
        "Authorization": f"Basic {auth_base64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "grant_type": "client_credentials"
    }
    response = requests.post(url=api, headers=header, data=payload)
    if response.status_code == 200:
        s = response.json()
        token1 = s['access_token']
        global token
        token = token1
        # token = '67566699-e23a-326e-8739-29dde2515239'  # 用于调试token过期的场景
        return token1
    else:
        return False


def generate_timestamp():
    get_daily_counter()
    global counter
    if not counter:
        counter = 'tmp'
    datastr = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return datastr + '{:05d}'.format(counter)


def open_file():
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="请选择表格文件",
        filetypes=[("Excel Files", "*.xlsx;*.xls")]
    )
    root.destroy()
    return file_path


def read_data_from_excel() -> Iterable[Tuple[Hashable, pd.Series]]:
    try:
        file_path = open_file()
        df = pd.read_excel(file_path)
        global df_row
        df_row = df.shape[0]
        rows = df.iterrows()
        return rows
    except FileNotFoundError:
        sys.exit(0)


def send_data_to_lecoo(excel_data, access_token):
    api1 = 'https://api-cn-t.lenovo.com/uat/v1.0/supply_chain/ips_guarantee_data/tbl_machine_sequence'
    header = {
        "Authorization": f"Bearer {access_token}",
    }
    body = {
        "header": {
            "TRL": "1",
            "PLANT": "LecooTN",
            "TXT_NAME": "",
            "TXT_NUM": "",
            "TXT_SOURCE": ""
        },
        "Data": [
            {
                "Machine_No": "主机",
                "MATERIAL_NO": excel_data[0],
                "PACKING_LOT_NO": excel_data[1],
                "START_DATE": excel_data[2],
                "Flag_Linked": "1",
                "Check_Code": "",
                "VF_NAME": "",
                "PLANT": "",
                "SITE_TYPE": "",
                "UWIP_SN": "",
                "SHIP_DATE": "",
                "SALE_REGION": "",
                "SHOP": "",
                "UWIP_BARCODE": "",
                "ADD_DEL_FLAG": "A"  # D为删除
            }
        ]
    }

    payload = {
        "header": {
            "TRL": "400",  # 必填 行数总量
            "PLANT": "LecooTN",  # 必填 工厂代码
            "TXT_NAME": "",  # 必填 文件名
            "TXT_NUM": "",  # ROW Header 空值
            "TXT_SOURCE": ""  # 必填 PRC
        },
        "Data": [
            {
                "MACHINE_NO": "主机号",  # 必填 MACH_SER
                "MATERIAL_BARCODE_PRE": "",  # 传空值
                "AUTO_ID": "",  # 传空值
                "MATERIAL_BARCODE": "部件条码--部件的条形码",  # 必填 PART_SER
                "CREATE_DATE_TIME": "创建时间--时分秒格式",  # 必填 BUILD_DATE
                "MATERIAL_NO": "部件编码--部件条形码的CODE",  # 必填 PART_NBR
                "VF_NAME": "",  # 传空值
                "MATERIAL_CLASS_CODE": "部件类别代码",  # MATERIAL_CLASS_CODE
                "PLANT_CODE": "",  # ibase数据上传文件名中的plant code
                "CS_FILE_TYPE": "",  # 传空值
                "SITE_TYPE": "工厂类型--该主机的所属工厂分类",  # 必填 INHOUSE / ODM
                "MTMSN": "",  # 传空值
                "PACKING_LOT_NO": "批次号",  # 有的话必填，没有为空
                "MODEL": "产品编码（MTM）",  # 必填 PRODUCT_ID
                "PRINTED_DESC": "",  # 物料描述，同装箱单一致，没有传空值
                "PRODUCT_DATE": "生产日期-年月日格式",  # Product_Date
                "SCAN_DATE": "出库日期--时分秒格式",  # Scan_Date
                "LUCKY_NO": "",  # 可为空
                "SALEORDER": "销售单号",  # DOA无的话填NA值
                "COUNTRY": "国家--CODE",  # DOA无的话填NA值
                "QTY": "数量",  # 固定值1
                "PO": "",  # DOA无的话填NA值
                "ADD_DEL_FLAG": "A",  # 必填 写死 A
                # "SHELL_IND": "-"  # 必填 固定值 -
            }
        ]
    }
    pass


def extract_specific_cell_from_series(row: Tuple[Hashable, pd.Series], key: str):
    header = row[1].index
    for i in header:
        if key == i:
            value = row[1].get(i)
            if isinstance(value, pd.Timestamp):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            return None if pd.isna(value) else value  # 判断是否为空
    return None


def tbl_Machine_Sequence(params_rows: Iterable[Tuple[Hashable, pd.Series]]):
    """主机信息上传方法"""
    api = 'https://api-cn-t.lenovo.com/uat/v1.0/supply_chain/ips_guarantee_data/tbl_machine_sequence'
    global token
    header = {
        "Authorization": f"Bearer {token}",
    }
    body = {
        "header": {
            "TRL": df_row,
            "PLANT": factory_code,
            "TXT_NAME": txt_name if txt_name else generate_timestamp(),
            "TXT_NUM": "",
            "TXT_SOURCE": "PRC"
        },
        "Data": []
    }
    data_list_for_count = []
    # 将所有行上传到接口
    for row in params_rows:
        body_item = {
            "Machine_No": None,
            "MATERIAL_NO": None,
            "PACKING_LOT_NO": None,
            "START_DATE": None,
            "Flag_Linked": "",
            "Check_Code": "",
            "VF_NAME": "",
            "PLANT": None,
            "SITE_TYPE": None,
            "UWIP_SN": None,
            "SHIP_DATE": None,
            "SALE_REGION": None,
            "SHOP": None,
            "UWIP_BARCODE": None,
            "ADD_DEL_FLAG": "A",  # D为删除
            "SHELL_IND": ""
        }
        if "set body_item":
            sn = extract_specific_cell_from_series(row, sn_key)
            body_item["Machine_No"] = sn
            body_item["MATERIAL_NO"] = sn[: 9]
            batch_no = extract_specific_cell_from_series(row, batch_number_key)
            body_item["PACKING_LOT_NO"] = batch_no if batch_no else loss_tip
            produce_date = extract_specific_cell_from_series(row, host_production_time_key)
            body_item["START_DATE"] = produce_date if produce_date else loss_tip
            factory_name = extract_specific_cell_from_series(row, factory_name_key)
            body_item["PLANT"] = factory_name if factory_name else no_factory_name_key
            factory_type = extract_specific_cell_from_series(row, factory_type_key)
            body_item["SITE_TYPE"] = factory_type if factory_type else no_factory_type_key
            body_item["UWIP_SN"] = sn
            ship_date = extract_specific_cell_from_series(row, ship_date_key)
            body_item["SHIP_DATE"] = ship_date if ship_date else null_info
            sale_region = extract_specific_cell_from_series(row, sale_region_key)
            body_item["SALE_REGION"] = sale_region if sale_region else null_info
            shop = extract_specific_cell_from_series(row, shop_key)
            body_item["SHOP"] = shop if shop else null_info
            uwip_barcode = extract_specific_cell_from_series(row, uwip_barcode_key)
            body_item["UWIP_BARCODE"] = uwip_barcode if uwip_barcode else null_info

        data_list_for_count.append(body_item)
        if len(data_list_for_count) >= batach_size:
            body["Data"] = data_list_for_count
            try:
                response = requests.post(api, json=body, headers=header)
                status_code_handlers.get(response.status_code, handle_default)(response)
                print(body)
                print(response.text)
            except TokenExpired as e:
                logging.info(f"codeNum-343：Token过期，错误信息：{e}")
                # 重新请求接口
                response = requests.post(api, json=body, headers=header)
                print(f"重新获取请求token后的请求结果：{response.text}")
            except Exception as e:
                logging.error(f"codeNum-342：接口请求失败，错误信息：{e}")
            data_list_for_count = []
    #  循环结束后将剩余的部分（即不满足一批的）继续发送
    if data_list_for_count:
        body["Data"] = data_list_for_count
        try:
            response = requests.post(api, json=body, headers=header)
            status_code_handlers.get(response.status_code, handle_default)(response)
            print(response.text)
        except TokenExpired as e:
            logging.info(f"codeNum-343：Token过期，错误信息：{e}")
            # 重新请求接口
            response = requests.post(api, json=body, headers=header)
            print(f"重新获取请求token后的请求结果：{response.text}")
        except Exception as e:
            logging.error(f"codeNum-342：接口请求失败，错误信息：{e}")
        print(body)


def tbl_Packing_Machine_Material():
    pass


def get_daily_counter():
    """
    基于当前日期生成每日计数器值，并将其保存到一个文件中。
    """
    global counter
    current_date = datetime.date.today().strftime("%Y%m%d")
    filename = "resource/tmp/counter.txt"
    if not os.path.exists(filename):
        counter = 1
    else:
        with open(filename, 'r') as f:
            saved_date, saved_counter = f.read().split(',')
            if saved_date != current_date:
                counter = 1
            else:
                counter = int(saved_counter) + 1

    with open(filename, 'w') as f:
        f.write(f"{current_date},{counter}")


get_token()
rows = read_data_from_excel()
tbl_Machine_Sequence(rows)
