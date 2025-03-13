# -*- coding: utf-8 -*-
import serial.tools.list_ports
import serial
import time
import re
from colorama import init, Fore, Back, Style

# 初始化colorama，用于彩色输出
init(autoreset=True)


class ScreenDetector:
    def __init__(self):
        """初始化屏幕检测器"""
        self.ser = None
        self.connected = False
        self.baudrate = 115200
        self.timeout = 2  # 串口读取超时时间
        self.current_port = None
        print(Fore.CYAN + "欢迎使用屏幕ID和版本号检测工具")
        print(Fore.CYAN + "=" * 50)
        """设置检测选项"""
        self.check_screenId = False
        self.check_version = True
        self.check_location = True
        self.has_disconnected = False

    def list_serial_ports(self):
        """列出所有可用的串口设备"""
        ports = serial.tools.list_ports.comports()
        if not ports:
            print(Fore.RED + "未检测到任何串口设备")
            return []

        print(Fore.YELLOW + "发现以下串口设备:")
        for i, port in enumerate(ports):
            print(f"{i + 1}. {port.device} - {port.description}")

        return ports

    def connect_to_port(self, port):
        """连接到指定串口"""
        try:
            # 如果已有连接，先关闭
            if self.ser and self.ser.is_open:
                self.ser.close()
                time.sleep(0.5)  # 等待端口释放

            # 尝试新连接
            self.ser = serial.Serial(port, self.baudrate, timeout=self.timeout)
            self.connected = True
            self.current_port = port
            print(Fore.GREEN + f"成功连接到串口: {port}")
            return True
        except serial.SerialException as e:
            print(Fore.RED + f"连接串口 {port} 失败: {str(e)}")
            self.connected = False
            return False

    def check_device_booting(self):
        """检查设备是否处于启动过程中"""
        if not self.connected or not self.ser:
            return False

        try:
            # 读取当前缓冲区内容但不清空
            boot_markers = ["Version:", "Auto-Negotiation", "[WDT]", "SPINAND:", "MMC:", "I2C:"]

            # 不发送任何命令，只读取当前输出
            start_time = time.time()
            buffer = ""

            # 最多读取2秒
            while (time.time() - start_time) < 2:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
                    buffer += data

                # 一旦检测到任何启动标记，立即返回True
                for marker in boot_markers:
                    if marker in buffer:
                        print(Fore.YELLOW + f"检测到设备启动标记: {marker}，等待设备启动...")
                        return True

                time.sleep(0.1)

            return False
        except Exception as e:
            print(Fore.RED + f"检查设备启动状态时出错: {str(e)}")
            return False

    def judge_uboot_and_exit(self):
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        prompt = 'SigmaStar'
        pattern = re.compile(prompt)
        try:
            self.ser.write(b'\r\n')
            time.sleep(0.5)
            max_attempts = 3
            for _ in range(max_attempts):
                # 读取一行数据
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # 检查是否匹配 U-Boot 提示符
                    if pattern.search(line):
                        # 退出 U-Boot 界面
                        self.ser.write(b'reset\r\n')
                        time.sleep(7)
                        return True
                # 如果没有数据，发送回车符重试
                self.ser.write(b'\r\n')
                time.sleep(0.1)

            return False
        except Exception:
            return False

    def send_command(self, command, wait_time=0.3):
        """发送命令到串口并获取响应"""
        if not self.connected or not self.ser:
            print(Fore.RED + "无法发送命令: 未连接到设备，请检查设备是否连接")
            self.judge_uboot_and_exit()
            return None

        try:
            # 先检查设备是否连接
            if not self.check_device_connection():
                print(Fore.RED + "设备已断开，无法发送命令")
                self.has_disconnected = True
                return None
            # 检查设备是否处于启动过程
            if self.has_disconnected:
                if self.check_device_booting():
                    print(Fore.YELLOW + "检测到设备正在启动，等待5秒...")
                    time.sleep(5)  # 等待设备启动完成
                    print(Fore.GREEN + "继续执行操作")

            # 完全清空缓冲区，等待一段时间确保当前所有输出都被读取并丢弃
            # time.sleep(0.3)  # 等待可能的输出
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            time.sleep(0.2)  # 再次等待确保缓冲区真的空了

            # 发送命令并加上回车
            cmd = command + '\r\n'
            cmdlen = self.ser.write(cmd.encode('utf-8'))

            # 保证命令发送成功
            if cmdlen != len(cmd):
                print(Fore.RED + "串口接触不良，请检查后重新插入，若仍然无法读取到id，请重启设备")
                return None

            # 等待命令执行
            time.sleep(wait_time)

            # 读取响应，使用更长的等待时间确保捕获完整响应
            response = b''
            start_time = time.time()
            max_wait_time = 2.0  # 等待最多2秒
            while (time.time() - start_time) < max_wait_time:
                try:
                    if self.ser.in_waiting > 0:
                        chunk = self.ser.read(self.ser.in_waiting)
                        response += chunk
                        if 'SigmaStar' in response.decode('utf-8', errors='ignore'):
                            self.ser.write(b'reset\r\n')
                            time.sleep(7)
                        # 如果已经找到了我们要的信息，可以提前结束
                        if command.startswith("cat "):
                            decoded = response.decode('utf-8', errors='replace')
                            if command.endswith("screenId.ini") and "deviceId=" in decoded:
                                break
                            if command.endswith("version.ini") and "version=" in decoded:
                                break
                            if command.endswith("local.ini") and "local=" in decoded:
                                break
                except Exception as e:
                    print(Fore.RED + f"读取响应时出错: {str(e)}")
                    # 设备可能已断开
                    self.connected = False
                    return None

                time.sleep(0.1)  # 短暂等待后再次检查

            if response:
                decoded = response.decode('utf-8', errors='replace')
                return decoded
            else:
                print(Fore.RED + "设备串口接触不良，请检查后重新插入，若重新插入还不行请重启设备")
                self.judge_uboot_and_exit()
                return None
        except Exception as e:
            print(Fore.RED + f"发送命令出错: {str(e)}")
            # 设备可能已断开
            self.connected = False
            return None

    def check_device_ready(self):
        """检查设备是否准备好接收命令"""
        if not self.connected:
            print(Fore.RED + "设备未连接")
            return False

        # 多次尝试发送回车，检查是否得到响应
        for attempt in range(5):
            response = self.send_command("", wait_time=0.5)

            if response:
                if '/' in response or '#' in response:
                    print(Fore.GREEN + "设备已就绪")
                    return True

            # 如果没有响应或没有预期的提示符，尝试不同的命令
            if attempt == 2:
                resp = self.send_command("echo hello", wait_time=0.5)
                if resp and 'hello' in resp:
                    return True

        # 尝试中断可能正在运行的程序
        self.ser.write(b'\x03')
        time.sleep(1)
        response = self.send_command("", wait_time=0.5)

        if response and ('/' in response or '#' in response):
            print(Fore.GREEN + "设备在发送中断后就绪")
            return True

        print(Fore.RED + "设备未就绪，无法通信")
        return False

    def check_file_exists(self, filepath):
        """检查文件是否存在"""
        response = self.send_command(f"ls -la {filepath}")
        if response and "No such file or directory" not in response:
            return True
        return False

    def check_device_connection(self):
        """检查设备是否仍然连接"""
        if not self.ser:
            return False

        try:
            # 尝试发送一个简单命令来检查连接状态
            self.ser.write(b'\r\n')
            time.sleep(0.2)
            return self.ser.is_open
        except Exception as e:
            print(Fore.RED + f"设备连接检查失败: {str(e)}")
            # 如果发生异常，标记为未连接
            self.connected = False
            return False

    def wait_for_device_reconnect(self, port):
        """等待设备重新连接，提供动态进度提示"""
        print(Fore.RED + "未检测到串口设备，正在等待设备连接...")

        # 确保关闭和释放之前的连接
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
            self.ser = None  # 重要：完全释放之前的连接

        self.connected = False

        dots_count = 0
        scan_interval = 0.5  # 每0.5秒扫描一次设备

        while True:
            # 动态显示检测中...
            dots = "." * (dots_count % 4 + 1)
            spaces = " " * (3 - dots_count % 4)
            print(f"\r{Fore.YELLOW}检测中{dots}{spaces}", end="")
            dots_count += 1

            # 主动扫描所有串口设备
            available_ports = list(serial.tools.list_ports.comports())

            if available_ports:
                # 优先尝试连接到原端口
                original_port_available = False
                for port_info in available_ports:
                    if port_info.device == port:
                        original_port_available = True
                        break

                try:
                    if original_port_available:
                        # 原端口可用，尝试连接
                        self.ser = serial.Serial(port, self.baudrate, timeout=self.timeout)
                        self.connected = True
                        self.current_port = port
                        print(f"\r{Fore.GREEN}成功重新连接到原串口: {port}" + " " * 30)

                        # 检查设备是否处于启动过程
                        if self.check_device_booting():
                            print(Fore.YELLOW + "检测到设备正在启动，等待5秒...")
                            time.sleep(5)  # 等待设备启动完成

                        return True
                    else:
                        # 原端口不可用，连接到第一个可用端口
                        new_port = available_ports[0].device
                        self.ser = serial.Serial(new_port, self.baudrate, timeout=self.timeout)
                        self.connected = True
                        self.current_port = new_port
                        print(f"\r{Fore.GREEN}连接到新串口: {new_port}" + " " * 30)

                        # 检查设备是否处于启动过程
                        if self.check_device_booting():
                            print(Fore.YELLOW + "检测到设备正在启动，等待5秒...")
                            time.sleep(5)  # 等待设备启动完成

                        return True
                except Exception as e:
                    print(f"\r{Fore.RED}尝试连接失败: {str(e)}" + " " * 30)
                    time.sleep(0.5)  # 短暂等待后继续

            time.sleep(scan_interval)

    def check_device(self):
        """检查当前连接的设备，读取屏幕ID和版本号"""
        if not self.connected:
            print(Fore.RED + "未连接到设备")
            # 尝试等待设备连接
            if not self.wait_for_device_reconnect(self.current_port):
                return None, None, None

        # 等待用户确认继续
        input(Fore.RED + "按回车键开始读取设备信息...")
        print(Fore.CYAN + "正在读取设备信息，请耐心等待...")
        # 在读取前再次检查设备连接状态
        if not self.check_device_connection():
            print(Fore.RED + "设备已断开，等待重新连接...")
            # 等待设备重新连接
            if not self.wait_for_device_reconnect(self.current_port):
                return None, None, None
            print(Fore.GREEN + "设备已重新连接，继续读取设备信息...")

        # 尝试检查文件是否存在
        screen_id_path = "/customer/screenId.ini"
        version_path = "/software/version.ini"
        location_path = "/software/local.ini"

        # start_time = time.time()

        # # 验证文件路径
        # if not self.check_file_exists(screen_id_path):
        #     # 尝试其他可能的路径
        #     for path in ["/data/customer/screenId.ini", "/etc/screenId.ini"]:
        #         if self.check_file_exists(path):
        #             screen_id_path = path
        #             break
        #
        # if not self.check_file_exists(version_path):
        #     # 尝试其他可能的路径
        #     for path in ["/software/version.ini", "/etc/version.ini"]:
        #         if self.check_file_exists(path):
        #             version_path = path
        #             break
        #
        # end_time = time.time()
        # print(f"检查文件耗时: {end_time - start_time: .2f} 秒")

        # 持续尝试读取，直到成功或用户中断
        max_attempts = 50  # 最大尝试次数
        attempt = 0
        screen_id = None if self.check_screenId else True
        version = None if self.check_version else True
        location = None if self.check_location else True

        while (screen_id is None or version is None or location is None) and attempt < max_attempts:
            attempt += 1

            # 获取屏幕ID
            if screen_id is None:
                screen_id = self.get_screen_id_from_path(screen_id_path)

            # 获取版本号
            if version is None:
                version = self.get_version_from_path(version_path)

            # 获取位置
            if location is None:
                location = self.get_location_from_path(location_path)

            # 判断是否已获取到信息
            if screen_id is not None and version is not None and location is not None:
                print(Fore.GREEN + "设备信息读取完成!")
                break
            # 继续尝试
            if attempt < max_attempts:
                time.sleep(0.5)  # 等待1秒再次尝试

        # 处理无法获取信息的情况
        if screen_id is None:
            print(Fore.RED + "无法获取屏幕ID，已达到最大尝试次数")
        if version is None:
            print(Fore.RED + "无法获取版本号，已达到最大尝试次数")
        if location is None:
            print(Fore.RED + "无法获取位置，已达到最大尝试次数")
        # 返回结果，注意空字符串("")表示值为空但配置项存在
        return screen_id, version, location

    def get_screen_id_from_path(self, path):
        """从指定路径获取屏幕ID"""
        try:
            response = self.send_command(f"cat {path} ")
            if not response:
                return None
            # 首先检查是否包含deviceId配置项，即使值为空
            empty_match = re.search(r'deviceId\s*=\s*(\S*)', response)
            if empty_match:
                screen_id = empty_match.group(1)
                if not screen_id:  # 如果值为空
                    print(Fore.YELLOW + "屏幕ID存在但为空!")
                    print("屏幕ID: [空]")
                    return ""  # 返回空字符串表示ID存在但为空
                else:
                    print(f"屏幕ID: {screen_id}")
                    return screen_id

            # 未找到deviceId配置项
            print(Fore.RED + "未找到屏幕ID配置项")
            return None
        except Exception as e:
            print(Fore.RED + f"从路径 {path} 获取屏幕ID时出错: {str(e)}")
            return None

    def get_version_from_path(self, path):
        """从指定路径获取版本号"""
        try:
            response = self.send_command(f"cat {path}")
            if not response:
                return None
            # 首先检查是否包含version配置项，即使值为空
            empty_match = re.search(r'version\s*=\s*(\S*)', response)
            if 'SigmaStar' in response:
                self.ser.write(b'reset\r\n')
                time.sleep(7)
                return None
            if empty_match:
                version = empty_match.group(1)
                if not version:  # 如果值为空
                    print(Fore.YELLOW + "版本号存在但为空!")
                    print("软件版本: [空]")
                    return ""  # 返回空字符串表示版本号存在但为空
                else:
                    print(f"软件版本号: {version}")
                    return version
            return None
        except Exception as e:
            print(Fore.RED + f"从路径 {path} 获取版本号时出错: {str(e)}")
            return None

    def get_location_from_path(self, path):
        try:
            response = self.send_command(f"cat {path}")
            if not response:
                return None

            # 首先检查是否包含location配置项，即使值为空
            empty_match = re.search(r'local\s*=\s*(\S*)', response)
            if empty_match:
                location = empty_match.group(1)
                if not location:  # 如果值为空
                    print(Fore.YELLOW + "位置存在但为空!")
                    print("版本: [空]")
                    return ""  # 返回空字符串表示位置存在但为空
                else:
                    if location == '2':
                        location = '海外版本'
                    elif location == '1':
                        location = '国内版本'
                    else:
                        location = '未知'
                    print(f"版本: {location}")
                    return location
            return None
        except Exception as e:
            print(Fore.RED + f"未能获取到设备的海内外版本配置: {str(e)}")
            return None

    def run(self):
        """运行主循环"""
        try:
            while True:
                print(Fore.CYAN + "\n正在检测串口设备...\n")

                # 循环直到找到可用设备
                device_found = False
                dots_count = 0

                while not device_found:
                    ports = self.list_serial_ports()

                    if ports:
                        device_found = True
                    else:
                        # 动态显示检测中... (修复了显示ports的错误)
                        dots = "." * (dots_count % 4 + 1)
                        spaces = " " * (3 - dots_count % 4)
                        print(f"\r{Fore.YELLOW}检测中{dots}{spaces}", end="")
                        dots_count += 1
                        time.sleep(0.5)

                print()  # 换行

                # 让用户选择串口
                selection = -1
                if len(ports) == 1:
                    selection = 1
                else:
                    while selection < 1 or selection > len(ports):
                        try:
                            selection = int(input(Fore.YELLOW + "请选择串口 (输入编号): "))
                            if selection < 1 or selection > len(ports):
                                print(Fore.RED + "无效的选择，请重新输入")
                        except ValueError:
                            print(Fore.RED + "请输入有效的数字")

                # 连接到选择的串口
                selected_port = ports[selection - 1].device
                if self.connect_to_port(selected_port):
                    print(Fore.GREEN + "设备连接成功!")

                    continue_checking = True
                    while continue_checking:
                        # 在每次读取前检查设备连接状态
                        if not self.check_device_connection():
                            print(Fore.RED + "设备已断开，等待重新连接...")
                            # 等待设备重新连接
                            if self.wait_for_device_reconnect(selected_port):
                                print(Fore.GREEN + "设备已重新连接，继续检测...")
                                # 重新连接成功后，更新端口号
                                selected_port = self.current_port
                            else:
                                # 如果无法重新连接，跳出内循环
                                break

                        # 读取设备信息
                        self.check_device()

                time.sleep(0.5)  # 短暂延迟，避免CPU占用过高

        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n程序被用户中断")
        except Exception as e:
            print(Fore.RED + f"\n程序出现错误: {str(e)}")
        finally:
            # 清理工作
            if self.ser and self.ser.is_open:
                try:
                    self.ser.close()
                    print(Fore.YELLOW + "已关闭串口连接")
                except:
                    pass
            print(Fore.GREEN + "程序退出，谢谢使用!")


def main():
    """主函数"""
    detector = ScreenDetector()
    detector.run()


if __name__ == "__main__":
    main()
