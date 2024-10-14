import numpy as np
from PIL import Image

def load_fb_raw_image(raw_file_path, width, height):
    try:
        # 计算每个像素的字节数
        bytes_per_pixel = 4  # 假设是32位（4字节）

        # 计算文件的期望大小
        expected_size = width * height * bytes_per_pixel

        # 打开文件并读取前 expected_size 字节
        with open(raw_file_path, 'rb') as f:
            raw_data = f.read(expected_size)

        # 检查实际读取的字节数是否等于期望大小
        if len(raw_data) != expected_size:
            print(f"File size does not match expected dimensions: {len(raw_data)} != {expected_size}")
            return None

        # 将二进制数据转换为 numpy 数组，每个像素4字节
        image_array = np.frombuffer(raw_data, dtype=np.uint32).reshape((height, width))

        # 测试不同的通道排列方式
        # 1. ARGB8888
        a = (image_array >> 24) & 0xFF  # Alpha 通道
        r = (image_array >> 16) & 0xFF  # 红色通道
        g = (image_array >> 8) & 0xFF   # 绿色通道
        b = image_array & 0xFF          # 蓝色通道

        # # 2. RGBA8888 (尝试不同顺序)
        # r = (image_array >> 24) & 0xFF  # 红色通道
        # g = (image_array >> 16) & 0xFF  # 绿色通道
        # b = (image_array >> 8) & 0xFF   # 蓝色通道
        # a = image_array & 0xFF          # Alpha 通道

        # # 3. BGRA8888 (另一种顺序)
        # b = (image_array >> 24) & 0xFF  # 蓝色通道
        # g = (image_array >> 16) & 0xFF  # 绿色通道
        # r = (image_array >> 8) & 0xFF   # 红色通道
        # a = image_array & 0xFF          # Alpha 通道

        # 合并成RGBA图像
        image_array = np.stack((r, g, b, a), axis=-1)

        # 将 numpy 数组转换为 Pillow 图像
        image = Image.fromarray(image_array, 'RGBA')
        return image

    except Exception as e:
        print(f"An error occurred while processing the file: {str(e)}")
        return None

def show_image(image):
    if image:
        image.show()
    else:
        print("No image to display.")

if __name__ == "__main__":
    raw_file_path = "fb0.raw"  # 这里填写你的 RAW 文件路径
    width = 1920  # 从fbset获取的宽度
    height = 1200  # 从fbset获取的高度

    image = load_fb_raw_image(raw_file_path, width, height)
    show_image(image)
