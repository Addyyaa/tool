from fontTools.ttLib import TTFont
import tkinter as tk
from tkinter import filedialog

def otf_to_ttf():
    def select_files():
        try:
            print("Initializing Tkinter...")
            root = tk.Tk()
            print("Tkinter initialized.")
            root.withdraw()
            print("Root window withdrawn.")
            root.update()  # Ensure root window is fully created
            print("Root window updated.")
            files = filedialog.askopenfilenames(
                title="选择字体文件",
                filetypes=[("OTF Files", "*.otf")]
            )
            print("File dialog opened.")
            root.destroy()
            print("Root window destroyed.")
            if files:
                print(f"选择的文件: {files}")
            else:
                print("未选择任何文件")
            print("文件选择流程完成")
            return files
        except Exception as e:
            print(f"发生错误: {e}")
            return ()

    # 获取用户选择的文件
    file_paths = select_files()

    if not file_paths:  # 如果没有选择文件，直接退出
        print("没有选择任何文件，程序终止。")
        return

    # 获取保存路径
    save_dir = filedialog.askdirectory()
    if not save_dir:  # 如果没有选择保存路径，直接退出
        print("没有选择保存路径，程序终止。")
        return

    # 遍历每个选中的文件并转换
    for file_path in file_paths:
        try:
            # 提取文件名和扩展名
            file_name = file_path.split("/")[-1].split(".")[0]
            output_path = f"{save_dir}/{file_name}.woff2"

            # 加载字体并转换
            font = TTFont(file_path)  # 注意这里传入的是单个文件路径
            font.flavor = "woff2"
            font.save(output_path)
            print(f"成功将 {file_path} 转换为 {output_path}")
        except Exception as e:
            print(f"转换文件 {file_path} 时发生错误: {e}")

# 示例调用
otf_to_ttf()