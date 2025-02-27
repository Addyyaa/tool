import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os

# 创建主窗口
root = tk.Tk()
root.title("文件内容提取器")
root.geometry("400x300")

# 全局变量，用于存储文件路径和保存目录
file_path = ""
save_dir = ""

# 提取下载链接的函数
def extract_links(text):
    # 使用正则表达式匹配 http 或 https 开头的链接
    link_pattern = r'https?://[^\s"]+'
    links = re.findall(link_pattern, text)
    return links

# 选择文件的函数
def choose_file():
    global file_path
    file_path = filedialog.askopenfilename(
        title="选择文件",
        filetypes=(("文本文件", "*.txt *.ini"), ("所有文件", "*.*"))
    )
    if file_path:
        file_label.config(text=f"已选择文件: {os.path.basename(file_path)}")
    else:
        file_label.config(text="未选择文件")

# 选择保存目录的函数
def choose_save_dir():
    global save_dir
    save_dir = filedialog.askdirectory(title="选择保存目录")
    if save_dir:
        dir_label.config(text=f"保存目录: {save_dir}")
    else:
        dir_label.config(text="未选择保存目录")

# 处理文件并保存结果的函数
def process_file():
    if not file_path:
        messagebox.showerror("错误", "请先选择一个文件！")
        return
    if not save_dir:
        messagebox.showerror("错误", "请先选择保存目录！")
        return

    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取链接
        links = extract_links(content)

        # 保存结果到文件
        output_file = os.path.join(save_dir, "extracted_links.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            if links:
                f.write("提取到的下载链接:\n")
                for link in links:
                    f.write(f"{link}\n")
            else:
                f.write("未找到任何下载链接。\n")

        messagebox.showinfo("成功", f"结果已保存到: {output_file}")
    except Exception as e:
        messagebox.showerror("错误", f"处理失败: {str(e)}")

# UI 布局
# 文件选择部分
file_label = tk.Label(root, text="未选择文件", wraplength=350)
file_label.pack(pady=10)

file_button = tk.Button(root, text="选择文件", command=choose_file)
file_button.pack(pady=5)

# 保存目录选择部分
dir_label = tk.Label(root, text="未选择保存目录", wraplength=350)
dir_label.pack(pady=10)

dir_button = tk.Button(root, text="选择保存目录", command=choose_save_dir)
dir_button.pack(pady=5)

# 处理按钮
process_button = tk.Button(root, text="提取链接并保存", command=process_file)
process_button.pack(pady=20)

# 运行主循环
root.mainloop()