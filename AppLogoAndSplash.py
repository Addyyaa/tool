import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import json

class ImageResolutionConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("图片分辨率转换工具")
        self.root.geometry("800x600")
        self.root.minsize(600, 500)  # 设置最小窗口大小
        
        # 监听窗口大小变化
        self.root.bind("<Configure>", self.on_window_resize)
        
        # 默认分辨率配置
        self.splash_resolutions = {
            "iPhone SE": "640x1136",
            "iPhone 8": "750x1334",
            "iPhone 8 Plus": "1242x2208",
            "iPhone X/XS/11 Pro": "1125x2436",
            "iPhone XR/11": "828x1792",
            "iPhone XS Max/11 Pro Max": "1242x2688",
            "iPhone 12/13/14": "1170x2532",
            "iPhone 12/13/14 Pro Max": "1284x2778",
            "主流安卓手机": "1080x1920"
        }
        
        self.icon_resolutions = {
            "iPhone 应用图标": "1024x1024",
            "Android 高分辨率": "192x192",
            "Android 中等分辨率": "144x144",
            "Android 低分辨率": "96x96",
            "App Store": "512x512",
            "Google Play": "512x512"
        }
        
        self.selected_image_path = None
        self.output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "转换后的图片")
        self.custom_resolutions = []
        self.selected_type = tk.StringVar(value="启动图")
        
        # 配置根窗口的网格权重，使得内容可以随窗口大小调整
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        self.create_widgets()
        
    def create_widgets(self):
        # 创建主框架 - 使用Grid布局
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # 配置主框架的行列权重
        main_frame.grid_rowconfigure(1, weight=1)  # 预览区域可以扩展
        main_frame.grid_columnconfigure(0, weight=0)  # 左侧控制区域固定宽度
        main_frame.grid_columnconfigure(1, weight=1)  # 右侧预览区域可以扩展
        
        # 顶部区域 - 图片选择
        image_frame = ttk.LabelFrame(main_frame, text="图片选择")
        image_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        select_button = ttk.Button(image_frame, text="选择图片", command=self.select_image)
        select_button.grid(row=0, column=0, padx=5, pady=5)
        
        self.image_label = ttk.Label(image_frame, text="未选择图片")
        self.image_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # 左侧 - 选项区域
        options_frame = ttk.LabelFrame(main_frame, text="输出选项")
        options_frame.grid(row=1, column=0, sticky="n", padx=(0, 10))
        
        # 类型选择
        type_frame = ttk.Frame(options_frame)
        type_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        splash_radio = ttk.Radiobutton(type_frame, text="启动图", variable=self.selected_type, 
                                      value="启动图", command=self.update_resolution_display)
        splash_radio.grid(row=0, column=0, padx=5)
        
        icon_radio = ttk.Radiobutton(type_frame, text="APP图标", variable=self.selected_type, 
                                     value="APP图标", command=self.update_resolution_display)
        icon_radio.grid(row=0, column=1, padx=5)
        
        # 右侧 - 预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="图片预览")
        preview_frame.grid(row=1, column=1, sticky="nsew", pady=(0, 10))
        preview_frame.grid_rowconfigure(0, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)
        
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # 分辨率显示区域 - 在左侧控制区域下方
        self.resolution_frame = ttk.LabelFrame(main_frame, text="默认输出分辨率")
        self.resolution_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # 自定义分辨率输入
        custom_frame = ttk.LabelFrame(main_frame, text="自定义分辨率")
        custom_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.custom_entry = ttk.Entry(custom_frame, width=15)
        self.custom_entry.grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Label(custom_frame, text="格式: 宽x高, 例如: 800x600").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        add_button = ttk.Button(custom_frame, text="添加", command=self.add_custom_resolution)
        add_button.grid(row=0, column=2, padx=5, pady=5)
        
        # 自定义分辨率列表
        custom_list_frame = ttk.LabelFrame(main_frame, text="自定义分辨率列表")
        custom_list_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # 配置列表框的权重
        custom_list_frame.grid_columnconfigure(0, weight=1)
        
        self.custom_listbox = tk.Listbox(custom_list_frame, height=4)
        self.custom_listbox.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        delete_button = ttk.Button(custom_list_frame, text="删除", command=self.delete_custom_resolution)
        delete_button.grid(row=0, column=1, padx=5, pady=5)
        
        # 输出目录选择
        output_frame = ttk.LabelFrame(main_frame, text="输出目录")
        output_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # 配置输出框架的权重
        output_frame.grid_columnconfigure(0, weight=1)
        
        self.output_label = ttk.Label(output_frame, text=self.output_dir)
        self.output_label.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        output_button = ttk.Button(output_frame, text="选择目录", command=self.select_output_dir)
        output_button.grid(row=0, column=1, padx=5, pady=5)
        
        # 转换按钮
        convert_button = ttk.Button(main_frame, text="开始转换", command=self.convert_images)
        convert_button.grid(row=6, column=0, columnspan=2, pady=10)
        
        # 默认显示启动图分辨率
        self.update_resolution_display()
        
    def select_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.image_label.config(text=os.path.basename(file_path))
            self.display_preview(file_path)
    
    def display_preview(self, image_path):
        try:
            image = Image.open(image_path)
            
            # 获取预览框架的大小
            preview_width = self.preview_label.winfo_width()
            preview_height = self.preview_label.winfo_height()
            
            # 确保有合理的预览尺寸
            if preview_width < 50: preview_width = 300
            if preview_height < 50: preview_height = 300
            
            # 保持纵横比缩放图像
            image_width, image_height = image.size
            ratio = min(preview_width/image_width, preview_height/image_height)
            new_width = int(image_width * ratio)
            new_height = int(image_height * ratio)
            
            # 调整图片大小
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # 转换为PhotoImage并显示
            photo = ImageTk.PhotoImage(resized_image)
            self.preview_label.config(image=photo)
            self.preview_label.image = photo  # 保持引用防止被垃圾回收
        except Exception as e:
            messagebox.showerror("错误", f"无法预览图片: {str(e)}")
    
    def update_resolution_display(self):
        # 清除当前显示的分辨率
        for widget in self.resolution_frame.winfo_children():
            widget.destroy()
        
        # 获取当前选择的类型对应的分辨率
        if self.selected_type.get() == "启动图":
            resolutions = self.splash_resolutions
        else:
            resolutions = self.icon_resolutions
        
        # 创建Checkbutton显示分辨率 - 使用Grid布局
        row, col = 0, 0
        self.resolution_vars = {}
        
        for name, res in resolutions.items():
            var = tk.BooleanVar(value=True)
            self.resolution_vars[name] = var
            cb = ttk.Checkbutton(self.resolution_frame, text=f"{name}: {res}", variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            
            col += 1
            if col >= 3:  # 每行显示3个选项
                col = 0
                row += 1
    
    def add_custom_resolution(self):
        resolution = self.custom_entry.get().strip()
        if not resolution:
            return
            
        # 验证格式 (宽x高)
        if not self.validate_resolution(resolution):
            messagebox.showerror("错误", "分辨率格式不正确，请使用 宽x高 格式，例如: 800x600")
            return
            
        if resolution not in self.custom_resolutions:
            self.custom_resolutions.append(resolution)
            self.custom_listbox.insert(tk.END, resolution)
            self.custom_entry.delete(0, tk.END)
    
    def validate_resolution(self, resolution):
        try:
            width, height = resolution.lower().split('x')
            return width.isdigit() and height.isdigit()
        except:
            return False
    
    def delete_custom_resolution(self):
        selected = self.custom_listbox.curselection()
        if selected:
            index = selected[0]
            resolution = self.custom_listbox.get(index)
            self.custom_listbox.delete(index)
            self.custom_resolutions.remove(resolution)
    
    def select_output_dir(self):
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir = directory
            self.output_label.config(text=directory)
    
    def convert_images(self):
        if not self.selected_image_path:
            messagebox.showerror("错误", "请先选择一张图片")
            return
        
        try:
            # 创建输出目录
            os.makedirs(self.output_dir, exist_ok=True)
            
            # 打开原始图片
            original_image = Image.open(self.selected_image_path)
            
            # 获取需要转换的分辨率
            resolutions_to_convert = []
            
            # 添加选中的默认分辨率
            if self.selected_type.get() == "启动图":
                resolutions_dict = self.splash_resolutions
            else:
                resolutions_dict = self.icon_resolutions
                
            for name, var in self.resolution_vars.items():
                if var.get():
                    resolution = resolutions_dict[name]
                    resolutions_to_convert.append((name, resolution))
            
            # 添加自定义分辨率
            for i, resolution in enumerate(self.custom_resolutions):
                resolutions_to_convert.append((f"自定义{i+1}", resolution))
            
            # 转换图片
            for name, resolution in resolutions_to_convert:
                width, height = map(int, resolution.lower().split('x'))
                resized_image = self.resize_image(original_image, width, height)
                
                # 保存转换后的图片
                filename = f"{os.path.splitext(os.path.basename(self.selected_image_path))[0]}_{name}_{width}x{height}.png"
                output_path = os.path.join(self.output_dir, filename)
                resized_image.save(output_path)
            
            messagebox.showinfo("成功", f"已成功转换 {len(resolutions_to_convert)} 张图片，保存在：{self.output_dir}")
            
        except Exception as e:
            messagebox.showerror("错误", f"转换过程中出错: {str(e)}")
    
    def resize_image(self, image, width, height):
        # 创建一个新的空白图像
        if self.selected_type.get() == "APP图标":
            # 对于图标，保持原比例并居中
            new_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            
            # 计算保持纵横比的尺寸
            ratio = min(width / image.width, height / image.height)
            new_width = int(image.width * ratio)
            new_height = int(image.height * ratio)
            
            # 重新调整大小
            resized = image.resize((new_width, new_height), Image.LANCZOS)
            
            # 计算粘贴位置（居中）
            paste_x = (width - new_width) // 2
            paste_y = (height - new_height) // 2
            
            # 粘贴到新图像
            new_image.paste(resized, (paste_x, paste_y))
            return new_image
        else:
            # 对于启动图，拉伸填满
            return image.resize((width, height), Image.LANCZOS)

    def on_window_resize(self, event):
        # 只在根窗口调整大小时更新预览
        if event.widget == self.root and self.selected_image_path:
            # 延迟更新预览，避免频繁刷新
            self.root.after(100, lambda: self.display_preview(self.selected_image_path))

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageResolutionConverter(root)
    root.mainloop()
