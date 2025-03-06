from PIL import Image
import os
import numpy as np

# Constants
TARGET_SIZE = 20 * 1024 * 1024  # 20MB 大小
WIDTH = 1280


def generate_image_with_size():
    height = 1000
    max_attempts = 50

    for attempt in range(max_attempts):
        data = np.random.randint(0, 256, (height, WIDTH, 3), dtype=np.uint8)  # 生成一个3三层的二位数组，每层数组行数为height，列数为WIDTH
        img = Image.fromarray(data, "RGB")

        # Save as PNG
        temp_path = "temp.png"
        img.save(temp_path, "PNG", optimize=True)
        current_size = os.path.getsize(temp_path)

        print(f"Height: {height}, Size: {current_size / 1024 / 1024: .2f} MB")

        if abs(current_size - TARGET_SIZE) <= 1 * 1024 * 1024:
            break

        # Adjust height
        if current_size < TARGET_SIZE:
            height = int(height * 1.5)
        else:
            height = int(height * 0.8)

    # Final output
    img.save("output_20mb.png", "PNG")
    final_size = os.path.getsize("output_20mb.png")
    print(f"Final size: {final_size / 1024 / 1024: .2f} MB, Resolution: {WIDTH}x{height}")


if __name__ == "__main__":
    generate_image_with_size()
