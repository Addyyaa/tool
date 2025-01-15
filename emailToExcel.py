import email
from email import policy
from email.parser import BytesParser
from pathlib import Path
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox


def readFile(fileName):
    """读取单个 .eml 文件内容"""
    with open(fileName, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)
    return msg


def list_files(directory):
    """遍历目录下所有 .eml 文件并提取 'to' 字段"""
    data = []
    path = Path(directory)
    for file_path in path.rglob('*.eml'):
        if file_path.is_file():
            msg = readFile(file_path)
            if 'to' in msg:  # 确保字段存在
                data.append(msg['to'])
    return list(set(data))  # 去重


def data_to_excel(data, output_dir):
    """将邮箱数据保存到 Excel"""
    if not data:
        messagebox.showinfo("结果", "未找到任何邮箱数据")
        return

    data_dict = {
        '用户邮箱': data
    }
    df = pd.DataFrame(data_dict, index=range(1, len(data) + 1))
    output_file = Path(output_dir) / 'PinturaExcel.xlsx'

    # 调整写入参数，避免警告
    with pd.ExcelWriter(output_file, mode='w', engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='邮箱列表', index=False)

    messagebox.showinfo("完成", f"数据已成功保存到:\n{output_file}")


def choose_directory():
    """打开文件夹选择对话框"""
    root = tk.Tk()
    root.withdraw()
    directory = filedialog.askdirectory(title='请选择邮箱导出文件的所在目录')
    return directory


# 主程序
if __name__ == '__main__':
    directory = choose_directory()
    if not directory:
        messagebox.showwarning("警告", "未选择任何目录，程序将退出。")
    else:
        email_data = list_files(directory)
        data_to_excel(email_data, directory)
