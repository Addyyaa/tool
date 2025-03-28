import os
import sys
import time
import requests
import base64
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import datetime
from typing import Iterator, Tuple, Iterable, Hashable

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


def extract_specific_cell_from_series(row: Tuple[int, pd.Series], key: str):
    header = row[1].index
    for i in header:
        if key == i:
            return row[1].get(i)
    return None


def tbl_Machine_Sequence(params_rows: Iterable[Tuple[Hashable, pd.Series]]):
    api = 'https://api-cn-t.lenovo.com/uat/v1.0/supply_chain/ips_guarantee_data/tbl_packing_machine_material'
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
        "Data": [
            {
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
        ]
    }
    # 将所有行上传到接口
    for row in params_rows:
        if "set body":
            sn = extract_specific_cell_from_series(row, sn_key)
            body["Data"][0]["Machine_No"] = sn
            body["Data"][0]["MATERIAL_NO"] = sn[: 9]
            batch_no = extract_specific_cell_from_series(row, batch_number_key)
            body["Data"][0]["PACKING_LOT_NO"] = batch_no if batch_no else loss_tip
            produce_date = extract_specific_cell_from_series(row, host_production_time_key)
            body["Data"][0]["START_DATE"] = produce_date if produce_date else loss_tip
            factory_name = extract_specific_cell_from_series(row, factory_name_key)
            body["Data"][0]["PLANT"] = factory_name if factory_name else no_factory_name_key
            factory_type = extract_specific_cell_from_series(row, factory_type_key)
            body["Data"][0]["SITE_TYPE"] = factory_type if factory_type else no_factory_type_key
            body["Data"][0]["UWIP_SN"] = sn
            ship_date = extract_specific_cell_from_series(row, ship_date_key)
            body["Data"][0]["SHIP_DATE"] = ship_date if ship_date else null_info
            sale_region = extract_specific_cell_from_series(row, sale_region_key)
            body["Data"][0]["SALE_REGION"] = sale_region if sale_region else null_info
            shop = extract_specific_cell_from_series(row, shop_key)
            body["Data"][0]["SHOP"] = shop if shop else null_info
            uwip_barcode = extract_specific_cell_from_series(row, uwip_barcode_key)
            body["Data"][0]["UWIP_BARCODE"] = uwip_barcode if uwip_barcode else null_info

        response = requests.post(api, json=body, headers=header)
        print(body)
        print(response.text)


def tbl_Packing_Machine_Material():
    pass


def get_daily_counter():
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
print(type(rows))
tbl_Machine_Sequence(rows)
