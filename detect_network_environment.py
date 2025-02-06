import ctypes
import os
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QRadioButton, \
    QTextEdit, QButtonGroup, QProgressBar
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from scapy.layers.inet import IP, ICMP
from scapy.sendrecv import sr1
from PyQt5.QtGui import QTextCursor



import time


class NetworkTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("网络环境测试工具")
        self.setGeometry(100, 100, 600, 400)

        # 初始化布局
        self.central_widget = QWidget()
        self.layout = QVBoxLayout()

        # 产品版本选择
        self.label = QLabel("请选择产品版本：")
        self.layout.addWidget(self.label)

        self.button_group = QButtonGroup()
        self.radio_china = QRadioButton("中国大陆")
        self.radio_overseas = QRadioButton("海外")
        self.button_group.addButton(self.radio_china)
        self.button_group.addButton(self.radio_overseas)
        self.layout.addWidget(self.radio_china)
        self.layout.addWidget(self.radio_overseas)

        # 测试按钮
        self.test_button = QPushButton("开始测试")
        self.test_button.clicked.connect(self.start_test)
        self.layout.addWidget(self.test_button)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.progress_bar)

        # 测试结果显示
        self.result_label = QLabel("测试结果：")
        self.layout.addWidget(self.result_label)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.layout.addWidget(self.result_text)

        # 设置中心窗口
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)

    def start_test(self):
        if self.radio_china.isChecked():
            region = "中国大陆"
        elif self.radio_overseas.isChecked():
            region = "海外"
        else:
            self.result_text.setText("请先选择产品版本！")
            return

        # 启动网络测试线程
        self.thread = NetworkTestThread(region)
        self.thread.progress_updated.connect(self.progress_bar.setValue)
        self.thread.test_completed.connect(self.display_results)
        self.thread.start()

    def display_results(self, results):
        # 分割结果为每行
        lines = results.split("\n")

        # 提取关键字段并格式化
        formatted_lines = []
        for line in lines:
            if "Ping" in line:
                # 按照关键字段对齐
                formatted_line = line.replace("Ping", "<b>Ping</b>").replace("平均延时:", " | 平均延时:").replace(
                    "最大延时:", " | 最大延时:")
                formatted_lines.append(formatted_line)
            elif "测试域名" in line or "备用域名" in line:
                formatted_lines.append(f"<b>{line}</b>")
            elif "评估结果" in line:
                # 对评估结果单独设置颜色
                if "良好" in line:
                    color = "green"
                elif "异常" in line:
                    color = "red"
                else:
                    color = "orange"
                formatted_lines.append(f'<font color="{color}"><b>{line}</b></font>')
            else:
                formatted_lines.append(line)

        # 使用 HTML 换行符合并内容
        formatted_results = "<br>".join(formatted_lines)
        self.result_text.setHtml(formatted_results)
        # 滚动到最底部
        self.result_text.moveCursor(QTextCursor.End)



class NetworkTestThread(QThread):
    progress_updated = pyqtSignal(int)
    test_completed = pyqtSignal(str)

    def __init__(self, region):
        super().__init__()
        self.region = region
        self.count = 100

    def ping_host(self, host, count):
        """使用 scapy 进行 Ping 测试并统计丢包率和延时"""
        loss_rate = 100
        avg_time = -1
        max_time = -1
        success_count = 0
        result = ""

        for _ in range(count):
            start_time = time.time()
            packet = IP(dst=host) / ICMP()
            response = sr1(packet, timeout=4, verbose=False)

            if response:
                success_count += 1
                round_trip_time = (time.time() - start_time) * 1000  # 毫秒
                avg_time += round_trip_time
                if round_trip_time > max_time:
                    max_time = round_trip_time
            else:
                result += f"Ping {host} 请求超时\n"

        # 计算丢包率和平均延时
        if success_count > 0:
            loss_rate = 100 - (success_count / count) * 100
            avg_time /= success_count
            result += f"Ping {host} 成功，平均延时: {avg_time:.2f}ms，最大延时: {max_time:.2f}ms\n"
        else:
            result += f"Ping {host} 失败，未收到回应\n"

        return loss_rate, avg_time, max_time, result

    def run(self):
        results = []

        if self.region == "中国大陆":
            hosts = ["cloud-service.austinelec.com", "www.baidu.com"]
        else:
            hosts = ["cloud-service-us.austinelec.com", "8.8.8.8"]

        total_pings = len(hosts) * self.count  # 假设每个主机 ping 100 次
        completed_pings = 0
        stats = {}

        for host in hosts:
            total_loss = 0
            total_time = 0
            max_time = 0
            for i in range(self.count):  # 每个主机 ping 100 次
                loss, avg, max_t, result = self.ping_host(host, self.count)
                total_loss += loss
                if avg > 0:
                    total_time += avg
                if max_t > max_time:
                    max_time = max_t
                results.append(result)
                completed_pings += 1
                progress = int((completed_pings / total_pings) * 100)
                self.progress_updated.emit(progress)

            avg_loss = total_loss / 100  # 计算平均丢包率
            avg_time = total_time / 100 if total_time > 0 else -1
            stats[host] = {
                "loss": avg_loss,
                "avg_time": avg_time,
                "max_time": max_time
            }

        # 评估结果
        cloud_service = "cloud-service.austinelec.com" if self.region == "中国大陆" else "cloud-service-us.austinelec.com"
        backup_host = "www.baidu.com" if self.region == "中国大陆" else "8.8.8.8"

        cloud_service_stats = stats.get(cloud_service, {"loss": 100, "avg_time": -1, "max_time": -1})
        backup_host_stats = stats.get(backup_host, {"loss": 100, "avg_time": -1, "max_time": -1})

        if cloud_service_stats["loss"] > 50 and backup_host_stats["loss"] <= 5:
            final_result = "网络环境正常，但与产品服务通信异常。"
        elif cloud_service_stats["loss"] > 50 and backup_host_stats["loss"] >= 20:
            final_result = "网络环境不稳定。"
        elif cloud_service_stats["loss"] == 100 and backup_host_stats["loss"] == 100:
            final_result = "无网络链接，请检查网络。"
        elif cloud_service_stats["loss"] > 10:
            final_result = "当前网络与服务器通信不稳，产品使用存在频繁掉线、不受控等问题。"
        elif cloud_service_stats["loss"] > 5:
            final_result = "检测到与服务器之间存在较大波动。"
        elif cloud_service_stats["loss"] > 0:
            final_result = "检测到与服务器之间存在微弱波动。"
        else:
            final_result = "网络环境良好。"

        results.append(
            f"\n测试域名: {cloud_service}\n丢包率: {cloud_service_stats['loss']}%\n平均延时: {cloud_service_stats['avg_time']}ms\n最大延时: {cloud_service_stats['max_time']}ms")
        results.append(
            f"备用域名: {backup_host}\n丢包率: {backup_host_stats['loss']}%\n平均延时: {backup_host_stats['avg_time']}ms\n最大延时: {backup_host_stats['max_time']}ms")
        results.append(f"\n评估结果：{final_result}")
        self.test_completed.emit("\n".join(results))



if __name__ == "__main__":
    if ctypes.windll.shell32.IsUserAnAdmin():
        app = QApplication(sys.argv)
        window = NetworkTester()
        window.show()
        sys.exit(app.exec_())
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
