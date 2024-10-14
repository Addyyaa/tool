import os.path
import sys
from tkinter import filedialog

from PIL import Image
import tkinter as tk


def select_images():
    try:
        root = tk.Tk()
        root.withdraw()
        root.update()  # Ensure root window is fully created
        files = filedialog.askopenfilenames(
            title="选择图片",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.mp4")]
        )
        root.destroy()
        if files:
            print(f"选择的文件: {files}")
        else:
            print("未选择任何文件")
        print("文件选择流程完成")
        return files
    except Exception as e:
        print(f"发生错误: {e}")
        return ()


def select_folder():
    try:
        root = tk.Tk()
        root.withdraw()
        root.update()  # Ensure root window is fully created
        folder = filedialog.askdirectory()
        root.destroy()
        if folder:
            print(f"选择的文件夹: {folder}")
        else:
            print("未选择任何文件夹")
        print("文件夹选择流程完成")
        return folder
    except Exception as e:
        print(f"发生错误: {e}")
        return ()


def resize_image(target_size):
    file_path = select_images()
    for i in file_path:
        try:
            # 打开图片
            with Image.open(i) as img:
                # 调整图片大小
                img = img.resize(target_size, Image.LANCZOS)
                # 保存调整后的图片
                file_name = os.path.basename(i)
                output_path = select_folder()
                output_path = os.path.join(output_path, file_name)
                img.save(output_path)
                print(f"图片已成功调整为{target_size}并保存为{output_path}")
        except Exception as e:
            print(f"处理图片时出错: {e}")


if __name__ == "__main__":
    while True:
        # 用户输入文件路径和目标分辨率
        try:
            width = int(input("请输入目标宽度："))
            height = int(input("请输入目标高度："))
        except Exception:
            sys.exit(1)

        # 调用函数
        resize_image((width, height))
