import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk


class ImageCropTool:
    def __init__(self, master):
        self.master = master
        self.master.title("图片裁剪工具")
        self.master.geometry("800x600")  # 设置默认窗口尺寸

        self.image = None  # 原始图片对象
        self.cropped_image = None  # 裁剪后的图片对象

        # 主界面分为左侧图片显示区和右侧控制面板
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧：图片显示区域
        self.canvas = tk.Canvas(self.main_frame, bg="gray")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 右侧：控制面板
        self.control_panel = ttk.Frame(self.main_frame, width=200)
        self.control_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # 加载图片按钮
        self.btn_load = ttk.Button(self.control_panel, text="加载图片", command=self.load_image)
        self.btn_load.pack(padx=10, pady=10, fill=tk.X)

        # 裁剪参数输入区（使用LabelFrame分组）
        param_frame = ttk.LabelFrame(self.control_panel, text="裁剪参数")
        param_frame.pack(padx=10, pady=10, fill=tk.X)

        # 使用StringVar管理输入框数据，方便后续取值
        self.var_x = tk.StringVar()
        self.var_y = tk.StringVar()
        self.var_w = tk.StringVar()
        self.var_h = tk.StringVar()

        # 起点 X
        ttk.Label(param_frame, text="起点 X:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_x = ttk.Entry(param_frame, textvariable=self.var_x, width=10)
        self.entry_x.grid(row=0, column=1, padx=5, pady=5)

        # 起点 Y
        ttk.Label(param_frame, text="起点 Y:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_y = ttk.Entry(param_frame, textvariable=self.var_y, width=10)
        self.entry_y.grid(row=1, column=1, padx=5, pady=5)

        # 裁剪宽度
        ttk.Label(param_frame, text="宽度:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_w = ttk.Entry(param_frame, textvariable=self.var_w, width=10)
        self.entry_w.grid(row=2, column=1, padx=5, pady=5)

        # 裁剪高度
        ttk.Label(param_frame, text="高度:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.entry_h = ttk.Entry(param_frame, textvariable=self.var_h, width=10)
        self.entry_h.grid(row=3, column=1, padx=5, pady=5)

        # 裁剪按钮
        self.btn_crop = ttk.Button(self.control_panel, text="裁剪", command=self.crop_image)
        self.btn_crop.pack(padx=10, pady=10, fill=tk.X)

        # 保存图片按钮
        self.btn_save = ttk.Button(self.control_panel, text="保存图片", command=self.save_image)
        self.btn_save.pack(padx=10, pady=10, fill=tk.X)

        # 为输入框绑定回车键触发裁剪
        self.entry_h.bind("<Return>", lambda event: self.crop_image())

        # 绑定窗口大小变化事件，实现图片自适应居中显示
        self.master.bind("<Configure>", self.on_resize)

    def load_image(self):
        """加载图片文件"""
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if file_path:
            try:
                self.image = Image.open(file_path)
                # 加载图片后，初始化裁剪参数为全图
                self.var_x.set("0")
                self.var_y.set("0")
                self.var_w.set(str(self.image.width))
                self.var_h.set(str(self.image.height))
                self.cropped_image = None  # 清空之前的裁剪结果
                self.display_image(self.image)
            except Exception as e:
                messagebox.showerror("错误", f"加载图片失败: {e}")

    def display_image(self, img):
        """在Canvas中显示图片，并自动居中显示，支持自适应缩放"""
        self.canvas.delete("all")
        # 将 PIL 图片转换为 Tkinter 可用的 PhotoImage
        self.tk_img = ImageTk.PhotoImage(img)
        # 确保Canvas尺寸已更新
        self.canvas.update()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        img_width = self.tk_img.width()
        img_height = self.tk_img.height()

        # 计算缩放比例（仅在图片尺寸大于canvas时缩放）
        scale = min(canvas_width / img_width, canvas_height / img_height, 1)
        if scale < 1:
            new_size = (int(img_width * scale), int(img_height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            self.tk_img = ImageTk.PhotoImage(img)
            img_width, img_height = new_size

        # 计算居中显示的坐标
        x = (canvas_width - img_width) // 2
        y = (canvas_height - img_height) // 2
        self.canvas.create_image(x, y, anchor="nw", image=self.tk_img)
        # 保存当前显示信息，便于后续扩展（例如绘制裁剪框）
        self.display_info = {"x": x, "y": y, "scale": scale}

    def crop_image(self):
        """根据输入的起点和宽高裁剪图片"""
        if self.image is None:
            messagebox.showwarning("警告", "请先加载图片")
            return

        # 检查输入是否为空并转换为整数
        try:
            x = int(self.var_x.get())
            y = int(self.var_y.get())
            w = int(self.var_w.get())
            h = int(self.var_h.get())
        except ValueError:
            messagebox.showerror("错误", "请输入正确的数字")
            return

        # 检查坐标和尺寸的合法性
        if x < 0 or y < 0 or w <= 0 or h <= 0:
            messagebox.showwarning("警告", "坐标和尺寸必须为正整数")
            return

        # 检查裁剪区域是否超出原图范围
        if x + w > self.image.width or y + h > self.image.height:
            messagebox.showwarning("警告", "裁剪区域超出图片范围")
            return

        try:
            # 裁剪原图
            box = (x, y, x + w, y + h)
            self.cropped_image = self.image.crop(box)
            self.display_image(self.cropped_image)
        except Exception as e:
            messagebox.showerror("错误", f"裁剪失败: {e}")

    def save_image(self):
        """保存裁剪后的图片"""
        if self.cropped_image is None:
            messagebox.showwarning("警告", "请先裁剪图片")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg"), ("BMP", "*.bmp"), ("GIF", "*.gif")],
            title="保存裁剪后的图片"
        )
        if file_path:
            try:
                self.cropped_image.save(file_path)
                messagebox.showinfo("提示", "图片已保存")
            except Exception as e:
                messagebox.showerror("错误", f"保存图片失败: {e}")

    def on_resize(self, event):
        """窗口尺寸变化时重新显示图片，保持居中"""
        if self.image:
            # 如果有裁剪结果则显示裁剪结果，否则显示原图
            img = self.cropped_image if self.cropped_image else self.image
            self.display_image(img)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCropTool(root)
    root.mainloop()
