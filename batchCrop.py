import os
from tkinter import Tk, filedialog, messagebox, StringVar, Label, OptionMenu, Button
from tkinter import ttk
from PIL import Image


def center_crop(image, target_ratio, is_vertical):
    width, height = image.size
    current_ratio = width / height

    if is_vertical:
        # 竖屏图片需要裁剪为10:16 或 9:16
        if target_ratio == (16 / 10):  # 裁剪为10:16
            target_ratio = 10 / 16
        else:  # 裁剪为9:16
            target_ratio = 9 / 16
    else:
        # 横屏图片需要裁剪为16:10 或 16:9
        if target_ratio == (16 / 10):  # 裁剪为16:10
            target_ratio = 16 / 10
        else:  # 裁剪为16:9
            target_ratio = 16 / 9

    current_ratio = width / height

    if current_ratio > target_ratio:  # 横屏或宽屏
        # 裁剪宽度，保持目标比例
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        right = left + new_width
        top = 0
        bottom = height
    else:  # 竖屏
        # 裁剪高度，保持目标比例
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        bottom = top + new_height
        left = 0
        right = width

    return image.crop((left, top, right, bottom))


def batch_crop(input_files, output_folder, target_ratio):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    total_files = len(input_files)
    for index, input_path in enumerate(input_files):
        try:
            filename = os.path.basename(input_path)
            output_path = os.path.join(output_folder, filename)

            with Image.open(input_path) as img:
                is_vertical = img.width < img.height  # 判断图片是竖屏还是横屏
                cropped_img = center_crop(img, target_ratio, is_vertical)
                cropped_img.save(output_path)
                print(f"Cropped {filename} from {img.size} to {cropped_img.size}")

            # 更新进度条
            progress['value'] = (index + 1) / total_files * 100
            root.update_idletasks()

        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while processing {filename}: {str(e)}")
            continue


# 添加一个全局变量来存储文件路径
input_files_path = []

def select_files(var):
    global input_files_path  # 使用全局变量
    file_selected = filedialog.askopenfilenames(
        title="Select Images",
        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")]
    )
    if file_selected:
        input_files_path = file_selected  # 存储文件路径
        var.set(f"{len(file_selected)} files selected")  # 显示文件数量




def select_folder(var):
    folder_selected = filedialog.askdirectory()
    var.set(folder_selected)


def start_cropping(aspect_ratio_var):
    input_files = input_files_path  # 使用存储的文件路径
    output_folder = output_folder_var.get()
    aspect_ratio = aspect_ratio_var.get()

    if not input_files or not output_folder:
        messagebox.showerror("Error", "Please select input images and output folder.")
        return

    if aspect_ratio == "16:9":
        target_ratio = 16 / 9
    elif aspect_ratio == "16:10":
        target_ratio = 16 / 10
    else:
        messagebox.showerror("Error", "Invalid aspect ratio. Please choose either 16:9 or 16:10.")
        return

    try:
        batch_crop(input_files, output_folder, target_ratio)
        messagebox.showinfo("Success", "Cropping completed successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")



# 创建主窗口
root = Tk()
root.title("Batch Image Cropper")

# 变量存储文件夹路径和目标比例
input_files_var = StringVar()
output_folder_var = StringVar()
aspect_ratio_var = StringVar(value="16:9")

# 创建并放置组件
Label(root, text="选择要裁剪的图片（支持批量裁剪）:").grid(row=0, column=0, padx=10, pady=10)
Button(root, text="选择", command=lambda: select_files(input_files_var)).grid(row=0, column=1, padx=10, pady=10)
Label(root, textvariable=input_files_var, wraplength=400).grid(row=0, column=2, padx=10, pady=10)

Label(root, text="选择文件夹进行保存:").grid(row=1, column=0, padx=10, pady=10)
Button(root, text="选择", command=lambda: select_folder(output_folder_var)).grid(row=1, column=1, padx=10, pady=10)
Label(root, textvariable=output_folder_var).grid(row=1, column=2, padx=10, pady=10)

Label(root, text="选择比例:").grid(row=2, column=0, padx=10, pady=10)
OptionMenu(root, aspect_ratio_var, "16:9", "16:10").grid(row=2, column=1, padx=10, pady=10)

Button(root, text="开始裁剪", command=lambda: start_cropping(aspect_ratio_var)).grid(row=3, column=0,
                                                                                           columnspan=3, pady=20)

# 添加进度条
progress = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress.grid(row=4, column=0, columnspan=3, pady=10)

# 运行应用
root.mainloop()
