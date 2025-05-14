# -*- coding: utf-8 -*-
import tkinter as tk
from concurrent.futures import thread
from tkinter import filedialog, messagebox, ttk
import os
import comtypes.client
from threading import Thread
import queue

# 初始化主窗口
root = tk.Tk()
root.title("PPT转PDF工具")
root.geometry("600x400")  # 设置窗口大小

# 创建队列用于状态更新
status_queue = queue.Queue()


# 选择文件夹并更新输入框
def select_folder(entry):
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)


# 执行PPT到PDF的转换
def convert_ppt_to_pdf(input_folder, output_folder, quality, same_folder):
    total_files = 0
    converted_files = 0
    for root_dir, dirs, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(('.ppt', '.pptx')):
                total_files += 1
    status_queue.put(f"总共找到 {total_files} 个PPT文件待转换")
    
    for root_dir, dirs, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(('.ppt', '.pptx')):
                ppt_path = os.path.join(root_dir, file)
                if same_folder:
                    pdf_path = os.path.splitext(ppt_path)[0] + '.pdf'
                else:
                    rel_path = os.path.relpath(root_dir, input_folder)
                    output_dir = os.path.join(output_folder, rel_path)
                    os.makedirs(output_dir, exist_ok=True)
                    pdf_path = os.path.join(output_dir, os.path.splitext(file)[0] + '.pdf')

                if os.path.exists(pdf_path):
                    status_queue.put(f"跳过：{pdf_path} 已存在")
                    converted_files += 1
                    continue

                try:
                    ppt_app = comtypes.client.CreateObject("PowerPoint.Application")
                    presentation = ppt_app.Presentations.Open(ppt_path)
                    if quality == "无损质量":
                        intent = 1  # 无损质量，等同于打印质量
                    elif quality == "高质量 (打印)":
                        intent = 1  # 打印质量
                    else:
                        intent = 0  # 屏幕质量
                    presentation.ExportAsFixedFormat(pdf_path, 2, Intent=intent)  # 2表示PDF格式
                    presentation.Close()
                    ppt_app.Quit()
                    converted_files += 1
                    status_queue.put(f"转换成功 ({converted_files}/{total_files})：{ppt_path} -> {pdf_path}")
                except Exception as e:
                    status_queue.put(f"转换失败 ({converted_files+1}/{total_files}) {ppt_path}：{str(e)}")


# 启动转换线程
def start_conversion():
    input_folder = input_entry.get()
    output_folder = output_entry.get()
    quality = quality_var.get()
    same_folder = same_folder_var.get()

    if not input_folder:
        messagebox.showerror("错误", "请选择输入文件夹")
        return
    if not same_folder and not output_folder:
        messagebox.showerror("错误", "请选择输出文件夹或勾选'保存到原文件夹'")
        return

    log_text.delete(1.0, tk.END)
    log_text.insert(tk.END, "开始转换...\n")
    global conversion_thread
    conversion_thread = Thread(target=convert_ppt_to_pdf, args=(input_folder, output_folder, quality, same_folder))
    conversion_thread.start()
    root.after(100, check_queue)


# 检查队列并更新日志
def check_queue():
    while True:
        try:
            message = status_queue.get_nowait()
            log_text.insert(tk.END, message + '\n')
            log_text.see(tk.END)
        except queue.Empty:
            break
    if 'conversion_thread' in globals() and conversion_thread.is_alive():
        root.after(100, check_queue)
    else:
        log_text.insert(tk.END, "转换完成。\n")


# GUI布局
# 输入文件夹选择
input_frame = tk.Frame(root)
input_frame.pack(pady=10, padx=10, fill=tk.X)
tk.Label(input_frame, text="输入文件夹：", width=15, anchor='e').pack(side=tk.LEFT)
input_entry = tk.Entry(input_frame, width=50)
input_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
tk.Button(input_frame, text="浏览", command=lambda: select_folder(input_entry)).pack(side=tk.LEFT, padx=5)

# 输出文件夹选择
output_frame = tk.Frame(root)
output_frame.pack(pady=10, padx=10, fill=tk.X)
tk.Label(output_frame, text="输出文件夹：", width=15, anchor='e').pack(side=tk.LEFT)
output_entry = tk.Entry(output_frame, width=50)
output_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
tk.Button(output_frame, text="浏览", command=lambda: select_folder(output_entry)).pack(side=tk.LEFT, padx=5)

# 是否保存到原文件夹
same_folder_var = tk.BooleanVar()
tk.Checkbutton(root, text="将PDF保存到与PPT相同的文件夹", variable=same_folder_var).pack(pady=5)

# 转换质量选择
quality_frame = tk.Frame(root)
quality_frame.pack(pady=10, padx=10, fill=tk.X)
tk.Label(quality_frame, text="转换质量：", width=15, anchor='e').pack(side=tk.LEFT)
quality_var = tk.StringVar()
quality_combobox = ttk.Combobox(quality_frame, textvariable=quality_var,
                                values=["无损质量", "高质量 (打印)", "低质量 (屏幕)"], state="readonly")
quality_combobox.pack(side=tk.LEFT, expand=True, fill=tk.X)
quality_combobox.current(0)  # 默认无损质量

# 开始转换按钮
tk.Button(root, text="开始转换", command=start_conversion, bg='#4CAF50', fg='white', font=('Arial', 12, 'bold')).pack(pady=10)

# 日志显示区域
log_frame = tk.Frame(root)
log_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
log_text = tk.Text(log_frame, height=10)
log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
log_text.config(yscrollcommand=scrollbar.set)

# 运行主循环
root.mainloop()