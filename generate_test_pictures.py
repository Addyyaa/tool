import os
import random
import sys
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter.filedialog import askdirectory


# 生成随机分辨率，确保不重复
def generate_resolutions(count, min_res=100, max_res=8000):
    resolutions = set()
    while len(resolutions) < count:
        width = random.randint(min_res, max_res)
        height = random.randint(min_res, max_res)
        resolution = (width, height)
        if resolution not in resolutions:
            resolutions.add(resolution)
    return list(resolutions)


def select_folder():
    """
    弹窗让用户选择保存路径
    """
    # 创建一个隐藏的Tkinter主窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 设置窗口为置顶
    root.wm_attributes("-topmost", 1)

    # 弹出文件选择对话框，选择图片文件
    image_paths = askdirectory(title="请选择保存图片的文件夹")

    # 关闭主窗口
    root.destroy()

    if image_paths:
        return image_paths  # 返回选择的文件夹路径
    print("未选择保存文件夹，程序终止。")
    sys.exit(1)


# 生成图片并保存
def create_images(count, folder_path):
    resolutions = generate_resolutions(count)
    for i, (width, height) in enumerate(resolutions, 1):
        # 创建空白图片
        img = Image.new('RGB', (width, height), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 设置字体（可以根据系统路径调整字体路径）
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default()

        # 图片中显示分辨率
        text = f"{width}x{height}"
        # 使用 textbbox 计算文本边界框
        bbox = draw.textbbox((0, 0), text, font=font)
        textwidth = bbox[2] - bbox[0]  # 右边界减去左边界
        textheight = bbox[3] - bbox[1]  # 底边减去顶边
        text_x = (width - textwidth) // 2
        text_y = (height - textheight) // 2

        # 绘制文字在图片中心
        draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255))

        # 拼接保存路径，确保正确的文件名拼接
        save_path = os.path.join(folder_path, f"image_{i}.png")

        # 保存图片，文件名按序号命名
        img.save(save_path)
        print(f"已生成图片：{save_path}，分辨率：{width}x{height}")


# 获取用户输入的图片数量
image_count = int(input("请输入要生成的图片数量: "))
image_save_path = select_folder()
create_images(image_count, image_save_path)
