import json
import logging
import math
import os
import shutil
import sys
import time
import requests
import base64
import pandas as pd
import configparser
from tkinter import filedialog
import datetime
from typing import Tuple, Hashable, Optional
import tkinter as tk
from tkinter import Toplevel, ttk
from requests.exceptions import ConnectionError, Timeout, HTTPError
from datetime import timedelta
import re

# 配置日志记录器
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s [in %(filename)s:%(lineno)d]',
                    datefmt='%Y-%m-%d %H:%M:%S')
batch_size = 50
file_path = None
pn_table_index_key = '8码'
pn_table_product_name = '27 一体机 '
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
produce_date_key = "生产日期"
planet_code = ""
# 如果缺少信息的字段使用下面的内容
loss_tip = ""
no_factory_name_key = "LecooTN"
no_factory_type_key = "ODM"
null_info = ""
progress_bar = 0
total_request_count = 0
progress_window: tk.Tk | None = None
progress_label: Optional[tk.Label] = None
progress_bar_widget: Optional[ttk.Progressbar] = None
# 测试环境 TODO 切换成正式环境
# token_api = 'https://api-cn-t.lenovo.com/uat/token'
# mathine_api = 'https://api-cn-t.lenovo.com/uat/v1.0/supply_chain/ips_guarantee_data/tbl_machine_sequence'
# material_api = 'https://api-cn-t.lenovo.com/uat/v1.0/supply_chain/ips_guarantee_data/tbl_packing_machine_material'
# consumer_key = 'CrjifR54rsPeirvatCMBi8oRnUMa'
# consumer_secret = 'T3C5Xwtt9Jn_pPv2PIBhs0q8mDwa'

# 生产环境
token_api = 'https://api-cn.lenovo.com/token'
mathine_api = 'https://api-cn.lenovo.com/v1.0/supply_chain/ips_guarantee_data/tbl_machine_sequence'
material_api = 'https://api-cn.lenovo.com/v1.0/supply_chain/ips_guarantee_data/tbl_packing_machine_material'
consumer_key = 'zuuA3GFYEfx1B2Hdngs3V_A19Vca'
consumer_secret = 'KB3mrXiAMlJoTlqstyXSDniM5osa'


# 自定义一个异常类用于token失效是抛出
class TokenExpired(Exception):
    """自定义异常类"""

    def __init__(self, message="token失效"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'Error: {self.message}'


# 创建进度窗口
def create_progress_window():
    global progress_window, progress_label, progress_bar_widget

    # 先检查是否已有窗口存在
    if progress_window is not None:
        try:
            if hasattr(progress_window, 'winfo_exists') and progress_window.winfo_exists():
                progress_window.destroy()
        except (tk.TclError, RuntimeError):
            pass  # 忽略错误，窗口可能已经被销毁

    try:
        progress_window = tk.Tk()
        progress_window.title("处理进度")
        # 初始大小，后面会更新
        initial_width = 300
        initial_height = 100
        progress_window.geometry(f"{initial_width}x{initial_height}")
        progress_window.resizable(False, False)

        # 添加窗口关闭处理器
        def on_window_close():
            global progress_window, progress_label, progress_bar_widget
            progress_window = None
            progress_label = None
            progress_bar_widget = None

        progress_window.protocol("WM_DELETE_WINDOW", on_window_close)

        progress_label = tk.Label(progress_window, text=f"处理进度: 0/{total_request_count}")
        progress_label.pack(pady=10)

        progress_bar_widget = ttk.Progressbar(progress_window, length=200, mode='determinate')
        progress_bar_widget.pack(pady=10)
        progress_bar_widget['value'] = 0

        # 强制更新窗口以获取准确的尺寸
        progress_window.update_idletasks()

        # 获取屏幕宽度和高度
        screen_width = progress_window.winfo_screenwidth()
        screen_height = progress_window.winfo_screenheight()

        # 获取窗口的实际宽度和高度
        window_width = progress_window.winfo_width()
        window_height = progress_window.winfo_height()

        # 计算居中位置
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2

        # 设置窗口居中显示
        progress_window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

        # 再次强制更新以确保位置立即生效
        progress_window.update()

        # 确保窗口保持在最前面
        progress_window.attributes('-topmost', True)

        return progress_window
    except Exception as e:
        logging.error(f"创建进度窗口时出错: {e}")
        return None


# 更新进度窗口
def update_progress_window():
    global progress_bar, total_request_count, progress_label, progress_bar_widget, progress_window

    # 检查窗口和组件是否存在
    if progress_window is None:
        return

    try:
        # 确保窗口仍然存在
        if not hasattr(progress_window, 'winfo_exists') or not progress_window.winfo_exists():
            progress_window = None
            progress_label = None
            progress_bar_widget = None
            return

        if progress_label is None or progress_bar_widget is None:
            return

        progress_percentage = (progress_bar / total_request_count) * 100 if total_request_count > 0 else 0
        progress_label.config(text=f"进度: {progress_bar}/{total_request_count}")
        progress_bar_widget['value'] = progress_percentage

        # 安全地更新窗口
        try:
            progress_window.update()
        except tk.TclError:
            # 窗口可能已被销毁
            progress_window = None
            progress_label = None
            progress_bar_widget = None
            return

        # 如果进度完成，显示完成消息
        if progress_bar >= total_request_count and progress_window is not None:
            progress_label.config(text="处理完成！")
            # 使用安全的方式延迟关闭窗口
            try:
                progress_window.after(2000, lambda: safe_destroy_window())
            except tk.TclError:
                pass
    except Exception as e:
        # 处理窗口可能已关闭或无效的情况
        logging.warning(f"更新进度窗口时出错: {e}")
        progress_window = None
        progress_label = None
        progress_bar_widget = None


# 安全地销毁窗口
def safe_destroy_window():
    global progress_window
    if isinstance(progress_window, tk.Tk):
        try:
            if progress_window and hasattr(progress_window, 'winfo_exists') and progress_window.winfo_exists():
                progress_window.destroy()
        except Exception as e:
            logging.warning(f"关闭进度窗口时出错: {e}")
        finally:
            progress_window = None


# 异常处理
def handle_200(response):
    global progress_bar
    progress_bar += 1
    update_progress_window()  # 更新进度窗口


def handle_400(response):
    msg = response.json()["ErrorMessage"]
    if "payload to long" in msg:
        show_popup("数据过大，请联系工具制作人！")
    elif "missing some field in the payload header" in msg:
        show_popup("头部缺少字段，请联系工具制作人")
        logging.error(response.text)
    elif "missing some field in the payload body" in msg:
        show_popup("缺少部分数据，请检查表格")
        logging.error(response.text)
    else:
        show_popup(f"未知错误：{msg}")
        logging.error(response.text)


def handle_401(response):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}-重新获取token")
    t = get_token()
    print(f"新的token： {token}\t{t}")
    raise TokenExpired


def handle_500(response):
    show_popup("服务器500异常，请联系来酷、欧讯！")


def handle_default(response):
    logging.error(f"未处理的响应状态码：{response.status_code}\t响应内容：{response.text}")
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


def show_progress_window(total, current):
    """
    弹出进度窗口，显示当前处理进度。

    参数：
    total (int): 总数量
    current (int): 当前已处理的数量
    """
    # 创建主窗口
    root = tk.Tk()
    root.title("处理进度")
    root.geometry("300x100")  # 设置窗口大小
    root.resizable(False, False)  # 禁止调整窗口大小

    # 计算进度百分比
    progress_percentage = (current / total) * 100 if total > 0 else 0

    # 创建进度条
    progress_label1 = tk.Label(root, text=f"进度: {current}/{total}")
    progress_label1.pack(pady=10)

    progress_bar1 = ttk.Progressbar(root, length=200, mode='determinate')
    progress_bar1.pack(pady=10)
    progress_bar1['value'] = progress_percentage

    # 刷新窗口以显示进度
    root.update()

    # 如果进度未完成，保持窗口打开（这里可以根据需要调整）
    if current < total:
        root.after(100, lambda: root.destroy())  # 100ms 后关闭窗口（模拟刷新效果）
    else:
        time.sleep(1)  # 完成后显示 1 秒后关闭
        root.destroy()

    # 进入主循环（仅在需要持续显示时使用）
    root.mainloop()


def get_token():
    config = get_local_config()
    option = 'CONFIG'
    global token_api, consumer_key, consumer_secret
    tk = config.get(option, 'token_api')
    token_api = tk if tk is not None and tk != "" else token_api
    print(token_api)
    api = token_api
    csk = config.get(option, 'consumer_secret')
    consumer_secret = csk if csk is not None and csk != "" else consumer_secret
    csv = config.get(option, 'consumer_key')
    consumer_key = csv if csv is not None and csv != "" else consumer_key
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


def get_header():
    header = {
        "Authorization": f"Bearer {token}",
    }
    return header


def generate_timestamp():
    get_daily_counter()
    global counter
    if not counter:
        counter = 'tmp'
    datastr = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return datastr + '{:05d}'.format(counter)


def extract_specific_cell_from_series(row: Tuple[Hashable, pd.Series], key: str):
    value = row[1].get(key, None)
    # print(value, key)
    if isinstance(value, pd.Timestamp):
        value = value.strftime('%Y-%m-%d %H:%M:%S')
    return None if pd.isna(value) else value  # 判断是否为空


def convert_cycle_to_production_date(weeks: str) -> str:
    """
    从编码字符串中解析日期。编码中可能包含多个 'A'，我们需要找到第一个前面是数字的 'A'，
    然后从这个 'A' 后面提取年份（1位）和周数（2位），并计算该周的最后一天（周日）。

    参数:
        weeks (str): 输入的编码字符串，例如 '870028177A4480161' 或 '123A456A789'

    返回:
        str: 日期字符串，例如 '2024-11-24'

    异常:
        ValueError: 如果未找到前面是数字的 'A' 或周数无效
    """
    # 使用正则表达式找到第一个前面是数字的 'A'
    match = re.search(r'\dA', weeks)
    if not match:
        raise ValueError("未找到前面是数字的 'A'")

    # 获取 'A' 的位置
    a_index = match.start() + 1  # +1 因为 match.start() 是 'A' 前数字的位置

    # 提取年份（A 后的第一个数字）
    year_digit = int(weeks[a_index + 1])
    current_year = datetime.datetime.now().year
    current_year = int(str(current_year)[:3]) * 10
    year = current_year + year_digit  # 假设年份为 20XX，例如 4 -> 2024

    # 提取周数（A 后第 2-3 位）
    week = int(weeks[a_index + 2:a_index + 4])

    # 校验周数是否有效（1-53）
    if week < 1 or week > 53:
        raise ValueError(f"周数 {week} 无效，必须在 1-53 之间")

    # 获取该年的第一天
    first_day = datetime.datetime(year, 1, 1)

    # 计算该年的第一周的周一（ISO 周从周一开始）
    first_day_weekday = first_day.isoweekday()  # 1=周一, 7=周日
    if first_day_weekday <= 4:  # 如果 1 月 1 日是周一到周四，属于第 1 周
        first_monday = first_day - timedelta(days=(first_day_weekday - 1))
    else:  # 如果是周五到周日，属于下一年的第 1 周
        first_monday = first_day + timedelta(days=(8 - first_day_weekday))

    # 计算第 N 周的周一（第 week 周的开始）
    target_monday = first_monday + timedelta(weeks=(week - 1))

    # 计算该周的最后一天（周日）
    last_day = target_monday + timedelta(days=6)

    # 返回格式化的日期字符串
    return last_day.strftime('%Y-%m-%d')


def extract_component_production_date(barcode: str) -> str:
    try:
        month = {
            '1': '01',
            '2': '02',
            '3': '03',
            '4': '04',
            '5': '05',
            '6': '06',
            '7': '07',
            '8': '08',
            '9': '09',
            'A': '10',
            'B': '11',
            'C': '12',
        }
        day = {
            '1': '01',
            '2': '02',
            '3': '03',
            '4': '04',
            '5': '05',
            '6': '06',
            '7': '07',
            '8': '08',
            '9': '09',
            'A': '10',
            'B': '11',
            'C': '12',
            'D': '13',
            'E': '14',
            'F': '15',
            'G': '16',
            'H': '17',
            'J': '18',
            'K': '19',
            'L': '20',
            'M': '21',
            'N': '22',
            'P': '23',
            'Q': '24',
            'R': '25',
            'S': '26',
            'T': '27',
            'U': '28',
            'V': '29',
            'W': '30',
            'X': '31'
        }
        # if len(barcode) >= 23:
        #     date_info = barcode[16:19:1]
        # else:
        #     date_info = barcode
        if len(barcode) >= 23:
            date_info = barcode[-5:-8:-1][::-1]
        else:
            date_info = barcode[-4:-7:-1][::-1]  # TODO 此处键鼠的SN与其他规则不一致，无法断定生产日期，需要与工厂确认
        try:
            current_year = datetime.datetime.now().year
            current_year = int(str(current_year)[:3]) * 10
            year = date_info[0]
            year = int(year) + current_year
        except Exception as y:
            logging.error(f"处理年出错\t{y}\t{date_info}")
            show_popup("SN码的日期存在数字0，无法转换为年份，不符合规则，请检查")
            sys.exit(1)
        try:
            # month_digit = str(int(date_info[1]) + 1) if date_info[1] == '0' else date_info[1]
            month_digit = date_info[1]
            month_part = month[month_digit]
        except Exception as m:
            logging.error(f"处理月出错\t{m}\t{date_info}")
            show_popup("SN码的日期存在数字0，无法转换为月份，不符合规则，请检查")
            sys.exit(1)
        try:
            day_digit = date_info[2]
            day_part = day[day_digit]
        except Exception as d:
            logging.error(f"处理日出错\t{d}\t{date_info}")
            show_popup("SN码的日期存在数字0，无法转换为日，不符合规则，请检查")
            sys.exit(1)
        real_date = f'{year}-{month_part}-{day_part}'
        return real_date
    except Exception as e:
        logging.error(e)
        return ""


def open_file():
    root = tk.Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    file_path1 = filedialog.askopenfilename(
        title="请选择表格文件",
        filetypes=[("Excel Files", "*.xlsx;*.xls")]
    )
    root.destroy()
    return file_path1


def read_data_from_excel(sheet_name=0) -> pd.DataFrame:
    try:
        global file_path
        if not file_path:
            file_path_excel = open_file()
            file_path = file_path_excel
        df1 = pd.read_excel(file_path, sheet_name=sheet_name)
        # 计算总请求次数
        global total_request_count
        if total_request_count == 0:
            total_request_count = df1.shape[0] + math.ceil(df1.shape[0] / batch_size)
        return df1
    except FileNotFoundError:
        sys.exit(0)


def send_data_to_lecoo(excel_data):
    global progress_window, progress_label, progress_bar_widget, progress_bar, txt_name
    txt_name = generate_timestamp()
    config = get_local_config()
    global planet_code
    option = 'CONFIG'
    manufacturer = config.get(option, 'ODM')
    producer = config.get(option, '生产工厂代码')
    planet_code = manufacturer + '-' + producer
    global mathine_api, material_api, pn_table_index_key
    mc = config.get(option, 'mathine_api')
    mathine_api = mc if mc is not None and mc != "" else mathine_api
    mt = config.get(option, 'material_api')
    material_api = mt if mt is not None and mt != "" else material_api
    pk = config.get(option, 'pn_key')
    pn_table_index_key = pk if pk is not None and pk != "" else pn_table_index_key

    # 重置进度计数
    progress_bar = 0

    try:
        # 创建进度窗口前确保之前的窗口已关闭
        if progress_window is not None and hasattr(progress_window, 'winfo_exists') and progress_window.winfo_exists():
            progress_window.destroy()
        create_progress_window()  # 创建进度窗口
        tbl_Machine_Sequence(excel_data)
        tbl_Packing_Machine_Material(excel_data)
        # 如果所有处理都完成但窗口还存在，手动更新一次
        file_path_tmp = f'resource/tmp/'
        new_name = file_path_tmp + (txt_name + '.xlsx')
        print(file_path_tmp, new_name)
        if file_path is not None and new_name is not None:
            shutil.copy(str(file_path), str(new_name))
        update_progress_window()
    except Exception as e:
        logging.error(f"处理数据时出错: {e}")
        # 确保即使发生错误，窗口也会关闭
        if progress_window is not None and hasattr(progress_window, 'winfo_exists') and progress_window.winfo_exists():
            progress_window.destroy()


def tbl_Machine_Sequence(df1: pd.DataFrame):
    global df_row
    df_row = df1.shape[0]
    params_rows = df1.iterrows()
    """主机信息上传方法"""
    api = mathine_api

    body = {
        "header": {
            "TRL": df_row,
            "PLANT": factory_code,
            "TXT_NAME": txt_name,
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
            "PACKING_LOT_NO": "",
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
        }
        if "set body_item":
            sn = extract_specific_cell_from_series(row, sn_key)
            print(sn)
            body_item["Machine_No"] = sn
            try:
                body_item["MATERIAL_NO"] = sn[: 9]
            except Exception as e:
                show_popup(
                    f"表格文件存在干扰的隐藏数据，请新建一个空的excel文件后，手动从有问题的表格数据复制到空的excel，建议使用ctrl+a键全选后粘贴到空的excel并保存")
                logging.error(f"获取物料号时出错: {e}")
                sys.exit(1)
            batch_no = extract_specific_cell_from_series(row, batch_number_key)
            body_item["PACKING_LOT_NO"] = batch_no if batch_no else " "  # 该字段无法填空值，会报错
            produce_date = convert_cycle_to_production_date(sn)
            body_item["START_DATE"] = produce_date if produce_date else loss_tip
            body_item["PLANT"] = planet_code
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
        if len(data_list_for_count) >= batch_size:
            body["Data"] = data_list_for_count
            request_handler(api, body)
            data_list_for_count = []
    #  循环结束后将剩余的部分（即不满足一批的）继续发送
    if data_list_for_count:
        body["Data"] = data_list_for_count
        request_handler(api, body)


def tbl_Packing_Machine_Material(df1: pd.DataFrame):
    params_rows = df1.iterrows()
    global df_row
    df_row += df1.shape[0]
    key_to_remove = ['序号', sn_key, '批次号', '日期']
    keys = list(df1.keys())
    keys = list(filter(lambda x: x not in key_to_remove, keys))
    """读取PN表"""
    try:
        df2: pd.DataFrame = read_data_from_excel(1)
    except Exception as e:
        logging.error(f"读取PN表时出错: {e}")
        show_popup("缺少第二张表：如8码表")
        sys.exit(1)
    cols = list(df2.columns)
    cols.insert(0, cols.pop(cols.index(pn_table_index_key)))
    df2 = df2[cols]
    df2.set_index(cols[0], inplace=True)
    """主机信息上传方法"""
    api = material_api
    global token
    body = {
        "header": {
            "TRL": df_row,
            "PLANT": planet_code,
            "TXT_NAME": txt_name,
            "TXT_NUM": "",
            "TXT_SOURCE": "PRC"
        },
        "Data": []
    }
    # 将所有行上传到接口
    for row in params_rows:
        body_item = {
            "MACHINE_NO": "",
            "MATERIAL_BARCODE_PRE": "",
            "AUTO_ID": "",
            "MATERIAL_BARCODE": "",
            "CREATE_DATE_TIME": "",
            "MATERIAL_NO": "",
            "VF_NAME": "",
            "MATERIAL_CLASS_CODE": "",  # TODO 填空
            "PLANT_CODE": "",
            "CS_FILE_TYPE": "",
            "SITE_TYPE": "",
            "MTMSN": "",
            "PACKING_LOT_NO": "",  # TODO 批次号应该也需要单独一张表，需要跟工厂对接，应该是部件的详细表
            "MODEL": "",
            "PRINTED_DESC": "",
            "PRODUCT_DATE": "",  # TODO 产品编码应该也需要单独一张表，需要跟工厂对接，应该是部件的详细表
            "SCAN_DATE": "",  # TODO 出库日期应该也需要单独一张表，需要跟工厂对接，应该是部件的详细表
            "LUCKY_NO": "",
            "SALEORDER": "NA",
            "COUNTRY": "NA",
            "QTY": 1,
            "PO": "NA",
            "ADD_DEL_FLAG": "A",
            "SHELL_IND": "-"
        }
        if "set body_item":
            sn = extract_specific_cell_from_series(row, sn_key)
            body_item["MACHINE_NO"] = sn
            create_date = convert_cycle_to_production_date(sn)
            # 创建日期应该需要重写，大概率是每一个码都有自己的生产日期，而不是主机的生产日期
            body_item["CREATE_DATE_TIME"] = create_date if create_date else loss_tip  # TODO
            factory_type = extract_specific_cell_from_series(row, factory_type_key)
            body_item["SITE_TYPE"] = factory_type if factory_type else no_factory_type_key
            # 设置 MODEL 码，因为与主机的8码一致所以不需要循环遍历
            body_item["MODEL"] = sn[:9]
            # 以单元格级别逐个提交接口了，而不是跟主机一样按照行进行提交接口
            for _ in keys:
                # if _ in df2.index:
                #     value = df2.loc[_].iloc[0]  # 取消使用列标题定位具体值，使用列的下标,满足不同产品也能使用
                #     # 根据索引和列标题定位在表2，定位到对应的pn码
                #     body_item['MATERIAL_NO'] = value
                #     body_item['MATERIAL_CLASS_CODE'] = loss_tip
                #     body_item["MODEL"] = sn[:9]
                # else:
                #     body_item['MATERIAL_NO'] = loss_tip

                # 获取部件条码
                component = extract_specific_cell_from_series(row, _)
                component = component if pd.notna(component) else loss_tip
                if 'SN' in component:
                    component = component.split('SN:', 1)[1]
                    meterial_date = create_date
                    # 设置MATERIAL_NO
                    body_item['MATERIAL_NO'] = component
                else:
                    meterial_date = extract_component_production_date(component)
                    body_item['MATERIAL_NO'] = component[3:12]
                body_item['MATERIAL_BARCODE'] = component  # 字典修改是在原引用对象的基础上修改的，所以后续的修改还是会修改这个对象，最终导致列表里面的元素都是一样的
                body_item['PRODUCT_DATE'] = meterial_date if meterial_date else loss_tip
                # body['Data'].append(body_item) # 字典修改是在原引用对象的基础上修改的，所以后续的修改还是会修改这个对象，最终导致列表里面的元素都是一样的
                body['Data'].append(body_item.copy())
            request_handler(api, body)
            body["Data"] = []


def request_handler(api, body):
    print(f"body:\t{json.dumps(body, ensure_ascii=False)}")

    def is_json(response1):
        try:
            response1.json()
            return True
        except ValueError:
            return False
        except Exception as e:
            logging.error(f"解析响应内容时出错：{e}")

    try:
        header = get_header()
        try:
            # 使用json模块进行序列化处理
            # 这会将所有NumPy和pandas特殊类型转换为Python标准类型
            json_body = json.loads(json.dumps(body, default=str))
            response = requests.post(api, json=json_body, headers=header)
        except Exception as e:
            show_popup(f"请求接口时出错：{e}")
            logging.error(f"请求接口时出错：{e}")
            sys.exit()

        # 获取正确的状态码并安全地调用处理函数
        try:
            if is_json(response):
                status_code = int(response.json().get("code"))
                handler = status_code_handlers.get(status_code, handle_default)
            else:
                handler = status_code_handlers.get(response.status_code, handle_default)

            # 安全地调用处理函数
            try:
                handler(response)
            except TokenExpired as e:
                header = get_header()
                logging.info(f"codeNum-343：Token过期，错误信息：{e}")
                # 重新请求接口
                response = requests.post(api, json=body, headers=header)
                logging.info(f"重新获取请求token后的请求结果：{response.text}")
            except tk.TclError:
                # 窗口可能已被销毁，但我们仍然想增加进度计数
                global progress_bar
                if handler == handle_200:  # 如果是成功处理函数
                    progress_bar += 1
            except Exception as e:
                logging.warning(f"处理响应时出错: {e}\t状态码：{response.status_code}\ttxt：{response.text}")
        except Exception as e:
            logging.warning(f"处理响应时出错: {e}\t状态码：{response.status_code}\ttxt：{response.text}")
        print(response.text, f'\t{response.status_code}')
    except ConnectionError:
        show_popup("无法连接服务器，请检查网络连接")
        header = get_header()
        response = requests.post(api, json=body, headers=header)
        logging.info(f"重新获取请求token后的请求结果：{response.text}")
    except Timeout:
        show_popup("请求超时，请重试")
    except HTTPError as e:
        show_popup(f"HTTP错误发生: {e}")
    except Exception as e:
        logging.error(f"接口请求失败，错误信息：{e}")


def get_daily_counter():
    """
    基于当前日期生成每日计数器值，并将其保存到一个文件中。
    """
    global counter
    current_date = datetime.date.today().strftime("%Y%m%d")
    filename = "resource/tmp/counter.txt"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
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


def get_local_config():
    config = configparser.ConfigParser()
    if os.path.exists("config.ini"):
        config.read("config.ini", encoding='utf-8')
        if not config.sections() or not config.has_section('CONFIG') or not config.options('CONFIG'):
            config['CONFIG'] = {
                '生产工厂代码': '',
                '每批处理数量': '',
                'ODM': 'OST'
            }
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
    else:
        logging.info("未找到配置文件，开始创建配置文件")
        config['CONFIG'] = {
            '生产工厂代码': '',
            '每批处理数量': '',
            'ODM': 'OST',
            'token_api': '',
            'mathine_api': '',
            'material_api': '',
            'consumer_key': '',
            'consumer_secret': '',
            'pn_key': ''
        }
        with open('config.ini', 'w', encoding='utf-8') as configfile:
            config.write(configfile)
    return config


get_token()
df = read_data_from_excel()
send_data_to_lecoo(df)
