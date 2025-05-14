import os
from typing import Callable
import glob
import sys
import tkinter as tk
from tkinter import Toplevel
import re


class PKIDReader:
    def __init__(self):
        self.current_dir = os.getcwd()

    def read_pkid(self):
        file_contents = []
        pkids_list: list[dict] = []
        pkid_files = self.detect_pkid_file()

        def read_file():
            for file in pkid_files:
                with open(file, 'r') as f:
                    file_contents.append(f.read())

        def extract_pkid(file_contents1):
            for index, content in enumerate(file_contents1):
                pkid_pattern = r'KeyID=(.*?);'
                pkid_match = re.search(pkid_pattern, content)
                sn_pattern = r'ASSYSN=(.*?);'
                sn_match = re.search(sn_pattern, content)
                if pkid_match and sn_match:
                    pkid = pkid_match.group(1)
                    sn = sn_match.group(1)
                    pkids_list.append({'pkid': pkid, 'sn': sn})
                else:
                    if not pkid_match:
                        self.show_popup(f"未找到PKID，文件名：{pkid_files[index]}", self.exit_program)
                    if not sn_match:
                        self.show_popup(f"未找到SN，文件名：{pkid_files[index]}", self.exit_program)

        read_file()
        extract_pkid(file_contents)
        return pkids_list

    def detect_pkid_file(self) -> list:
        dirs = os.listdir(self.current_dir)
        if 'pkids' not in dirs:
            # 如果pkids文件夹不存在，则创建pkids文件夹
            os.makedirs(os.path.join(self.current_dir, 'pkids'))
            self.prompt_for_pikid_file()
            sys.exit()

        # 检测pkids文件夹下是否存在ini文件
        ini_pattern = os.path.join(self.current_dir, 'pkids', '*.ini')
        ini_files: list = glob.glob(ini_pattern)
        if ini_files:
            return ini_files
        else:
            self.prompt_for_pikid_file()
            sys.exit()

    def prompt_for_pikid_file(self):
        os.startfile(os.path.join(self.current_dir, 'pkids'))
        self.show_popup("未检测到PKID文件，请在pkids文件夹下添加PKID文件后重新运行程序！", self.exit_program)

    def exit_program(self):
        sys.exit()

    def show_popup(self, message: str, closed: Callable[[], None] = None):
        # 创建主窗口，但不显示
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口

        # 定义一个函数来处理关闭操作
        def on_closing():
            popup.destroy()
            if not any(w.winfo_exists() for w in root.winfo_children()):
                root.quit()
            if closed:
                closed()

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


if __name__ == "__main__":
    pkid_reader = PKIDReader()
    pkid_reader.read_pkid()
