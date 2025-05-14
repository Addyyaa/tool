import os
import sys
import json
import threading
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk

# 配置文件路径
CONFIG_FILE = "image_compress_config.json"

class ImageCompressor:
    """图片压缩工具核心类"""
    
    def __init__(self):
        self.output_dir = None
        self.quality = 90  # 默认压缩质量
    
    def set_output_directory(self, output_path):
        """设置输出目录，如果不存在则创建"""
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir
    
    def compress_image(self, image_path, quality=None):
        """压缩单个图片"""
        if quality is None:
            quality = self.quality
            
        try:
            # 打开图片
            img = Image.open(image_path)
            
            # 保持原始文件名但更改路径到输出目录
            filename = Path(image_path).name
            output_path = self.output_dir / filename
            
            # 如果是JPEG，直接压缩保存
            if img.format == 'JPEG':
                img.save(output_path, quality=quality, optimize=True)
            # 如果是PNG，转换为RGB然后保存为JPEG (如果有透明通道会丢失)
            elif img.format == 'PNG':
                # 检查是否有透明通道
                if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                    # 有透明通道，保存为PNG但优化
                    img.save(output_path, optimize=True)
                else:
                    # 无透明通道，可以转为JPEG
                    rgb_img = img.convert('RGB')
                    output_path = output_path.with_suffix('.jpg')
                    rgb_img.save(output_path, 'JPEG', quality=quality, optimize=True)
            # 其他格式尝试直接保存
            else:
                img.save(output_path, optimize=True)
                
            return {
                'status': 'success',
                'original_path': image_path,
                'output_path': output_path,
                'original_size': Path(image_path).stat().st_size,
                'compressed_size': output_path.stat().st_size
            }
            
        except UnidentifiedImageError:
            return {
                'status': 'error',
                'original_path': image_path,
                'message': f"无法识别的图片格式: {image_path}"
            }
        except Exception as e:
            return {
                'status': 'error',
                'original_path': image_path,
                'message': str(e)
            }

class CompressorApp(ctk.CTk):
    """图片压缩应用UI"""
    
    def __init__(self):
        super().__init__()
        
        # 设置CTk外观模式和颜色主题
        ctk.set_appearance_mode("system")  # 系统模式
        ctk.set_default_color_theme("blue")  # 蓝色主题
        
        self.title("图片压缩工具")
        self.geometry("800x600")
        self.minsize(600, 400)
        
        # 创建图片压缩器实例
        self.compressor = ImageCompressor()
        
        # 加载配置
        self.config = self.load_config()
        
        # 设置输出目录（使用保存的配置或默认）
        output_dir = self.config.get("output_dir", str(Path(os.getcwd()) / "output"))
        self.compressor.set_output_directory(output_dir)
        
        # 设置默认质量（使用保存的配置或默认）
        self.default_quality = self.config.get("quality", 90)
        self.compressor.quality = self.default_quality
        
        # 保存选择的文件
        self.selected_files = []
        
        # 创建UI
        self.create_ui()
        
    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置文件出错: {e}")
        return {}  # 返回空配置
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config = {
                "output_dir": str(self.compressor.output_dir),
                "quality": self.compressor.quality
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"保存配置文件出错: {e}")
    
    def create_ui(self):
        """创建用户界面"""
        # 设置网格权重使组件可调整大小
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        # 顶部标题
        header_frame = ctk.CTkFrame(self)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="图片压缩工具", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=10)
        
        # 控制区域
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        
        # 设置网格
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)
        control_frame.grid_columnconfigure(2, weight=1)
        
        # 选择文件按钮
        select_btn = ctk.CTkButton(
            control_frame, 
            text="选择图片文件", 
            command=self.select_files,
            height=36
        )
        select_btn.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # 质量控制
        quality_frame = ctk.CTkFrame(control_frame)
        quality_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        quality_label = ctk.CTkLabel(quality_frame, text="压缩质量:")
        quality_label.pack(side="left", padx=5)
        
        self.quality_var = tk.IntVar(value=self.compressor.quality)
        quality_slider = ctk.CTkSlider(
            quality_frame, 
            from_=50, 
            to=95, 
            variable=self.quality_var,
            width=100
        )
        quality_slider.pack(side="left", padx=5, fill="x", expand=True)
        
        self.quality_display = ctk.CTkLabel(quality_frame, text=f"{self.quality_var.get()}%")
        self.quality_display.pack(side="left", padx=5)
        
        # 更新显示的质量值
        def update_quality_display(event):
            self.quality_display.configure(text=f"{self.quality_var.get()}%")
        
        quality_slider.bind("<ButtonRelease-1>", update_quality_display)
        
        # 压缩按钮
        compress_btn = ctk.CTkButton(
            control_frame, 
            text="开始压缩", 
            command=self.start_compression,
            height=36,
            fg_color="#0078d4",  # Win11蓝色
            hover_color="#106ebe"
        )
        compress_btn.grid(row=0, column=2, padx=10, pady=10, sticky="ew")
        
        # 信息展示和目录选择区域
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        
        # 使左右两个元素分别靠左和靠右
        info_frame.grid_columnconfigure(0, weight=1)  # 文件数量标签
        info_frame.grid_columnconfigure(1, weight=0)  # 目录选择按钮
        info_frame.grid_columnconfigure(2, weight=1)  # 输出目录标签
        
        # 左侧：文件数量
        self.file_count_label = ctk.CTkLabel(
            info_frame, 
            text="已选择 0 个文件"
        )
        self.file_count_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        # 中间：目录选择按钮
        select_dir_btn = ctk.CTkButton(
            info_frame,
            text="选择输出目录",
            command=self.select_output_directory,
            width=120,
            height=28
        )
        select_dir_btn.grid(row=0, column=1, padx=10, pady=5)
        
        # 右侧：输出目录标签
        self.output_dir_label = ctk.CTkLabel(
            info_frame, 
            text=f"输出目录: {self.compressor.output_dir}"
        )
        self.output_dir_label.grid(row=0, column=2, padx=10, pady=5, sticky="e")
        
        # 日志区域
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        log_label = ctk.CTkLabel(log_frame, text="处理日志:")
        log_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")
        
        self.log_text = ctk.CTkTextbox(log_frame, wrap="word")
        self.log_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        
        # 状态栏
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(status_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=10)
        self.progress_bar.set(0)
        
        self.status_label = ctk.CTkLabel(status_frame, text="准备就绪")
        self.status_label.pack(side="left", padx=10, pady=(0, 10))
    
    def select_output_directory(self):
        """选择输出目录"""
        new_dir = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=self.compressor.output_dir
        )
        
        if new_dir:  # 确保用户选择了目录
            self.compressor.set_output_directory(new_dir)
            self.output_dir_label.configure(text=f"输出目录: {self.compressor.output_dir}")
            self.save_config()  # 保存配置
            self.log(f"输出目录已更改为: {self.compressor.output_dir}")
    
    def select_files(self):
        """选择多个图片文件"""
        filetypes = [
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
            ("JPEG文件", "*.jpg *.jpeg"),
            ("PNG文件", "*.png"),
            ("所有文件", "*.*")
        ]
        
        self.selected_files = list(filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=filetypes
        ))
        
        self.file_count_label.configure(text=f"已选择 {len(self.selected_files)} 个文件")
        
        if self.selected_files:
            self.log("已选择以下文件:")
            for file in self.selected_files[:10]:  # 只显示前10个
                self.log(f"- {Path(file).name}")
            
            if len(self.selected_files) > 10:
                self.log(f"... 共 {len(self.selected_files)} 个文件")
    
    def start_compression(self):
        """开始压缩处理"""
        if not self.selected_files:
            messagebox.showinfo("提示", "请先选择需要压缩的图片文件")
            return
        
        # 获取当前质量设置
        quality = self.quality_var.get()
        self.compressor.quality = quality
        
        # 保存配置（记住当前质量设置）
        self.save_config()
        
        # 清空日志
        self.log_text.delete("1.0", "end")
        self.log(f"开始处理 {len(self.selected_files)} 个文件，压缩质量: {quality}%")
        self.log(f"输出目录: {self.compressor.output_dir}")
        
        # 重置进度条
        self.progress_bar.set(0)
        self.status_label.configure(text="处理中...")
        
        # 在线程中执行压缩任务
        threading.Thread(target=self.compress_task, daemon=True).start()
    
    def compress_task(self):
        """在后台线程中执行压缩任务"""
        total_files = len(self.selected_files)
        processed = 0
        success_count = 0
        error_count = 0
        total_saved = 0
        
        try:
            for img_path in self.selected_files:
                result = self.compressor.compress_image(img_path)
                processed += 1
                progress = processed / total_files
                
                # 更新UI（线程安全方式）
                self.after(0, lambda p=progress: self.progress_bar.set(p))
                self.after(0, lambda c=processed, t=total_files: 
                          self.status_label.configure(text=f"处理中... {c}/{t}"))
                
                if result['status'] == 'success':
                    success_count += 1
                    original_size = result['original_size']
                    compressed_size = result['compressed_size']
                    saved = original_size - compressed_size
                    total_saved += saved if saved > 0 else 0
                    
                    saved_percent = 0 if original_size == 0 else (saved / original_size) * 100
                    
                    self.log(
                        f"✓ {Path(img_path).name} "
                        f"({self.format_size(original_size)} → {self.format_size(compressed_size)}, "
                        f"节省: {saved_percent:.1f}%)"
                    )
                else:
                    error_count += 1
                    self.log(f"✗ {Path(img_path).name}: {result['message']}")
            
            # 完成后更新UI
            self.after(0, lambda: self.progress_bar.set(1))
            self.after(0, lambda: self.status_label.configure(
                text=f"完成! 成功: {success_count}, 失败: {error_count}"
            ))
            
            # 显示汇总信息
            self.log("\n--- 处理完成 ---")
            self.log(f"成功处理: {success_count} 个文件")
            self.log(f"处理失败: {error_count} 个文件")
            self.log(f"共节省空间: {self.format_size(total_saved)}")
            
            # 显示成功对话框
            if success_count > 0:
                self.after(0, lambda: messagebox.showinfo(
                    "处理完成", 
                    f"已成功压缩 {success_count} 个图片，共节省 {self.format_size(total_saved)} 空间。\n"
                    f"输出保存至: {self.compressor.output_dir}"
                ))
            
        except Exception as e:
            self.log(f"处理过程中发生错误: {str(e)}")
            self.after(0, lambda: self.status_label.configure(text="处理出错"))
            self.after(0, lambda: messagebox.showerror("错误", f"处理过程中发生错误:\n{str(e)}"))
    
    def log(self, message):
        """添加消息到日志区域"""
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")  # 滚动到底部
    
    @staticmethod
    def format_size(size_bytes):
        """将字节大小格式化为人类可读形式"""
        if size_bytes < 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB"]
        unit_index = 0
        
        while size_bytes >= 1024 and unit_index < len(units) - 1:
            size_bytes /= 1024
            unit_index += 1
        
        return f"{size_bytes:.1f} {units[unit_index]}"

if __name__ == "__main__":
    try:
        app = CompressorApp()
        app.mainloop()
    except Exception as e:
        messagebox.showerror("启动错误", f"程序启动失败:\n{str(e)}\n\n请确保已安装所需的依赖包。")
        print(f"错误: {str(e)}")
        sys.exit(1)
