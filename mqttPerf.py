import ast
import math
import time
import paho.mqtt.client as mqtt
import threading
import random
import string
import logging
import json
import argparse
import psutil
import pandas as pd
import os
import uuid
from datetime import datetime
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init

# 配置锁，确保线程安全
connect_time_lock = Lock()
receive_msg_lock = Lock()
publish_msg_lock = Lock()
connection_stats_lock = Lock()

class MQTTLoadTester:
    def __init__(self, config_file=None):
        # 初始化配置
        self.config = self.load_config(config_file)
        self.setup_logging()
        
        # 性能数据收集
        self.connect_elapsed_time = []
        self.connections_count = self.config["num_publishers"] + self.config["num_subscribers"]
        self.sub_spend_time = {}
        self.sub_spend_time_list = []
        self.receive_msg_spend_time = {}
        self.receive_msg_spend_time_list = []
        self.receive_msg_count = []
        self.publish_msg_count = []
        
        # 系统资源监控数据
        self.resource_data = []
        
        # 性能数据记录
        self.performance_data = []
        
        # 消息丢失统计
        self.message_ids = {}  # 用于跟踪已发送消息
        self.received_ids = set()  # 用于跟踪已接收消息
        
        # 连接状态统计
        self.connection_failures = 0
        self.disconnections = 0
        self.reconnections = 0
        self.connection_times = {}  # 每个客户端的连接时间
        
        # 消息延迟分布统计
        self.latency_buckets = {
            "0-10ms": 0,
            "10-50ms": 0,
            "50-100ms": 0,
            "100-500ms": 0,
            "500-1000ms": 0,
            ">1000ms": 0
        }
        
        # QoS统计
        self.qos_success = {0: 0, 1: 0, 2: 0}
        self.qos_failure = {0: 0, 1: 0, 2: 0}
        
        # 错误统计
        self.protocol_errors = 0
        self.timeouts = 0
        
        # 客户端管理
        self.subscribers = []
        self.publishers = []
        self.heartbeats = []
        
        # 测试开始时间
        self.test_start_time = datetime.now()
        
        # 初始化主题订阅时间追踪
        for topic in self.config["sub_topics"]:
            self.sub_spend_time[topic] = []
        
        # 初始化消息接收时间追踪
        for topic in self.config["sub_topics"]:
            self.receive_msg_spend_time[topic] = []
        
        # 初始化colorama
        init(autoreset=True)
        
        # 运行状态
        self.running = True
        
    def load_config(self, config_file=None):
        """加载配置"""          
        # 默认配置
        default_config = {
            "broker": "139.224.192.36",
            "port": 1883,
            "username": "mqtttest",
            "password": "mqtttest2022",
            "num_subscribers": 200,
            "num_publishers": 200,
            "num_heartbeats": 20,
            "sub_topics": [
                "/screen/magicframe/cloud/setplaymode[-flat]/mf50",
                "/screen/magicframe/cloud/downloadpicture[-flat]/mf50",
                "/screen/magicframe/cloud/setbrightness[-flat]/mf50",
                "/screen/magicframe/cloud/setcolortemp[-flat]/mf50",
                "/screen/magicframe/cloud/turnon[-flat]/mf50",
                "/screen/magicframe/cloud/setsleepschedule[-flat]/mf50",
                "/screen/magicframe/cloud/playsync[-flat]/mf50",
                "/screen/magicframe/cloud/delvideo[-flat]/mf50",
                "/screen/magicframe/cloud/delpicture[-flat]/mf50",
                "/screen/magicframe/cloud/upgrade[-flat]/mf50",
                "/screen/magicframe/cloud/broadcast[-flat]/mf50",
                "/screen/magicframe/cloud/setscreengroupidandno[-flat]/mf50",
                "/screen/magicframe/cloud/setvolume[-flat]/mf50",
                "/screen/magicframe/cloud/setdirection[-flat]/mf50",
                "/screen/magicframe/cloud/reset[-flat]/mf50",
                "/screen/magicframe/cloud/settimezone[-flat]/mf50",
            ],
            "pub_topics": [
                "/screen/magicframe/cloud/downloadpicture[-flat]/mf50"
            ],
            "heartbeat_topics": [
                "mf50/screen/cloud/screengroupstatus[-flat]/"
            ],
            "publish_interval": 1,
            "heartbeat_interval": 30,
            "qos_level": 2,
            "report_interval": 10,
            "resource_monitor_interval": 5,
            "connection_timeout": 10,  # 连接超时时间
            "keep_alive": 60,  # Keep Alive时间
            "max_inflight": 100,  # 最大在途消息数
            "excel_report_dir": "reports"  # Excel报告保存目录
        }
        
        if config_file:
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                
        return default_config
    
    def setup_logging(self):
        """配置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - Line %(lineno)d - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_mqtt_client(self, client_id, subscribe=False):
        """创建MQTT客户端"""
        try:
            # 转换client_id为字符串类型，避免编码问题
            client_id = str(client_id)
            
            # 使用MQTTv5版本创建客户端并更新回调API版本
            client = mqtt.Client(
                client_id=client_id, 
                protocol=mqtt.MQTTv5,
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                transport="tcp"  # 明确指定传输协议
            )
            
            # 设置最大在途消息数
            client.max_inflight_messages_set(self.config.get("max_inflight", 20))
            
            # 设置重连间隔和尝试次数
            client.reconnect_delay_set(min_delay=1, max_delay=60)
            
            # 设置认证信息
            if self.config["username"] and self.config["password"]:
                client.username_pw_set(self.config["username"], self.config["password"])
            
            # 用户数据存储
            userdata = {
                "client_id": client_id,
                "subscribe": subscribe,
                "start_time": time.time(),
                "connection_time": 0,
                "connection_count": 0,
                "reconnected": False,
                "client_lock": threading.Lock()  # 为每个客户端添加锁
            }
            client.user_data_set(userdata)
            
            # 设置回调函数 - 使用正确的参数数量
            client.on_connect = lambda client, userdata, flags, reason_code, properties: self.on_connect(client, userdata, flags, reason_code, properties)
            client.on_disconnect = lambda client, userdata, reasonCode, properties: self.on_disconnect(client, userdata, reasonCode, properties)
            client.on_message = lambda client, userdata, msg: self.on_message(client, userdata, msg)
            client.on_publish = lambda client, userdata, mid, reason_code, properties: self.on_publish(client, userdata, mid, reason_code, properties)
            client.on_subscribe = lambda client, userdata, mid, reason_codes, properties: self.on_subscribe(client, userdata, mid, reason_codes, properties)
            
            # 添加错误日志回调
            client.on_log = lambda client, userdata, level, buf: self.on_log(client, userdata, level, buf)
            
            # 连接到broker
            client.connect_async(
                self.config["broker"], 
                self.config["port"], 
                keepalive=self.config["keep_alive"]
            )
            
            # 使用线程安全方式启动客户端循环
            client.loop_start()
            
            # 等待连接建立一个短暂的时间
            time.sleep(0.1)
            
            return client
        except Exception as e:
            self.logger.error(f"创建MQTT客户端失败: {e}")
            raise
    
    def connect_client(self, client, subscribe=False):
        """连接MQTT客户端"""
        try:
            client.connect(self.config["broker"], self.config["port"], keepalive=self.config["keep_alive"])
            client.loop_start()

            # 记录连接时间
            userdata = client._userdata
            userdata["connection_time"] = time.time()
            userdata["connection_count"] += 1
            self.connection_times[userdata["client_id"]] = userdata["connection_time"]

            # 订阅客户端连接时订阅主题
            if subscribe:
                for topic in self.config["sub_topics"]:
                    topic = client._client_id.decode('utf-8') + topic
                    client.subscribe(topic, qos=self.config["qos_level"])
                    self.logger.info(f"==========>{client._client_id} 订阅主题：{topic}")
        except Exception as e:
            self.logger.error(f"MQTT 客户端 {client._client_id} 连接失败: {e}")
            with connection_stats_lock:
                self.connection_failures += 1
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """连接回调函数"""
        self.logger.info(f"{client._client_id} 连接成功，返回码: {reason_code}")
        if reason_code == mqtt.CONNACK_ACCEPTED:
            self.logger.info(f"MQTT 客户端 {client._client_id} 已连接")
            end_time = time.time()
            token_time = round((end_time - userdata['start_time']) * 1000, 2)
            
            with connect_time_lock:
                self.connect_elapsed_time.append(token_time)
                
            with connection_stats_lock:
                # 更新连接统计
                userdata["connection_time"] = time.time()
                userdata["connection_count"] += 1
                
                # 记录连接事件
                if not hasattr(self, 'connection_events'):
                    self.connection_events = []
                
                self.connection_events.append({
                    "client_id": userdata["client_id"],
                    "event": "connect",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "reason_code": reason_code,
                    "connection_time_ms": token_time
                })
                
                if userdata["reconnected"]:
                    self.reconnections += 1
            
            self.logger.info(f"{client._client_id} 连接耗时：{token_time} ms")
            if userdata["subscribe"] and userdata["reconnected"]:
                userdata["reconnected"] = False
                for topic in self.config["sub_topics"]:
                    topic = client._client_id.decode('utf-8') + topic
                    client.subscribe(topic, qos=self.config["qos_level"])
                    self.logger.info(f"==========>{client._client_id} 重新订阅主题：{topic}")
        else:
            with connection_stats_lock:
                self.connection_failures += 1
                
                # 记录失败事件
                if not hasattr(self, 'connection_events'):
                    self.connection_events = []
                
                self.connection_events.append({
                    "client_id": userdata["client_id"],
                    "event": "connection_failure",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "reason_code": reason_code
                })
    
    def on_disconnect(self, client, userdata, reasonCode, properties=None):
        """断开连接回调函数"""
        if reasonCode != 0:
            self.logger.error(f"{client._client_id} 连接断开，返回码: {reasonCode}")
        else:
            self.logger.info(f"{client._client_id} 正常断开连接")
        
        with connection_stats_lock:
            self.disconnections += 1
            userdata["disconnection_time"] = time.time()
            userdata["reconnected"] = True
            
            # 记录断开连接事件
            if not hasattr(self, 'connection_events'):
                self.connection_events = []
            
            self.connection_events.append({
                "client_id": userdata["client_id"],
                "event": "disconnect",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reason_code": reasonCode,
                "connection_duration": userdata["disconnection_time"] - userdata["connection_time"] if userdata["connection_time"] else 0
            })
            
        if properties:
            self.logger.error(f"断开连接时的属性: {properties}")
    
    def on_message(self, client, userdata, msg):
        """消息回调函数"""
        try:
            payload = msg.payload.decode('utf-8')
            message_data = ast.literal_eval(payload)
            timestamp = message_data['time']
            
            # 检查消息是否包含ID
            if 'id' in message_data:
                message_id = message_data['id']
                self.track_message(message_id, is_sent=False)
            
            end_time = time.time()
            spend_time = round((end_time - timestamp) * 1000, 2)
            key = msg.topic.replace(client._client_id.decode('utf-8'), '')
            
            with receive_msg_lock:
                self.receive_msg_spend_time[key].append(spend_time)
                self.receive_msg_count.append(1)
                # 更新延迟分布
                self.update_latency_bucket(spend_time)
                
            self.logger.info(f"{client._client_id} 收到消息，耗时：{spend_time} ms：{payload}")
        except Exception as e:
            self.logger.error(f"处理接收消息时出错: {e}")
            self.protocol_errors += 1
    
    def update_latency_bucket(self, latency_ms):
        """更新延迟分布统计"""
        with receive_msg_lock:
            if latency_ms <= 10:
                self.latency_buckets["0-10ms"] += 1
            elif latency_ms <= 50:
                self.latency_buckets["10-50ms"] += 1
            elif latency_ms <= 100:
                self.latency_buckets["50-100ms"] += 1
            elif latency_ms <= 500:
                self.latency_buckets["100-500ms"] += 1
            elif latency_ms <= 1000:
                self.latency_buckets["500-1000ms"] += 1
            else:
                self.latency_buckets[">1000ms"] += 1
    
    def on_subscribe(self, client, userdata, mid, reason_code_list, properties):
        """订阅回调函数"""
        if "Granted" in str(reason_code_list[0]):
            self.logger.info(f"{client._client_id} 订阅成功，reason_code_list：{reason_code_list}, mid：{mid}")
            end_time = time.time()
            token_time = round((end_time - userdata['start_time']) * 1000, 2)
            
            if mid > 0 and (mid - 1) < len(self.config["sub_topics"]):
                with connect_time_lock:
                    self.sub_spend_time[self.config["sub_topics"][mid - 1]].append(token_time)
                    
            self.logger.info(f"{client._client_id} 订阅耗时：{token_time} ms")
        else:
            self.logger.error(f"{client._client_id} 订阅失败，reason_code_list：{reason_code_list}")
            self.qos_failure[self.config["qos_level"]] += 1
    
    def on_publish(self, client, userdata, mid, reason_code, properties):
        """发布回调函数"""
        with publish_msg_lock:
            qos = self.config["qos_level"]  # 当前配置的QoS级别
            self.qos_success[qos] += 1
    
    def on_publish_failure(self, client, userdata, mid):
        """发布失败回调函数"""
        with publish_msg_lock:
            qos = self.config["qos_level"]  # 当前配置的QoS级别
            self.qos_failure[qos] += 1
            self.logger.error(f"{client._client_id} 消息发布失败，mid: {mid}")
    
    def publish_messages(self, client, topic, interval, msg_type="测试消息"):
        """发布消息函数"""
        try:
            userdata = client._userdata
            client_id = userdata["client_id"]
            
            while self.running:
                try:
                    # 使用客户端特定的锁保护发布操作
                    with userdata["client_lock"]:
                        # 创建唯一消息ID
                        message_id = str(uuid.uuid4())
                        
                        # 构建消息内容
                        payload = {
                            'time': time.time(),
                            'msg': ''.join(random.choices(string.ascii_letters + string.digits, k=100)),
                            'id': message_id
                        }
                        
                        # 转换为JSON并发布
                        message = json.dumps(payload)
                        
                        # 记录发送的消息ID
                        self.track_message(message_id, is_sent=True)
                        
                        # 发布消息，确保不重叠
                        result = client.publish(
                            topic, 
                            message, 
                            qos=self.config["qos_level"]
                        )
                        
                        # 使用锁保护共享数据
                        with publish_msg_lock:
                            self.publish_msg_count.append(1)
                        
                        # 记录QoS成功/失败
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            self.qos_success[self.config["qos_level"]] += 1
                        else:
                            self.qos_failure[self.config["qos_level"]] += 1
                        
                        # 仅在开发环境或低频率下记录详细日志，避免I/O瓶颈
                        if random.random() < 0.01:  # 仅记录1%的消息，减少日志开销
                            self.logger.info(f"{client_id} 发布消息：{payload}, 主题：{topic}")
                        
                except Exception as e:
                    self.logger.error(f"发布消息时出错 {client_id}: {e}")
                    self.protocol_errors += 1
                    
                # 随机化发布间隔，防止消息风暴
                jitter = random.uniform(0.8, 1.2)  # 增加20%的随机性
                time.sleep(interval * jitter)
                
        except Exception as e:
            self.logger.error(f"发布消息线程出错: {e}")
    
    def monitor_resources(self):
        """监控系统资源使用情况"""
        while self.running:
            try:
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                # 网络IO统计
                net_io = psutil.net_io_counters()
                
                # 保存资源使用数据用于报告
                self.resource_data.append({
                    'timestamp': datetime.now(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv,
                    'packets_sent': net_io.packets_sent,
                    'packets_recv': net_io.packets_recv
                })
                
                self.logger.info(f"系统资源使用: CPU {cpu_percent}%, 内存 {memory_percent}%, "
                                 f"网络发送 {net_io.bytes_sent/1024:.2f}KB, 接收 {net_io.bytes_recv/1024:.2f}KB")
                
                # 如果资源使用过高，发出警告
                if cpu_percent > 90 or memory_percent > 90:
                    self.logger.warning(f"系统资源使用率过高！CPU: {cpu_percent}%, 内存: {memory_percent}%")
                    
                time.sleep(self.config["resource_monitor_interval"])
            except Exception as e:
                self.logger.error(f"监控资源时出错: {e}")
    
    def periodic_report(self):
        """定期生成性能报告"""
        start_time = time.time()
        prev_msg_count = 0
        prev_pub_count = 0
        
        while self.running:
            try:
                time.sleep(self.config["report_interval"])
                
                current_time = time.time()
                elapsed = current_time - start_time
                
                with receive_msg_lock:
                    current_msg_count = len(self.receive_msg_count)
                
                with publish_msg_lock:
                    current_pub_count = len(self.publish_msg_count)
                
                msg_rate = (current_msg_count - prev_msg_count) / self.config["report_interval"]
                pub_rate = (current_pub_count - prev_pub_count) / self.config["report_interval"]
                
                # 计算当前时间窗口的消息丢失率
                window_published = current_pub_count - prev_pub_count
                window_received = current_msg_count - prev_msg_count
                window_loss = max(0, window_published - window_received)
                window_loss_rate = (window_loss / window_published * 100) if window_published > 0 else 0
                
                # 保存性能数据用于报告
                self.performance_data.append({
                    'timestamp': datetime.now(),
                    'elapsed_time': elapsed,
                    'msg_rate': msg_rate,
                    'pub_rate': pub_rate,
                    'window_loss_rate': window_loss_rate,
                    'total_received': current_msg_count,
                    'total_published': current_pub_count,
                    'active_connections': self.connections_count - self.disconnections + self.reconnections,
                    'disconnections': self.disconnections
                })
                
                prev_msg_count = current_msg_count
                prev_pub_count = current_pub_count
                
                self.logger.info(f"性能报告: 运行时间 {elapsed:.2f}秒")
                self.logger.info(f"消息接收速率: {msg_rate:.2f}条/秒, 总接收: {current_msg_count}条")
                self.logger.info(f"消息发布速率: {pub_rate:.2f}条/秒, 总发布: {current_pub_count}条")
                self.logger.info(f"当前时间窗口消息丢失率: {window_loss_rate:.2f}%")
                self.logger.info(f"活动连接数: {self.connections_count - self.disconnections + self.reconnections}, 断开连接数: {self.disconnections}")
            except Exception as e:
                self.logger.error(f"生成性能报告时出错: {e}")
    
    def start_mqtt_clients(self):
        """启动MQTT客户端"""
        # 使用线程池管理
        executor = ThreadPoolExecutor(max_workers=min(200, self.connections_count + 10))
        
        try:
            # 启动资源监控
            monitor_thread = threading.Thread(target=self.monitor_resources)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # 启动性能报告线程
            report_thread = threading.Thread(target=self.periodic_report)
            report_thread.daemon = True
            report_thread.start()
            
            # 启动订阅客户端
            for i in range(self.config["num_subscribers"]):
                client_id = f"conn_subscriber_{i + 1}"
                client = self.create_mqtt_client(client_id, subscribe=True)
                self.connect_client(client, subscribe=True)
                self.subscribers.append(client)
            
            # 启动发布客户端
            for i in range(self.config["num_publishers"]):
                client_id = f"conn_publisher_{i + 1}"
                pub_topic = f"conn_subscriber_{i + 1}" + self.config["pub_topics"][0]
                client = self.create_mqtt_client(client_id)
                self.connect_client(client)
                future = executor.submit(self.publish_messages, client, pub_topic, self.config["publish_interval"])
                self.publishers.append((client, future))
            
            # 启动心跳报文发布客户端
            for i in range(self.config["num_heartbeats"]):
                client_id = f"conn_heartbeat_{i + 1}"
                pub_topic = self.config["pub_topics"][0] + f"conn_heartbeat_{i + 1}"
                client = self.create_mqtt_client(client_id)
                self.connect_client(client)
                future = executor.submit(self.publish_messages, client, pub_topic, self.config["heartbeat_interval"], "心跳包")
                self.heartbeats.append((client, future))
            
            # 保持主线程活跃
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在终止测试...")
            self.running = False
            self.generate_final_report()
            self.generate_excel_report()  # 生成Excel报告
            self.cleanup()
            executor.shutdown(wait=False)
        except Exception as e:
            self.logger.error(f"测试过程中发生错误: {e}")
            self.running = False
            self.generate_excel_report()  # 生成Excel报告
            self.cleanup()
            executor.shutdown(wait=False)
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        
        # 断开所有客户端连接
        for client in self.subscribers:
            try:
                client.disconnect()
                client.loop_stop()
            except Exception as e:
                self.logger.error(f"断开订阅客户端连接时出错: {e}")
        
        for client, _ in self.publishers:
            try:
                client.disconnect()
                client.loop_stop()
            except Exception as e:
                self.logger.error(f"断开发布客户端连接时出错: {e}")
        
        for client, _ in self.heartbeats:
            try:
                client.disconnect()
                client.loop_stop()
            except Exception as e:
                self.logger.error(f"断开心跳客户端连接时出错: {e}")
    
    def calculate_squared_diffs(self, data_list):
        """计算均值、标准差、最快、最慢"""
        if not data_list:
            return 0, 0, 0, 0
        
        fastest = min(data_list)
        slowest = max(data_list)
        mean_time = sum(data_list) / len(data_list)
        squared_diffs = [(t - mean_time) ** 2 for t in data_list]
        
        if not squared_diffs:
            return 0, 0, 0, 0
            
        variance = sum(squared_diffs) / len(squared_diffs)
        stddev = math.sqrt(variance)
        
        return round(stddev, 2), round(mean_time, 2), round(fastest, 2), round(slowest, 2)
    
    def calculate_sub_spendtime(self):
        """计算订阅耗时统计"""
        sub_stats = []
        receive_stats = []
        
        try:
            for key, value in self.sub_spend_time.items():
                if value:
                    stddev, average, fastest, slowest = self.calculate_squared_diffs(value)
                    self.sub_spend_time_list.append(
                        f'样本数：{self.config["num_subscribers"]}\t{key}：平均耗时：{average} ms，最快耗时：{fastest} ms，'
                        f'最慢耗时：{slowest} ms，耗时标准差：{stddev}'
                    )
                    
                    # 为Excel报告保存数据
                    sub_stats.append({
                        'topic': key,
                        'sample_count': self.config["num_subscribers"],
                        'avg_time_ms': average,
                        'fastest_ms': fastest,
                        'slowest_ms': slowest,
                        'stddev_ms': stddev
                    })
                    
            for key, value in self.receive_msg_spend_time.items():
                if value:
                    stddev, average, fastest, slowest = self.calculate_squared_diffs(value)
                    self.receive_msg_spend_time_list.append(
                        f'消息接收情况：\n样本数：{len(self.receive_msg_count)}\t{key}：平均耗时：{average} ms，'
                        f'最快耗时：{fastest} ms，最慢耗时：{slowest} ms，耗时标准差：{stddev}'
                    )
                    
                    # 为Excel报告保存数据
                    receive_stats.append({
                        'topic': key,
                        'sample_count': len(self.receive_msg_count),
                        'avg_time_ms': average,
                        'fastest_ms': fastest,
                        'slowest_ms': slowest,
                        'stddev_ms': stddev
                    })
        except Exception as e:
            self.logger.error(f"计算订阅耗时统计时出错: {e}")
            
        return sub_stats, receive_stats
    
    def generate_final_report(self):
        """生成最终测试报告"""
        self.logger.info("性能测试结束，生成最终报告...")
        
        # 连接耗时
        stddev, average, fastest, slowest = self.calculate_squared_diffs(self.connect_elapsed_time)
        self.logger.info(
            f"平均连接速度：{average} ms，最快连接时间：{fastest} ms，最慢连接时间：{slowest} ms， 连接标准差：{stddev}"
        )
        
        # 消息丢失计算
        loss_info = self.calculate_message_loss()
        
        # 发送和接收消息统计
        with publish_msg_lock, receive_msg_lock:
            self.logger.info(f"发送的消息数量：{len(self.publish_msg_count)}，接收到的消息数量：{len(self.receive_msg_count)}")
            self.logger.info(f"消息丢失率：{loss_info['loss_rate']:.2f}%，丢失消息数：{loss_info['lost_messages']}")
        
        # 连接可靠性统计
        self.logger.info(f"连接失败次数：{self.connection_failures}，断开连接次数：{self.disconnections}，重连次数：{self.reconnections}")
        
        # QoS统计
        self.logger.info(f"QoS {self.config['qos_level']} 成功发布：{self.qos_success[self.config['qos_level']]}，失败：{self.qos_failure[self.config['qos_level']]}")
        
        # 延迟分布
        self.logger.info("消息延迟分布：")
        for bucket, count in self.latency_buckets.items():
            self.logger.info(f"  {bucket}: {count} 条消息")
        
        # 订阅和接收消息耗时
        self.calculate_sub_spendtime()
        
        for item in self.sub_spend_time_list:
            self.logger.info(item)
            
        for item in self.receive_msg_spend_time_list:
            self.logger.info(item)
        
        self.logger.info("性能测试完成！")
        
    def generate_excel_report(self):
        """生成Excel格式的性能测试报告"""
        try:
            self.logger.info("正在生成Excel格式报告...")
            
            # 确保报告目录存在
            os.makedirs(self.config["excel_report_dir"], exist_ok=True)
            
            # 创建报告文件名
            timestamp = self.test_start_time.strftime("%Y%m%d_%H%M%S")
            report_filename = os.path.join(self.config["excel_report_dir"], f"mqtt_perf_report_{timestamp}.xlsx")
            
            # 创建Excel写入器
            with pd.ExcelWriter(report_filename, engine='openpyxl') as writer:
                # 测试配置信息
                config_df = pd.DataFrame([{
                    "测试开始时间": self.test_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "测试结束时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "测试持续时间(秒)": (datetime.now() - self.test_start_time).total_seconds(),
                    "MQTT代理服务器": f"{self.config['broker']}:{self.config['port']}",
                    "订阅客户端数量": self.config["num_subscribers"],
                    "发布客户端数量": self.config["num_publishers"],
                    "心跳客户端数量": self.config["num_heartbeats"],
                    "QoS级别": self.config["qos_level"],
                    "发布间隔(秒)": self.config["publish_interval"],
                    "心跳间隔(秒)": self.config["heartbeat_interval"],
                    "连接超时(秒)": self.config["connection_timeout"],
                    "Keep Alive(秒)": self.config["keep_alive"]
                }])
                config_df.to_excel(writer, sheet_name="测试配置", index=False)
                
                # 连接性能
                connect_stats = pd.DataFrame([{
                    "连接总数": len(self.connect_elapsed_time),
                    "平均连接时间(ms)": sum(self.connect_elapsed_time) / len(self.connect_elapsed_time) if self.connect_elapsed_time else 0,
                    "最快连接(ms)": min(self.connect_elapsed_time) if self.connect_elapsed_time else 0,
                    "最慢连接(ms)": max(self.connect_elapsed_time) if self.connect_elapsed_time else 0,
                    "连接时间标准差": round(math.sqrt(sum((x - (sum(self.connect_elapsed_time) / len(self.connect_elapsed_time))) ** 2 
                                       for x in self.connect_elapsed_time) / len(self.connect_elapsed_time)), 2) 
                                       if self.connect_elapsed_time else 0,
                    "连接失败次数": self.connection_failures,
                    "断开连接次数": self.disconnections,
                    "重连次数": self.reconnections,
                    "连接成功率(%)": (1 - (self.connection_failures / (len(self.connect_elapsed_time) + self.connection_failures))) * 100 
                                  if (len(self.connect_elapsed_time) + self.connection_failures) > 0 else 0
                }])
                connect_stats.to_excel(writer, sheet_name="连接性能", index=False)
                
                # 消息收发统计
                loss_info = self.calculate_message_loss()
                message_stats = pd.DataFrame([{
                    "发送消息总数": len(self.publish_msg_count),
                    "接收消息总数": len(self.receive_msg_count),
                    "消息丢失数": loss_info["lost_messages"],
                    "消息丢失率(%)": loss_info["loss_rate"],
                    "基于ID丢失数": loss_info["lost_messages_by_id"],
                    "基于ID丢失率(%)": loss_info["loss_rate_by_id"],
                    "测试持续时间(秒)": (datetime.now() - self.test_start_time).total_seconds(),
                    "平均发送速率(条/秒)": len(self.publish_msg_count) / (datetime.now() - self.test_start_time).total_seconds() 
                                      if (datetime.now() - self.test_start_time).total_seconds() > 0 else 0,
                    "平均接收速率(条/秒)": len(self.receive_msg_count) / (datetime.now() - self.test_start_time).total_seconds() 
                                      if (datetime.now() - self.test_start_time).total_seconds() > 0 else 0,
                    "QoS0成功率(%)": self.calculate_qos_success_rate(0),
                    "QoS1成功率(%)": self.calculate_qos_success_rate(1),
                    "QoS2成功率(%)": self.calculate_qos_success_rate(2)
                }])
                message_stats.to_excel(writer, sheet_name="消息统计", index=False)
                
                # 订阅性能统计
                sub_stats, receive_stats = self.calculate_sub_spendtime()
                
                if sub_stats:
                    sub_df = pd.DataFrame(sub_stats)
                    sub_df.to_excel(writer, sheet_name="订阅性能", index=False)
                
                if receive_stats:
                    receive_df = pd.DataFrame(receive_stats)
                    receive_df.to_excel(writer, sheet_name="消息接收性能", index=False)
                
                # 延迟分布统计
                latency_df = pd.DataFrame([{k: v for k, v in self.latency_buckets.items()}])
                latency_df.to_excel(writer, sheet_name="延迟分布", index=False)
                
                # 连接可靠性详情
                if hasattr(self, 'connection_events') and self.connection_events:
                    conn_df = pd.DataFrame(self.connection_events)
                    conn_df.to_excel(writer, sheet_name="连接事件", index=False)
                
                # 性能数据趋势
                if hasattr(self, 'performance_data') and self.performance_data:
                    perf_df = pd.DataFrame(self.performance_data)
                    perf_df.to_excel(writer, sheet_name="性能趋势", index=False)
                
                # 错误与异常统计
                error_stats = pd.DataFrame([{
                    "协议错误数": self.protocol_errors,
                    "超时次数": self.timeouts,
                    "重连失败次数": self.connection_failures,
                    "消息发布失败数": sum(self.qos_failure.values())
                }])
                error_stats.to_excel(writer, sheet_name="错误统计", index=False)
                
                # 资源使用情况
                if self.resource_data:
                    resource_df = pd.DataFrame(self.resource_data)
                    resource_df.to_excel(writer, sheet_name="资源使用", index=False)
            
            self.logger.info(f"Excel报告已生成: {report_filename}")
            
        except Exception as e:
            self.logger.error(f"生成Excel报告时发生错误: {e}")
    
    def calculate_message_loss(self):
        """计算消息丢失率"""
        total_published = len(self.publish_msg_count)
        total_received = len(self.receive_msg_count)
        
        # 基于消息计数的丢失率
        lost_messages = max(0, total_published - total_received)
        loss_rate = (lost_messages / total_published * 100) if total_published > 0 else 0
        
        # 基于消息ID的丢失率
        sent_ids_count = len(self.message_ids)
        received_ids_count = len(self.received_ids)
        lost_by_id = max(0, sent_ids_count - received_ids_count)
        loss_rate_by_id = (lost_by_id / sent_ids_count * 100) if sent_ids_count > 0 else 0
        
        return {
            "total_published": total_published,
            "total_received": total_received,
            "lost_messages": lost_messages,
            "loss_rate": loss_rate,
            "sent_ids_count": sent_ids_count,
            "received_ids_count": received_ids_count,
            "lost_messages_by_id": lost_by_id,
            "loss_rate_by_id": loss_rate_by_id
        }
    
    def calculate_qos_success_rate(self, qos_level):
        """计算指定QoS级别的成功率"""
        total = self.qos_success.get(qos_level, 0) + self.qos_failure.get(qos_level, 0)
        if total == 0:
            return 0
        return (self.qos_success.get(qos_level, 0) / total) * 100
    
    def track_message(self, message_id, is_sent=True):
        """跟踪消息发送和接收状态"""
        if is_sent:
            with publish_msg_lock:
                self.message_ids[message_id] = {
                    "send_time": time.time(),
                    "received": False
                }
        else:
            with receive_msg_lock:
                if message_id in self.message_ids:
                    self.message_ids[message_id]["received"] = True
                    self.message_ids[message_id]["receive_time"] = time.time()
                    latency = (self.message_ids[message_id]["receive_time"] - self.message_ids[message_id]["send_time"]) * 1000
                    self.update_latency_bucket(latency)
                self.received_ids.add(message_id)

    def on_log(self, client, userdata, level, buf):
        """记录MQTT客户端库的日志"""
        if level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT错误 ({userdata['client_id']}): {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT警告 ({userdata['client_id']}): {buf}")
        # 调试级别的日志太多，仅在需要时启用
        # elif level == mqtt.MQTT_LOG_DEBUG:
        #     self.logger.debug(f"MQTT调试 ({userdata['client_id']}): {buf}")

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='MQTT性能测试工具')
    parser.add_argument('-c', '--config', help='配置文件路径')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_arguments()
    tester = MQTTLoadTester(args.config)
    tester.start_mqtt_clients()

if __name__ == "__main__":
    main()