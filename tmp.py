import tkinter as tk
from tkinter import filedialog, messagebox
import vlc
import threading
import time

class VideoPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("多视频播放器")
        self.root.geometry("400x300")

        # 存储选择的视频路径
        self.video_paths = []
        # 存储 VLC 播放实例
        self.players = []

        # GUI 组件
        self.label = tk.Label(root, text="选择多个视频文件后点击开始播放")
        self.label.pack(pady=10)

        self.select_button = tk.Button(root, text="选择视频", command=self.select_videos)
        self.select_button.pack(pady=5)

        self.video_listbox = tk.Listbox(root, height=10, width=50)
        self.video_listbox.pack(pady=10)

        self.play_button = tk.Button(root, text="开始播放", command=self.start_playback, state="disabled")
        self.play_button.pack(pady=5)

    def select_videos(self):
        # 打开文件对话框，支持多选
        files = filedialog.askopenfilenames(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mkv *.mov *.wmv")]
        )
        if files:
            self.video_paths = list(files)
            self.video_listbox.delete(0, tk.END)  # 清空列表
            for path in self.video_paths:
                self.video_listbox.insert(tk.END, path.split('/')[-1])  # 只显示文件名
            self.play_button.config(state="normal")  # 启用播放按钮
        else:
            messagebox.showwarning("警告", "未选择任何视频文件！")

    def play_video(self, path):
        # 为每个视频创建一个 VLC 实例并播放
        instance = vlc.Instance()
        player = instance.media_player_new()
        media = instance.media_new(path)
        player.set_media(media)
        player.play()
        self.players.append(player)  # 保存播放器实例

        # 等待播放结束（可选）
        while player.is_playing():
            time.sleep(1)

    def start_playback(self):
        if not self.video_paths:
            messagebox.showerror("错误", "请先选择视频文件！")
            return

        # 清空之前的播放器实例
        self.players = []

        # 为每个视频启动一个线程播放
        for path in self.video_paths:
            thread = threading.Thread(target=self.play_video, args=(path,))
            thread.daemon = True  # 设置为守护线程，随主程序关闭
            thread.start()

        messagebox.showinfo("提示", f"正在播放 {len(self.video_paths)} 个视频")

    def on_closing(self):
        # 关闭时停止所有播放
        for player in self.players:
            player.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoPlayerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)  # 处理窗口关闭
    root.mainloop()