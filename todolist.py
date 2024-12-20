import tkinter as tk
from tkinter import messagebox
from tkinter.ttk import Style
import json
import time
import requests

class ToDoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("待办事项")
        self.root.geometry("400x500")
        self.root.configure(bg="#1e1e1e")  # 默认夜间模式
        self.root.attributes("-topmost", True)

        self.tasks = []
        self.task_status = []
        self.mode = "dark"  # 初始为夜间模式

        self.load_data()

        self.style = Style()
        self.style.theme_use('clam')
        self.update_styles()

        # 设置顶部区域背景色
        self.title_bar = tk.Frame(self.root, bg="#333" if self.mode == "dark" else "#ddd")
        self.title_bar.pack(fill="x")

        self.title_label = tk.Label(self.title_bar, text="待办事项", font=("Arial", 14, "bold"), fg="#fff" if self.mode == "dark" else "#000", bg=self.title_bar.cget("bg"))
        self.title_label.pack(pady=5)

        self.task_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.task_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.task_frame, bg="#1e1e1e", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.task_frame, orient="vertical", command=self.canvas.yview)
        self.task_listbox = tk.Frame(self.canvas, bg="#1e1e1e")

        self.task_listbox.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.task_listbox, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.entry_task = tk.Entry(self.root, width=40, bg="#333", fg="#fff", insertbackground="#fff",
                                   highlightbackground="#555", highlightcolor="#777")
        self.entry_task.pack(pady=5)

        self.button_add = tk.Button(self.root, text="添加任务", width=20, command=self.add_task, bg="#007acc", fg="#fff",
                                     activebackground="#005f99", relief="flat")
        self.button_add.pack(pady=5)

        self.button_delete = tk.Button(self.root, text="删除任务", width=20, command=self.delete_task, bg="#007acc", fg="#fff",
                                        activebackground="#005f99", relief="flat")
        self.button_delete.pack(pady=5)

        self.divider = tk.Label(self.root, text="-" * 50, bg="#1e1e1e", fg="#555")
        self.divider.pack(pady=5, fill="x")  # 调整分割线为全宽

        self.time_frame = tk.Frame(self.root, bg="#1e1e1e")
        self.time_frame.pack(pady=5, fill="x")

        self.time_label = tk.Label(self.time_frame, text="", font=("Arial", 12), bg="#1e1e1e", fg="#fff")
        self.time_label.pack(side="left", padx=10)

        self.weather_label = tk.Label(self.time_frame, text="加载天气...", font=("Arial", 12), bg="#1e1e1e", fg="#fff")
        self.weather_label.pack(side="right", padx=10)

        self.mode_button = tk.Button(self.root, text="切换为白天模式", command=self.toggle_mode, bg="#007acc", fg="#fff",
                                      activebackground="#005f99", relief="flat")
        self.mode_button.pack(pady=10)

        self.update_time()
        self.update_weather()
        self.update_task_listbox()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def add_task(self):
        task = self.entry_task.get().strip()
        if task:
            self.tasks.append(task)
            self.task_status.append(False)
            self.entry_task.delete(0, tk.END)
            self.update_task_listbox()
            self.save_data()
        else:
            messagebox.showwarning("输入无效", "请输入有效的任务内容")

    def delete_task(self):
        selected_indices = [i for i, status in enumerate(self.task_status) if status]
        for index in reversed(selected_indices):
            del self.tasks[index]
            del self.task_status[index]
        self.update_task_listbox()
        self.save_data()

    def toggle_task_status(self, index):
        self.task_status[index] = not self.task_status[index]
        self.update_task_listbox()
        self.save_data()

    def update_task_listbox(self):
        for widget in self.task_listbox.winfo_children():
            widget.destroy()

        for i, task in enumerate(self.tasks):
            frame = tk.Frame(self.task_listbox, bg="#1e1e1e" if self.mode == "dark" else "#f0f0f0")
            frame.pack(fill="x", pady=2)

            complete_button = tk.Checkbutton(
                frame, text=f"{i+1}.", command=lambda i=i: self.toggle_task_status(i), bg=frame.cget("bg"),
                fg="#fff" if self.mode == "dark" else "#000", activebackground=frame.cget("bg"))
            complete_button.pack(side="left")

            if self.task_status[i]:
                complete_button.select()

            task_label = tk.Label(frame, text=task, anchor="w", justify="left", wraplength=300,
                                   bg=frame.cget("bg"), fg="#aaa" if self.task_status[i] else ("#fff" if self.mode == "dark" else "#000"))
            task_label.pack(side="left", fill="x", expand=True)

            if self.task_status[i]:
                task_label.config(font=("Arial", 10, "overstrike"))

    def update_time(self):
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)

    def update_weather(self):
        try:
            api_url = "http://api.weatherapi.com/v1/current.json"
            params = {
                "key": "your_api_key",
                "q": "Beijing",
                "lang": "zh"
            }
            response = requests.get(api_url, params=params, timeout=5)
            data = response.json()
            location = data["location"]["name"]
            temp_c = data["current"]["temp_c"]
            condition = data["current"]["condition"]["text"]
            self.weather_label.config(text=f"{location}: {temp_c}°C, {condition}")
        except Exception:
            self.weather_label.config(text="天气加载失败")
        self.root.after(60000, self.update_weather)

    def save_data(self):
        data = {"tasks": self.tasks, "task_status": self.task_status}
        with open("tasks.json", "w") as f:
            json.dump(data, f)

    def load_data(self):
        try:
            with open("tasks.json", "r") as f:
                data = json.load(f)
                self.tasks = data.get("tasks", [])
                self.task_status = data.get("task_status", [])
        except FileNotFoundError:
            self.tasks = []
            self.task_status = []

    def toggle_mode(self):
        if self.mode == "dark":
            self.mode = "light"
            self.root.configure(bg="#f0f0f0")
            self.title_bar.configure(bg="#ddd")
            self.title_label.configure(bg="#ddd", fg="#000")
            self.update_styles()
            self.mode_button.config(text="切换为夜间模式")
        else:
            self.mode = "dark"
            self.root.configure(bg="#1e1e1e")
            self.title_bar.configure(bg="#333")
            self.title_label.configure(bg="#333", fg="#fff")
            self.update_styles()
            self.mode_button.config(text="切换为白天模式")
        self.update_task_listbox()

    def update_styles(self):
        if self.mode == "dark":
            self.style.configure("TButton", background="#007acc", foreground="#fff", relief="flat")
        else:
            self.style.configure("TButton", background="#ddd", foreground="#000", relief="flat")


if __name__ == "__main__":
    root = tk.Tk()
    app = ToDoApp(root)
    root.mainloop()
