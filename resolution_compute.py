def scale_resolution(width, height, long_bord=1920, short_bord=1200):
    # 计算宽高比
    aspect_ratio = width / height
    
    return width, height


def main():
    # 获取用户输入的分辨率
    try:
        input_long = int(input("请输入不能超过的长边 (像素): "))
        input_short = int(input("请输入不能超过的短边 (像素): "))
    except ValueError:
        print("无效输入，请输入有效的整数值。")
        return

    # 执行等比例缩放
    scaled_width, scaled_height = scale_resolution(long_bord=input_long, short_bord=input_short)

    # 输出缩放后的分辨率
    print(f"等比例缩放后的分辨率: {scaled_width} x {scaled_height}")


if __name__ == "__main__":
    main()
