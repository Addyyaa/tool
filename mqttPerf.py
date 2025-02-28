import math
import time
import paho.mqtt.client as mqtt
import threading
import random
import logging
import json
import argparse
import psutil
import pandas as pd
import os
import uuid
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from colorama import init
import numpy as np
import traceback
import signal
import concurrent.futures
import sys

# 配置锁，确保线程安全
connect_time_lock = threading.RLock()
receive_msg_lock = threading.RLock()
publish_msg_lock = threading.RLock()
connection_stats_lock = threading.RLock()
message_tracking_lock = threading.RLock()  # 添加消息跟踪锁


class MQTTLoadTester:
    def __init__(self, config_file=None):
        """初始化测试对象"""
        # 先设置默认日志
        self.setup_default_logging()
        
        # 加载配置
        self.config = self.load_config(config_file)
        
        # 根据配置设置日志
        self.setup_logging()
        
        # 测试运行状态
        self.running = False
        self.test_start_time = None
        
        # 客户端列表
        self.subscribers = []
        self.publishers = []
        self.heartbeats = []
        
        # 线程锁
        self.client_lock = threading.Lock()
        self.qos_lock = threading.Lock()
        
        # 连接统计
        self.connect_elapsed_time = []  # 连接耗时(毫秒)
        self.min_connect_time = float('inf')  # 最小连接时间，初始化为无穷大
        self.max_connect_time = 0       # 最大连接时间
        self.avg_connect_time = 0       # 平均连接时间
        self.conn_time_std_dev = 0  # 添加标准差属性初始化
        self.connection_failures = 0    # 连接失败次数
        self.disconnections = 0         # 断开连接次数
        self.reconnections = 0          # 重连次数
        self.connection_times = {}      # 每个客户端的连接时间
        
        # 消息统计
        self.publish_msg_count = []     # 发布的消息ID列表
        self.receive_msg_count = []     # 接收到的消息ID列表
        self.publish_msg_time = {}      # 发布消息的时间戳 {message_id: timestamp}
        self.receive_msg_time = {}      # 接收消息的时间戳 {message_id: timestamp}
        self.receive_msg_spend_time = {} # 接收消息延迟 {topic: [delay1, delay2, ...]}
        self.sub_spend_time = {}        # 订阅延迟 {topic: [delay1, delay2, ...]}
        
        # QoS统计
        self.qos_success = {0: 0, 1: 0, 2: 0}  # 各QoS级别成功计数
        self.qos_failure = {0: 0, 1: 0, 2: 0}  # 各QoS级别失败计数
        
        # 延迟分布统计
        self.latency_buckets = {
            "0-10ms": 0,
            "10-50ms": 0,
            "50-100ms": 0,
            "100-500ms": 0,
            "500-1000ms": 0,
            ">1000ms": 0
        }
        
        # 初始化colorama
        init(autoreset=True)
        
        # 消息跟踪相关
        self.message_ids = {}
        self.received_ids = set()
        
        # 添加订阅耗时相关属性
        self.sub_spend_time_list = []
        self.receive_msg_spend_time_list = []
        
        # 添加资源监控相关属性
        self.resource_data = []

    def setup_default_logging(self):
        """设置默认日志系统"""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - Line %(lineno)d - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            self.logger.setLevel(logging.INFO)

    def setup_logging(self):
        """根据配置设置完整的日志系统"""
        # 如果已经有了默认日志系统，先清除
        if hasattr(self, 'logger') and self.logger.handlers:
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

        # 创建日志记录器
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if self.config.get("debug", False) else logging.INFO)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - Line %(lineno)d - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器（如果需要）
        log_file = self.config.get("log_file")
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def load_config(self, config_file):
        """加载配置文件"""
        default_config = {
            "broker": "139.224.192.36",
            "port": 1883,
            "username": "mqtttest",
            "password": "mqtttest2022",
            "num_subscribers": 10,
            "num_publishers": 10,
            "num_heartbeats": 10,
            "qos_level": 1,
            "test_duration": 20,
            "publish_interval": 1,
            "heartbeat_interval": 5,
            "pub_topics": ["/screen/magicframe/cloud/downloadpicture[-flat]/mf50"],
            "sub_topics": ["/screen/magicframe/cloud/setplaymode[-flat]/mf50",
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
                           "/screen/magicframe/cloud/settimezone[-flat]/mf50", ],
            "heartbeat_topics": ["mf50/screen/cloud/screengroupstatus[-flat]/"],
            "excel_report_dir": "reports",
            "max_threads": 200,
            "debug": False,
            "report_interval": 5,
            "resource_monitor_interval": 5,
            "log_file": None,
            "keep_alive": 60  # 添加keep_alive参数
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    # 更新默认配置
                    default_config.update(user_config)
                    self.logger.info(f"已加载配置文件: {config_file}")
            except Exception as e:
                self.logger.error(f"加载配置文件出错: {e}")
        else:
            self.logger.warning("未找到配置文件，使用默认配置")

        return default_config

    def create_mqtt_client(self, client_id, subscribe=False):
        """创建MQTT客户端"""
        try:
            # 创建客户端 - 使用MQTTv5
            client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
            
            # 创建用户数据
            userdata = {
                'client_id': client_id,
                'start_time': time.time(),
                'connection_count': 0,
                'connection_time': 0
            }
            client.user_data_set(userdata)
            
            # 设置回调函数
            client.on_connect = self.on_connect
            client.on_disconnect = self.on_disconnect
            client.on_message = self.on_message
            client.on_publish = self.on_publish
            client.on_subscribe = self.on_subscribe
            client.on_log = self.on_log
            
            # 设置认证信息
            if self.config.get("username") and self.config.get("password"):
                client.username_pw_set(self.config["username"], self.config["password"])
            
            # 记录连接开始时间
            start_time = time.time()
            with connect_time_lock:
                self.connection_times[client_id] = start_time
            
            # 设置keep_alive参数
            keep_alive = self.config.get("keep_alive", 60)
            
            try:
                # 尝试连接MQTT代理
                self.logger.info(f"尝试连接到 {self.config['broker']}:{self.config['port']}")
                client.connect_async(self.config["broker"], self.config["port"], keepalive=keep_alive)
                
                # 启动网络循环
                client.loop_start()
                
                # 等待连接完成
                time.sleep(0.5)
                
                # 如果是订阅者，订阅主题
                if subscribe:
                    print(f"为 {client_id} 订阅主题...")
                    # 订阅发布主题
                    for topic in self.config["pub_topics"]:
                        client.subscribe(topic, qos=self.config.get("qos_level", 0))
                        print(f"订阅者 {client_id} 订阅主题: {topic}")
                        self.logger.info(f"订阅者 {client_id} 订阅主题: {topic}")
                    
                    # 也订阅订阅主题列表中的主题
                    for topic in self.config["sub_topics"]:
                        client.subscribe(topic, qos=self.config.get("qos_level", 0))
                        print(f"订阅者 {client_id} 订阅主题: {topic}")
                        self.logger.info(f"订阅者 {client_id} 订阅主题: {topic}")
                
                return client
            except Exception as e:
                self.logger.error(f"连接失败: {e}. 请确认MQTT代理 {self.config['broker']}:{self.config['port']} 正在运行。")
                return None
        except Exception as e:
            self.logger.error(f"创建MQTT客户端失败: {e}")
            return None

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

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        """处理连接事件 (MQTTv5版本)"""
        try:
            client_id = userdata.get('client_id', 'unknown')

            # 计算连接耗时
            current_time = time.time()

            with connect_time_lock:
                if client_id in self.connection_times:
                    start_time = self.connection_times[client_id]
                    elapsed = (current_time - start_time) * 1000  # 转换为毫秒

                    # 添加到连接耗时列表
                    with connection_stats_lock:
                        self.connect_elapsed_time.append(elapsed)
                        
                        # 更新连接统计信息
                        if elapsed < self.min_connect_time:
                            self.min_connect_time = elapsed
                        if elapsed > self.max_connect_time:
                            self.max_connect_time = elapsed
                        
                        # 计算平均连接时间
                        total_elapsed = sum(self.connect_elapsed_time)
                        total_connections = len(self.connect_elapsed_time)
                        self.avg_connect_time = total_elapsed / total_connections if total_connections > 0 else 0

                    if reason_code == 0:
                        self.logger.info(f"客户端 {client_id} 连接成功，耗时 {elapsed:.2f}毫秒")
                        print(f"连接成功: {client_id}, 耗时 {elapsed:.2f}毫秒")
                        
                        # 订阅者重新订阅主题
                        if client_id.startswith("conn_subscriber_"):
                            for topic in self.config["pub_topics"]:
                                client.subscribe(topic, qos=self.config.get("qos_level", 0))
                                print(f"连接后重新订阅: {client_id} -> {topic}")
                            for topic in self.config["sub_topics"]:
                                client.subscribe(topic, qos=self.config.get("qos_level", 0))
                                print(f"连接后重新订阅: {client_id} -> {topic}")
                    else:
                        self.logger.warning(f"客户端 {client_id} 连接失败，返回码: {reason_code}")
                        with connection_stats_lock:
                            self.connection_failures += 1

            # 打印当前连接统计信息
            with connection_stats_lock:
                print(f"连接统计 - 最小: {self.min_connect_time:.2f}毫秒, 最大: {self.max_connect_time:.2f}毫秒, " +
                      f"平均: {self.avg_connect_time:.2f}毫秒, 总连接数: {len(self.connect_elapsed_time)}")

        except Exception as e:
            self.logger.error(f"处理连接事件时出错: {e}")

    def on_disconnect(self, client, userdata, reason_code, properties=None):
        """处理断开连接事件 (MQTTv5版本)"""
        client_id = userdata.get("client_id", "未知客户端")
        self.logger.info(f"客户端 {client_id} 断开连接，原因码: {reason_code}")
        
        with connection_stats_lock:
            self.disconnections += 1
        
        # 如果不是正常断开且测试仍在运行，尝试重连
        if reason_code != 0 and self.running:
            self.logger.warning(f"客户端 {client_id} 意外断开，尝试重连...")
            try:
                client.reconnect()
                with connection_stats_lock:
                    self.reconnections += 1
                self.logger.info(f"客户端 {client_id} 重连成功")
            except Exception as e:
                self.logger.error(f"客户端 {client_id} 重连失败: {e}")

    def on_message(self, client, userdata, msg):
        """处理接收到的消息 (MQTTv5版本)"""
        try:
            client_id = userdata['client_id'] if userdata and 'client_id' in userdata else 'unknown'
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            # 当前时间
            received_time = time.time()
            
            # 打印原始接收到的消息
            print(f"\n===== 订阅者收到消息 =====")
            print(f"订阅者: {client_id}")
            print(f"主题: {topic}")
            print(f"内容: {payload[:150]}{'...' if len(payload) > 150 else ''}")
            print("==========================\n")
            
            # 记录到日志
            self.logger.info(f"订阅者 {client_id} 从主题 {topic} 接收到消息")
            
            # 处理消息，尝试解析JSON
            try:
                message_data = json.loads(payload)
                message_id = message_data.get("id", "unknown")
                send_time = message_data.get("timestamp", 0)
                
                # 计算消息延迟(毫秒)
                latency_ms = (received_time - send_time) * 1000 if send_time > 0 else 0
                
                # 记录接收到的消息
                with receive_msg_lock:
                    if message_id not in self.receive_msg_count:
                        self.receive_msg_count.append(message_id)
                        self.receive_msg_time[message_id] = received_time
                        
                        # 更新QoS统计，假设所有消息都是成功的
                        qos = msg.qos
                        with self.qos_lock:
                            if qos in self.qos_success:
                                self.qos_success[qos] += 1
                        
                        # 记录每个主题的接收延迟
                        if topic not in self.receive_msg_spend_time:
                            self.receive_msg_spend_time[topic] = []
                        
                        self.receive_msg_spend_time[topic].append(latency_ms)
                        
                        # 更新延迟分布统计
                        self.update_latency_distribution(latency_ms)
                        
                        print(f"收到新消息! ID: {message_id}, 延迟: {latency_ms:.2f}ms, 当前接收总数: {len(self.receive_msg_count)}")
                        
            except json.JSONDecodeError:
                # 处理非JSON消息
                self.logger.info(f"接收到非JSON格式消息")
                with receive_msg_lock:
                    # 对于非JSON消息，使用随机ID防止重复计数
                    message_id = f"non-json_{time.time()}_{random.randint(1,1000)}"
                    self.receive_msg_count.append(message_id)
                    self.receive_msg_time[message_id] = received_time
                    print(f"收到非JSON消息! 当前接收总数: {len(self.receive_msg_count)}")
            
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")
            traceback.print_exc()

    def update_latency_distribution(self, latency_ms):
        """更新延迟分布统计"""
        try:
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
                
                total = sum(self.latency_buckets.values())
                if total > 0 and total % 10 == 0:  # 每10条消息打印一次
                    print("\n----- 延迟分布 -----")
                    for bucket, count in self.latency_buckets.items():
                        percentage = (count / total) * 100 if total > 0 else 0
                        print(f"{bucket}: {count} ({percentage:.2f}%)")
                    print("--------------------\n")
        except Exception as e:
            self.logger.error(f"更新延迟分布时出错: {e}")

    def on_subscribe(self, client, userdata, mid, reason_codes=None, properties=None):
        """订阅回调函数 - 适用于 MQTTv5"""
        try:
            # 获取返回代码 - 正确处理不同参数情况
            result_code = 0
            if reason_codes is not None:
                if isinstance(reason_codes, list) and reason_codes:
                    result_code = reason_codes[0]
                else:
                    result_code = reason_codes
            
            client_id = userdata.get('client_id', 'unknown') if userdata else 'unknown'
            
            if result_code < 128:  # 成功代码小于128
                self.logger.info(f"{client_id} 订阅成功，返回码：{result_code}, mid：{mid}")
                print(f"{client_id} 订阅成功，返回码：{result_code}, mid：{mid}")
                
                # 计算订阅耗时
                if userdata and 'start_time' in userdata:
                    end_time = time.time()
                    token_time = round((end_time - userdata['start_time']) * 1000, 2)
                    
                    # 不访问properties对象的内容
                    self.logger.info(f"{client_id} 订阅耗时：{token_time} ms")
                    print(f"{client_id} 订阅耗时：{token_time} ms")
                    
                    # 使用通用主题标识符
                    with self.qos_lock:
                        generic_topic = f"topic_mid_{mid}"
                        if generic_topic not in self.sub_spend_time:
                            self.sub_spend_time[generic_topic] = []
                        self.sub_spend_time[generic_topic].append(token_time)
            else:
                self.logger.error(f"{client_id} 订阅失败，返回码：{result_code}")
                print(f"警告: {client_id} 订阅失败，返回码：{result_code}")
                with self.qos_lock:
                    qos = self.config.get("qos_level", 0)
                    self.qos_failure[qos] += 1
        except Exception as e:
            self.logger.error(f"处理订阅回调时出错: {e}")
            print(f"订阅回调错误: {e}")

    def on_publish(self, client, userdata, mid):
        """发布回调函数 (MQTTv5版本)"""
        try:
            with publish_msg_lock:
                qos = self.config["qos_level"]  # 当前配置的QoS级别
                self.qos_success[qos] += 1
                
                # 添加调试日志
                if self.config.get("debug", False):
                    client_id = userdata.get('client_id', 'unknown') if userdata else 'unknown'
                    self.logger.debug(f"消息发布成功: 客户端={client_id}, mid={mid}")
        except Exception as e:
            self.logger.error(f"处理发布回调时出错: {e}")

    def on_publish_failure(self, client, userdata, mid):
        """发布失败回调函数"""
        with publish_msg_lock:
            qos = self.config["qos_level"]  # 当前配置的QoS级别
            self.qos_failure[qos] += 1
            self.logger.error(f"{client._client_id} 消息发布失败，mid: {mid}")

    def publish_messages(self, client, topic, interval, msg_type="消息"):
        """定期发布消息"""
        try:
            counter = 0
            last_publish_time = time.time()
            
            client_id = client._client_id.decode('utf-8') if hasattr(client, '_client_id') else 'unknown'
            
            # 添加调试日志
            self.logger.info(f"发布者 {client_id} 开始发布消息到主题: {topic}")
            print(f"发布者 {client_id} 开始发布消息到主题: {topic}")
            
            # 确保消息能被订阅者接收 - 设置较小的发布间隔
            real_interval = min(interval, 1.0)  # 最大1秒
            
            while self.running:
                try:
                    # 当前时间
                    now = time.time()
                    
                    # 检查是否到达发送间隔
                    if now - last_publish_time >= real_interval:
                        # 更新上次发布时间
                        last_publish_time = now
                        
                        # 创建消息ID
                        message_id = f"{client_id}_{counter}"
                        
                        # 构建消息内容
                        message = {
                            "id": message_id,
                            "client": client_id,
                            "type": msg_type,
                            "timestamp": now,
                            "seq": counter,
                            "data": "测试消息内容 " * 5  # 添加一些内容
                        }
                        
                        # 转换为JSON
                        message_json = json.dumps(message)
                        
                        # 打印发布的消息
                        print(f"\n----- 发布新消息 -----")
                        print(f"发布者: {client_id}")
                        print(f"主题: {topic}")
                        print(f"内容: {message_json[:150]}...")
                        print("------------------------\n")
                        
                        # 使用客户端锁保护发布操作
                        with self.client_lock:
                            # 发布消息到指定主题
                            qos = self.config.get("qos_level", 0)
                            result = client.publish(topic, message_json, qos=qos)
                            
                            # 记录发布消息
                            with publish_msg_lock:
                                if message_id not in self.publish_msg_count:
                                    self.publish_msg_count.append(message_id)
                                    self.publish_msg_time[message_id] = now
                                    
                                    # 更新计数器和统计
                                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                                        with self.qos_lock:
                                            self.qos_success[qos] += 1
                                    else:
                                        with self.qos_lock:
                                            self.qos_failure[qos] += 1
                            
                        # 更新计数器
                        counter += 1
                        
                    # 睡眠一小段时间，确保订阅者有时间处理消息
                    time.sleep(0.2)
                    
                    # 打印发布统计
                    if counter % 10 == 0:
                        print(f"发布者 {client_id} 已发布 {counter} 条消息")
                    
                except Exception as e:
                    self.logger.error(f"发布单条消息时出错: {e}")
                    traceback.print_exc()
                    time.sleep(1)  # 出错后暂停一下
                
        except Exception as e:
            self.logger.error(f"发布消息线程出错 {client_id}: {e}")
            traceback.print_exc()

    def monitor_resources(self):
        """监控系统资源使用情况"""
        try:
            interval = self.config.get("resource_monitor_interval", 5)  # 使用get并提供默认值

            while self.running:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent

                # 获取网络统计
                net_io = psutil.net_io_counters()
                bytes_sent = net_io.bytes_sent
                bytes_recv = net_io.bytes_recv

                # 记录数据
                self.resource_data.append({
                    '时间戳': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'CPU使用率': cpu_percent,
                    '内存使用率': memory_percent,
                    '网络发送': bytes_sent / 1024,  # 转换为KB
                    '网络接收': bytes_recv / 1024  # 转换为KB
                })

                # 记录日志
                self.logger.info(f"系统资源使用: CPU {cpu_percent}%, 内存 {memory_percent}%, "
                                 f"网络发送 {bytes_sent / 1024:.2f}KB, 接收 {bytes_recv / 1024:.2f}KB")

                time.sleep(interval)
        except Exception as e:
            self.logger.error(f"监控资源时出错: {e}")

    def periodic_report(self):
        """定期生成性能报告"""
        try:
            interval = self.config.get("report_interval", 5)
            last_report_time = time.time()

            while self.running:
                now = time.time()

                # 每隔指定时间生成一次报告
                if now - last_report_time >= interval:
                    last_report_time = now

                    # 只生成性能报告，不生成Excel报告
                    self.generate_performance_report()

                    # 不在此处生成Excel报告，仅在测试结束时生成
                    # self.generate_excel_report()

                time.sleep(1)
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
                future = executor.submit(self.publish_messages, client, pub_topic, self.config["heartbeat_interval"],
                                         "心跳包")
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
        """清理资源，关闭所有客户端连接"""
        try:
            self.logger.info("正在清理资源...")

            # 关闭所有订阅者客户端
            for client in self.subscribers:
                try:
                    client.disconnect()
                    client.loop_stop()
                except Exception as e:
                    self.logger.debug(f"断开订阅者连接时出错: {e}")

            # 关闭所有发布者客户端
            for client in self.publishers:
                try:
                    client.disconnect()
                    client.loop_stop()
                except Exception as e:
                    self.logger.debug(f"断开发布者连接时出错: {e}")

            # 关闭所有心跳客户端
            for client in self.heartbeats:
                try:
                    client.disconnect()
                    client.loop_stop()
                except Exception as e:
                    self.logger.debug(f"断开心跳客户端连接时出错: {e}")

            # 给客户端一些时间正常关闭
            time.sleep(0.5)

            self.logger.info("所有MQTT客户端已停止")

        except Exception as e:
            self.logger.error(f"清理资源时出错: {e}")

    def handle_interrupt(self, signum, frame):
        """处理中断信号，安全地终止测试"""
        print("\n收到中断信号，正在安全退出...")
        self.logger.info("收到中断信号，正在安全退出...")

        # 标记测试停止
        self.running = False

        # 生成最终性能报告
        try:
            self.logger.info("生成中断时的性能报告...")
            self.generate_performance_report()
        except Exception as e:
            self.logger.error(f"生成性能报告失败: {e}")

        # 清理资源
        try:
            self.cleanup()
        except Exception as e:
            self.logger.error(f"清理资源失败: {e}")

        # 生成Excel报告
        try:
            self.logger.info("开始生成中断时的Excel报告...")
            report_path = self.generate_excel_report()
            if report_path:
                self.logger.info(f"中断状态报告已生成: {report_path}")
            else:
                self.logger.error("中断状态报告生成失败")
        except Exception as e:
            self.logger.error(f"生成Excel报告失败: {e}")
            traceback.print_exc()

        # 等待一点时间确保日志写入
        time.sleep(1)

        print("测试已安全终止，报告已生成")

        # 强制退出
        sys.exit(0)

    def calculate_squared_diffs(self, data_list):
        """计算标准差和其他统计数据"""
        if not data_list:
            return 0, 0, 0, 0
        
        # 计算平均值
        mean = sum(data_list) / len(data_list)
        
        # 计算方差
        if len(data_list) > 1:
            variance = sum((x - mean) ** 2 for x in data_list) / len(data_list)
            std_dev = variance ** 0.5
        else:
            variance = 0
            std_dev = 0
        
        # 查找最小值和最大值
        min_val = min(data_list) if data_list else 0
        max_val = max(data_list) if data_list else 0
        
        return std_dev, mean, min_val, max_val

    def calculate_sub_spendtime(self):
        """计算订阅和接收消息的耗时统计"""
        try:
            # 确保列表存在
            if not hasattr(self, 'sub_spend_time_list'):
                self.sub_spend_time_list = []
            if not hasattr(self, 'receive_msg_spend_time_list'):
                self.receive_msg_spend_time_list = []
                
            # 初始化返回值数据
            sub_stats = []
            receive_stats = []
            
            # 处理订阅耗时
            for key, value in self.sub_spend_time.items():
                if len(value) > 0:
                    sdt_dev, average, fastest, slowest = self.calculate_squared_diffs(value)
                    info_str = (f'样本数：{len(self.subscribers)}\t{key}：平均耗时：{average} ms，最快耗时：{fastest} ms，'
                               f'最慢耗时：{slowest} ms，耗时标准差：{sdt_dev}')
                    self.sub_spend_time_list.append(info_str)
                    
                    # 添加到统计数据
                    sub_stats.append({
                        "主题": key,
                        "样本数": len(self.subscribers),
                        "平均耗时(ms)": average,
                        "最快耗时(ms)": fastest,
                        "最慢耗时(ms)": slowest,
                        "标准差": sdt_dev
                    })
            
            # 处理接收消息耗时
            for key, value in self.receive_msg_spend_time.items():
                if len(value) > 0:
                    sdt_dev, average, fastest, slowest = self.calculate_squared_diffs(value)
                    info_str = (f'消息接收情况：\n样本数：{len(self.receive_msg_count)}\t{key}：平均耗时：{average} ms，'
                               f'最快耗时：{fastest} ms，最慢耗时：{slowest} ms，耗时标准差：{sdt_dev}')
                    self.receive_msg_spend_time_list.append(info_str)
                    
                    # 添加到统计数据
                    receive_stats.append({
                        "主题": key,
                        "样本数": len(self.receive_msg_count),
                        "平均耗时(ms)": average,
                        "最快耗时(ms)": fastest,
                        "最慢耗时(ms)": slowest,
                        "标准差": sdt_dev
                    })
            
            return sub_stats, receive_stats
            
        except Exception as e:
            self.logger.error(f"计算订阅耗时统计时出错: {e}")
            # 发生错误时返回空列表
            return [], []

    def generate_final_report(self):
        """生成最终测试报告"""
        self.logger.info("性能测试结束，生成最终报告...")

        # 连接耗时
        self.conn_time_std_dev, self.avg_connect_time, self.min_connect_time, self.max_connect_time = self.calculate_squared_diffs(self.connect_elapsed_time)
        
        self.logger.info(
            f"平均连接速度：{self.avg_connect_time} ms，最快连接时间：{self.min_connect_time} ms，最慢连接时间：{self.max_connect_time} ms， 连接标准差：{self.conn_time_std_dev}"
        )

        # 消息丢失计算
        loss_info = self.calculate_message_loss()

        # 发送和接收消息统计
        with publish_msg_lock, receive_msg_lock:
            self.logger.info(
                f"发送的消息数量：{len(self.publish_msg_count)}，接收到的消息数量：{len(self.receive_msg_count)}")
            self.logger.info(f"消息丢失率：{loss_info['loss_rate']:.2f}%，丢失消息数：{loss_info['lost_messages']}")

        # 连接可靠性统计
        self.logger.info(
            f"连接失败次数：{self.connection_failures}，断开连接次数：{self.disconnections}，重连次数：{self.reconnections}")

        # QoS统计
        self.logger.info(
            f"QoS {self.config['qos_level']} 成功发布：{self.qos_success[self.config['qos_level']]}，失败：{self.qos_failure[self.config['qos_level']]}")

        # 延迟分布
        self.logger.info("消息延迟分布：")
        for bucket, count in self.latency_buckets.items():
            self.logger.info(f"  {bucket}: {count} 条消息")

        # 订阅和接收消息耗时
        sub_stats, receive_stats = self.calculate_sub_spendtime()
        
        # 保存统计数据供Excel报告使用
        self.sub_performance_stats = sub_stats
        self.receive_performance_stats = receive_stats

        for item in self.sub_spend_time_list:
            self.logger.info(item)

        for item in self.receive_msg_spend_time_list:
            self.logger.info(item)

        self.logger.info("性能测试完成！")

    def generate_excel_report(self):
        """生成Excel格式的性能报告"""
        try:
            self.logger.info("正在生成Excel格式报告...")

            # 确保存在报告目录
            if not os.path.exists(self.config["excel_report_dir"]):
                os.makedirs(self.config["excel_report_dir"])

            # 创建时间戳用于文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 设置报告文件路径
            report_path = os.path.join(self.config["excel_report_dir"], f"mqtt_perf_report_{timestamp}.xlsx")

            # 计算测试总时长
            test_duration = 0
            if self.test_start_time:
                test_duration = (datetime.now() - self.test_start_time).total_seconds()

            # 活动连接数
            active_connections = max(0, len(self.connect_elapsed_time) - self.disconnections)

            # 计算订阅者和发布者数量
            subscribers_count = len(self.subscribers)
            publishers_count = len(self.publishers)
            heartbeats_count = len(self.heartbeats)

            self.logger.info(f"订阅者: {subscribers_count}, 发布者: {publishers_count}, 心跳: {heartbeats_count}")

            # 消息统计
            receive_msg_count = len(self.receive_msg_count)
            publish_msg_count = len(self.publish_msg_count)

            self.logger.info(f"接收消息统计: 原始计数={receive_msg_count}")

            # 计算消息速率
            receive_rate = receive_msg_count / test_duration if test_duration > 0 else 0
            publish_rate = publish_msg_count / test_duration if test_duration > 0 else 0

            # 消息丢失计算
            loss_data = self.calculate_message_loss()

            # 创建概览数据框
            overview_data = {
                "测试指标": [
                    "测试开始时间",
                    "测试持续时间",
                    "发布消息总数",
                    "接收消息总数",
                    "消息丢失率",
                    "发布速率 (消息/秒)",
                    "接收速率 (消息/秒)",
                    "活动连接数",
                    "连接失败次数",
                    "断开连接次数",
                    "重连次数",
                    "QoS 0 成功率",
                    "QoS 1 成功率",
                    "QoS 2 成功率"
                ],
                "值": [
                    self.test_start_time.strftime("%Y-%m-%d %H:%M:%S") if self.test_start_time else "未记录",
                    f"{test_duration:.2f}秒",
                    publish_msg_count,
                    receive_msg_count,
                    f"{loss_data['loss_rate']:.2f}%",
                    f"{publish_rate:.2f}",
                    f"{receive_rate:.2f}",
                    active_connections,
                    self.connection_failures,
                    self.disconnections,
                    self.reconnections,
                    f"{self.calculate_qos_success_rate(0):.2f}%",
                    f"{self.calculate_qos_success_rate(1):.2f}%",
                    f"{self.calculate_qos_success_rate(2):.2f}%"
                ]
            }

            overview_df = pd.DataFrame(overview_data)

            # 计算连接性能数据
            connect_times = []
            for client_id, start_time in self.connection_times.items():
                if start_time > 0:  # 有效的开始时间
                    connect_time = self.connect_elapsed_time[client_id] if client_id in self.connect_elapsed_time else 0
                    connect_times.append(connect_time)

            # 如果存在连接时间数据
            if connect_times:
                # 计算标准差
                avg_connect_time = sum(connect_times) / len(connect_times)
                conn_time_variance = sum((x - avg_connect_time) ** 2 for x in connect_times) / len(connect_times) if len(connect_times) > 1 else 0
                conn_time_std_dev = conn_time_variance ** 0.5
                
                conn_data = pd.DataFrame({
                    "连接指标": ["最小连接时间", "最大连接时间", "平均连接时间", "连接标准差", "总连接尝试次数", "成功连接次数"],
                    "值": [
                        f"{min(connect_times):.2f}秒" if connect_times else "N/A",
                        f"{max(connect_times):.2f}秒" if connect_times else "N/A",
                        f"{sum(connect_times) / len(connect_times):.2f}秒" if connect_times else "N/A",
                        f"{conn_time_std_dev:.2f}秒" if conn_time_std_dev else "N/A",
                        len(self.connection_times),
                        len(connect_times)
                    ]
                })
            else:
                conn_data = pd.DataFrame({
                    "连接指标": ["最小连接时间", "最大连接时间", "平均连接时间", "总连接尝试次数", "成功连接次数"],
                    "值": ["N/A", "N/A", "N/A", len(self.connection_times), 0]
                })

            # 接收消息性能数据
            receive_times = []
            for topic, times in self.receive_msg_spend_time.items():
                receive_times.extend(times)

            if receive_times:
                receive_data = pd.DataFrame({
                    "接收指标": ["最小接收延迟", "最大接收延迟", "平均接收延迟", "总接收消息数"],
                    "值": [
                        f"{min(receive_times):.2f}毫秒" if receive_times else "N/A",
                        f"{max(receive_times):.2f}毫秒" if receive_times else "N/A",
                        f"{sum(receive_times) / len(receive_times):.2f}毫秒" if receive_times else "N/A",
                        len(self.receive_msg_count)
                    ]
                })
            else:
                receive_data = pd.DataFrame({
                    "接收指标": ["最小接收延迟", "最大接收延迟", "平均接收延迟", "总接收消息数"],
                    "值": ["N/A", "N/A", "N/A", len(self.receive_msg_count)]
                })

            # 发布消息性能数据
            publish_data = pd.DataFrame({
                "发布指标": ["总发布消息数", "发布速率"],
                "值": [
                    len(self.publish_msg_count),
                    f"{publish_rate:.2f}消息/秒"
                ]
            })

            # 消息丢失统计数据
            loss_data_df = pd.DataFrame({
                "丢失指标": [
                    "发布消息数",
                    "接收消息数",
                    "丢失消息数",
                    "丢失率",
                    "发送的唯一ID数",
                    "接收的唯一ID数",
                    "根据ID丢失数",
                    "根据ID丢失率"
                ],
                "值": [
                    loss_data["total_published"],
                    loss_data["total_received"],
                    loss_data["lost_messages"],
                    f"{loss_data['loss_rate']:.2f}%",
                    loss_data["sent_ids_count"],
                    loss_data["received_ids_count"],
                    loss_data["lost_messages_by_id"],
                    f"{loss_data['loss_rate_by_id']:.2f}%"
                ]
            })

            # 延迟分布数据
            latency_list = []
            for bucket, count in self.latency_buckets.items():
                latency_list.append({"延迟范围": bucket, "消息数": count})

            latency_df = pd.DataFrame(latency_list)

            # 系统资源使用数据
            if hasattr(self, 'resource_data') and self.resource_data:  # 先检查属性是否存在，再检查是否为空
                resource_df = pd.DataFrame(self.resource_data)
                # 确保列名正确设置
                if len(resource_df.columns) >= 5:  # 确保至少有预期的5列
                    resource_df.columns = ["时间", "CPU使用率(%)", "内存使用率(%)", "网络发送(KB)", "网络接收(KB)"]
                    # 转换为字符串避免类型问题
                    resource_df["CPU使用率(%)"] = resource_df["CPU使用率(%)"].apply(lambda x: f"{float(x):.1f}")
                    resource_df["内存使用率(%)"] = resource_df["内存使用率(%)"].apply(lambda x: f"{float(x):.1f}")
                    resource_df["网络发送(KB)"] = resource_df["网络发送(KB)"].apply(lambda x: f"{float(x):.2f}")
                    resource_df["网络接收(KB)"] = resource_df["网络接收(KB)"].apply(lambda x: f"{float(x):.2f}")
                
                    # 创建Excel报告
                    with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                        overview_df.to_excel(writer, sheet_name='测试概述', index=False)
                        conn_data.to_excel(writer, sheet_name='连接性能', index=False)
                        receive_data.to_excel(writer, sheet_name='消息接收性能', index=False)
                        publish_data.to_excel(writer, sheet_name='消息发布性能', index=False)
                        loss_data_df.to_excel(writer, sheet_name='消息丢失统计', index=False)
                        latency_df.to_excel(writer, sheet_name='延迟分布', index=False)
                        resource_df.to_excel(writer, sheet_name='系统资源使用', index=False)  # 确保这一行存在
                
                # 添加主题订阅和接收性能工作表（如果这些属性存在）
                if hasattr(self, 'sub_performance_stats') and self.sub_performance_stats:
                    sub_df = pd.DataFrame(self.sub_performance_stats)
                    sub_df.to_excel(writer, sheet_name='订阅性能详情', index=False)
                    
                if hasattr(self, 'receive_performance_stats') and self.receive_performance_stats:
                    receive_df = pd.DataFrame(self.receive_performance_stats)
                    receive_df.to_excel(writer, sheet_name='接收性能详情', index=False)
                else:
                    self.logger.warning(f"没有订阅或接收性能数据，将跳过这些数据写入")
            else:
                self.logger.warning("没有资源使用数据，将跳过资源数据写入")
                # 创建Excel报告（不包含资源数据）
                with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                    overview_df.to_excel(writer, sheet_name='测试概述', index=False)
                    conn_data.to_excel(writer, sheet_name='连接性能', index=False)
                    receive_data.to_excel(writer, sheet_name='消息接收性能', index=False)
                    publish_data.to_excel(writer, sheet_name='消息发布性能', index=False)
                    loss_data_df.to_excel(writer, sheet_name='消息丢失统计', index=False)
                    latency_df.to_excel(writer, sheet_name='延迟分布', index=False)

            self.logger.info(f"Excel报告已生成: {report_path}")
            return report_path

        except Exception as e:
            self.logger.error(f"生成Excel报告出错: {e}")
            traceback.print_exc()

            # 备份报告逻辑仍保持
            try:
                # 确保timestamp已定义
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                simple_report_path = os.path.join(self.config["excel_report_dir"], f"simple_report_{timestamp}.xlsx")

                simple_data = pd.DataFrame({
                    "报告项目": ["测试日期", "测试持续时间", "总消息数"],
                    "值": [
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        f"{(datetime.now() - self.test_start_time).total_seconds():.2f}秒" if self.test_start_time else "N/A",
                        len(self.publish_msg_count)
                    ]
                })

                simple_data.to_excel(simple_report_path, index=False)
                self.logger.info(f"简化报告已生成: {simple_report_path}")
                return simple_report_path

            except Exception as e2:
                self.logger.error(f"生成简化报告也失败: {e2}")
                return None

    def calculate_message_loss(self):
        """计算消息丢失率"""
        total_published = len(self.publish_msg_count)
        total_received = len(self.receive_msg_count)

        # 基于消息计数的丢失率
        lost_messages = max(0, total_published - total_received)
        loss_rate = (lost_messages / total_published * 100) if total_published > 0 else 0

        # 确保必要的属性存在
        if not hasattr(self, 'message_ids'):
            self.message_ids = {}
        if not hasattr(self, 'received_ids'):
            self.received_ids = set()
        
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
        try:
            with message_tracking_lock:
                if is_sent:
                    # 记录发送的消息ID和发送时间
                    self.message_ids[message_id] = ("sent", time.time())
                else:
                    # 记录接收到的消息ID
                    self.received_ids.add(message_id)
                    # 更新消息状态为已接收
                    if message_id in self.message_ids:
                        self.message_ids[message_id] = ("received", time.time())
        except Exception as e:
            self.logger.error(f"跟踪消息时出错: {e}")

    def on_log(self, client, userdata, level, buf, properties=None):
        """记录MQTT客户端库的日志"""
        if level == mqtt.MQTT_LOG_ERR:
            self.logger.error(f"MQTT错误 ({userdata['client_id']}): {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.logger.warning(f"MQTT警告 ({userdata['client_id']}): {buf}")
        # 调试级别的日志太多，仅在需要时启用
        # elif level == mqtt.MQTT_LOG_DEBUG:
        #     self.logger.debug(f"MQTT调试 ({userdata['client_id']}): {buf}")

    def generate_performance_report(self):
        """生成性能报告"""
        try:
            # 计算测试持续时间
            test_duration = time.time() - self.test_start_time
            
            # 计算实际的发布开始和结束时间
            publish_start_time = min(self.publish_msg_time.values()) if self.publish_msg_time else self.test_start_time
            publish_end_time = max(self.publish_msg_time.values()) if self.publish_msg_time else time.time()
            publish_duration = publish_end_time - publish_start_time if publish_start_time < publish_end_time else test_duration
            
            # 计算实际的接收开始和结束时间
            receive_start_time = min(self.receive_msg_time.values()) if self.receive_msg_time else self.test_start_time
            receive_end_time = max(self.receive_msg_time.values()) if self.receive_msg_time else time.time()
            receive_duration = receive_end_time - receive_start_time if receive_start_time < receive_end_time else test_duration
            
            # 使用对应的时间段计算实际速率
            publish_count = len(self.publish_msg_count)
            receive_count = len(self.receive_msg_count)
            
            publish_rate = publish_count / publish_duration if publish_duration > 0 else 0
            receive_rate = receive_count / receive_duration if receive_duration > 0 else 0
            
            # 计算连接时间的统计信息
            conn_time_std_dev = 0
            conn_time_variance = 0
            if self.connect_elapsed_time:
                if len(self.connect_elapsed_time) > 1:
                    conn_time_variance = sum((x - self.avg_connect_time) ** 2 for x in self.connect_elapsed_time) / len(self.connect_elapsed_time)
                    conn_time_std_dev = conn_time_variance ** 0.5
            
            # 计算主题性能的统计信息
            topic_stats = {}
            for topic, latencies in self.receive_msg_spend_time.items():
                if latencies:
                    avg_latency = sum(latencies) / len(latencies)
                    min_latency = min(latencies)
                    max_latency = max(latencies)
                    
                    # 计算方差和标准差
                    variance = sum((x - avg_latency) ** 2 for x in latencies) / len(latencies) if len(latencies) > 1 else 0
                    std_dev = variance ** 0.5
                    
                    topic_stats[topic] = {
                        "消息数": len(latencies),
                        "平均延迟(ms)": round(avg_latency, 2),
                        "最小延迟(ms)": round(min_latency, 2),
                        "最大延迟(ms)": round(max_latency, 2),
                        "方差": round(variance, 2),
                        "标准差": round(std_dev, 2)
                    }
            
            # 计算消息丢失率
            message_loss_rate = 0
            if publish_count > 0:
                message_loss_rate = ((publish_count - receive_count) / publish_count) * 100
            
            # 生成报告
            report = {
                "测试开始时间": datetime.fromtimestamp(self.test_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                "测试持续时间(秒)": round(test_duration, 2),
                "发布消息总数": publish_count,
                "接收消息总数": receive_count,
                "消息丢失率": f"{message_loss_rate:.2f}%",
                "发布速率 (消息/秒)": round(publish_rate, 2),
                "接收速率 (消息/秒)": round(receive_rate, 2),
                "连接总数": len(self.connect_elapsed_time),
                "连接失败次数": self.connection_failures,
                "断开连接次数": self.disconnections,
                "QoS 0 成功率": f"{(self.qos_success.get(0, 0) / (self.qos_success.get(0, 0) + self.qos_failure.get(0, 0)) * 100) if (self.qos_success.get(0, 0) + self.qos_failure.get(0, 0)) > 0 else 0:.2f}%",
                "QoS 1 成功率": f"{(self.qos_success.get(1, 0) / (self.qos_success.get(1, 0) + self.qos_failure.get(1, 0)) * 100) if (self.qos_success.get(1, 0) + self.qos_failure.get(1, 0)) > 0 else 0:.2f}%",
                "QoS 2 成功率": f"{(self.qos_success.get(2, 0) / (self.qos_success.get(2, 0) + self.qos_failure.get(2, 0)) * 100) if (self.qos_success.get(2, 0) + self.qos_failure.get(2, 0)) > 0 else 0:.2f}%",
                "平均连接时间(毫秒)": round(self.avg_connect_time, 2) if self.avg_connect_time else 0,
                "连接时间方差": round(conn_time_variance, 2),
                "连接时间标准差": round(conn_time_std_dev, 2),
                "最小连接时间(毫秒)": round(self.min_connect_time, 2) if self.min_connect_time < float('inf') else 0,
                "最大连接时间(毫秒)": round(self.max_connect_time, 2) if self.max_connect_time > 0 else 0
            }
            
            # 打印主要性能指标
            print("\n============ MQTT性能测试报告 ============")
            for key, value in report.items():
                print(f"{key:<20} {value}")
            
            # 打印主题性能统计
            if topic_stats:
                print("\n============ 主题性能统计 ============")
                for topic, stats in topic_stats.items():
                    print(f"\n主题: {topic}")
                    for metric, value in stats.items():
                        print(f"{metric:<20} {value}")
            
            # 打印延迟分布
            print("\n============ 延迟分布 ============")
            total_messages = sum(self.latency_buckets.values())
            for bucket, count in self.latency_buckets.items():
                percentage = (count / total_messages) * 100 if total_messages > 0 else 0
                print(f"{bucket:<15} {count:<8} ({percentage:.2f}%)")
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成性能报告时出错: {e}")
            traceback.print_exc()
            return {}

    def generate_report(self):
        """生成测试报告"""
        try:
            # 计算测试时长
            if self.test_start_time:
                test_duration = (datetime.now() - self.test_start_time).total_seconds()
            else:
                test_duration = 0
            
            # 准备报告数据
            report_data = {
                "测试指标": ["值"],
                "测试开始时间": [self.test_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.test_start_time else 'N/A'],
                "测试持续时间": [f"{test_duration:.2f}秒"],
                "发布消息总数": [len(self.publish_msg_count)],
                "接收消息总数": [len(self.receive_msg_count)],
                "消息丢失率": [f"{(1 - len(self.receive_msg_count) / max(1, len(self.publish_msg_count))) * 100:.2f}%"],
                "发布速率 (消息/秒)": [f"{len(self.publish_msg_count) / max(1, test_duration):.2f}"],
                "接收速率 (消息/秒)": [f"{len(self.receive_msg_count) / max(1, test_duration):.2f}"],
                "活动连接数": [len(self.connect_elapsed_time)],
                "连接失败次数": [self.connection_failures],
                "断开连接次数": [self.disconnections],
                "重连次数": [self.reconnections]
            }
            
            # 添加QoS成功率
            for qos in sorted(self.qos_success.keys()):
                total = self.qos_success[qos] + self.qos_failure[qos]
                if total > 0:
                    success_rate = (self.qos_success[qos] / total) * 100
                else:
                    success_rate = 0
                report_data[f"QoS {qos} 成功率"] = [f"{success_rate:.2f}%"]
            
            # 打印报告
            print("\n=========== MQTT性能测试报告 ===========")
            for key, value in report_data.items():
                print(f"{key}: {value[0]}")
            
            # 打印连接指标
            print("\n=========== 连接指标 ===========")
            print(f"最小连接时间: {self.min_connect_time:.2f}毫秒")
            print(f"最大连接时间: {self.max_connect_time:.2f}毫秒")
            print(f"平均连接时间: {self.avg_connect_time:.2f}毫秒")
            print(f"总连接数: {len(self.connect_elapsed_time)}")
            print(f"成功连接率: {(len(self.connect_elapsed_time) - self.connection_failures) / max(1, len(self.connect_elapsed_time)) * 100:.2f}%")
            
            # 打印延迟分布
            print("\n=========== 延迟分布 ===========")
            total_messages = sum(self.latency_buckets.values())
            for bucket, count in self.latency_buckets.items():
                percentage = (count / total_messages) * 100 if total_messages > 0 else 0
                print(f"{bucket}: {count} ({percentage:.2f}%)")
            
            # 返回报告数据
            return report_data
            
        except Exception as e:
            self.logger.error(f"生成报告时出错: {e}")
            traceback.print_exc()
            return {}

    def run_test(self):
        """运行测试"""
        try:
            # 测试开始时间
            self.test_start_time = datetime.now()
            self.logger.info(f"测试开始时间: {self.test_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 重置测试状态和指标
            self.running = True
            self.test_ended = False
            self.subscribers = []
            self.publishers = []
            self.heartbeats = []
            
            # 重置消息计数器
            self.receive_msg_count = []
            self.publish_msg_count = []
            self.publish_msg_time = {}
            self.receive_msg_time = {}
            
            # 创建并启动资源监控线程
            monitor_thread = threading.Thread(target=self.monitor_resources)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # 创建订阅者
            self.logger.info(f"创建 {self.config['num_subscribers']} 个订阅者...")
            for i in range(self.config['num_subscribers']):
                client_id = f"conn_subscriber_{i}"
                client = self.create_mqtt_client(client_id, subscribe=True)
                if client:
                    self.subscribers.append(client)
                    self.logger.info(f"订阅者 {client_id} 已创建并订阅主题")
                    
            # 等待订阅者完成连接和订阅
            print("等待订阅者连接和订阅完成...")
            time.sleep(2)
            
            # 创建并启动发布者线程
            print(f"创建 {self.config['num_publishers']} 个发布者...")
            publish_threads = []
            
            for i in range(self.config['num_publishers']):
                client_id = f"conn_publisher_{i}"
                client = self.create_mqtt_client(client_id)
                
                if client:
                    self.publishers.append(client)
                    
                    # 确定发布主题 - 确保主题存在
                    if i < len(self.config["pub_topics"]):
                        pub_topic = self.config["pub_topics"][i]
                    else:
                        pub_topic = self.config["pub_topics"][0]  # 默认使用第一个主题
                    
                    thread = threading.Thread(
                        target=self.publish_messages,
                        args=(client, pub_topic, self.config.get("publish_interval", 1.0))
                    )
                    thread.daemon = True
                    thread.start()
                    publish_threads.append(thread)
                    
                    self.logger.info(f"发布者 {client_id} 已创建并开始发布消息到 {pub_topic}")
            
            # 等待测试完成
            test_duration = self.config.get("test_duration", 60)
            print(f"测试将运行 {test_duration} 秒...")
            
            start_time = time.time()
            while time.time() - start_time < test_duration and self.running:
                # 每5秒打印一次状态
                if int(time.time() - start_time) % 5 == 0:
                    with connection_stats_lock:
                        with publish_msg_lock:
                            with receive_msg_lock:
                                print(f"\n===== 测试状态 ({int(time.time() - start_time)}秒) =====")
                                print(f"活动连接: {len(self.connect_elapsed_time)}")
                                print(f"已发布消息: {len(self.publish_msg_count)}")
                                print(f"已接收消息: {len(self.receive_msg_count)}")
                                print("================================\n")
                time.sleep(1)
            
            # 测试完成
            self.running = False
            self.test_ended = True
            
            # 等待线程完成
            for thread in publish_threads:
                thread.join(timeout=2)
            
            # 断开连接
            self.disconnect_all_clients()
            
            # 生成报告
            report_data = self.generate_report()
            excel_path = self.save_excel_report()
            
            return report_data
            
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在安全终止测试...")
            print("\n测试被用户中断，正在生成中间报告...")
            
            # 标记测试停止
            self.running = False
            
            # 强制完成报告生成流程
            self.generate_final_report()  # 确保调用此方法生成最终报告
            self.generate_excel_report()  # 确保生成Excel报告
            
            # 清理资源
            self.cleanup()
            
            return {"状态": "已中断", "报告": "已生成中断状态报告"}
        
        except Exception as e:
            self.logger.error(f"运行测试时出错: {e}")
            traceback.print_exc()
            self.running = False
            self.test_ended = True
            return {}

    def print_progress(self):
        """打印当前测试进度"""
        try:
            pub_count = len(self.publish_msg_count)
            rec_count = len(self.receive_msg_count)
            
            # 计算测试时长
            if self.test_start_time:
                elapsed = (datetime.now() - self.test_start_time).total_seconds()
            else:
                elapsed = 0
            
            # 计算消息速率
            pub_rate = pub_count / max(1, elapsed)
            rec_rate = rec_count / max(1, elapsed)
            
            # 计算消息丢失率
            loss_rate = (1 - rec_count / max(1, pub_count)) * 100 if pub_count > 0 else 0
            
            print(f"\n===== 测试进度 ({elapsed:.1f}秒) =====")
            print(f"发布消息: {pub_count} ({pub_rate:.2f}/秒)")
            print(f"接收消息: {rec_count} ({rec_rate:.2f}/秒)")
            print(f"消息丢失率: {loss_rate:.2f}%")
            
            # 打印连接统计
            print(f"活动连接: {len(self.connect_elapsed_time)}")
            print(f"连接失败: {self.connection_failures}")
            print(f"断开连接: {self.disconnections}")
            print("============================\n")
            
        except Exception as e:
            self.logger.error(f"打印进度时出错: {e}")

    def disconnect_all_clients(self):
        """断开所有客户端连接"""
        try:
            # 断开所有订阅者
            for client in self.subscribers:
                try:
                    client.disconnect()
                    client.loop_stop()
                except:
                    pass
            
            # 断开所有发布者客户端
            for client in self.publishers:
                try:
                    client.disconnect()
                    client.loop_stop()
                except:
                    pass
            
            # 断开所有心跳客户端
            for client in self.heartbeats:
                try:
                    client.disconnect()
                    client.loop_stop()
                except:
                    pass
                
            self.logger.info("所有客户端已断开连接")
            
        except Exception as e:
            self.logger.error(f"断开客户端连接时出错: {e}")

    def save_excel_report(self):
        """将测试报告保存为Excel文件"""
        try:
            # 计算测试时长
            if self.test_start_time:
                test_duration = (datetime.now() - self.test_start_time).total_seconds()
            else:
                test_duration = 0
            
            # 确保报告目录存在
            report_dir = self.config.get("excel_report_dir", "reports")
            if not os.path.exists(report_dir):
                os.makedirs(report_dir)
            
            # 生成报告文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(report_dir, f"mqtt_perf_report_{timestamp}.xlsx")
            
            # 创建Excel写入器，使用ExcelWriter
            with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                # 1. 测试概况
                summary_data = {
                    "测试指标": [
                        "测试开始时间",
                        "测试持续时间",
                        "发布消息总数",
                        "接收消息总数",
                        "消息丢失率",
                        "发布速率 (消息/秒)",
                        "接收速率 (消息/秒)",
                        "活动连接数",
                        "连接失败次数",
                        "断开连接次数",
                        "重连次数"
                    ],
                    "值": [
                        self.test_start_time.strftime('%Y-%m-%d %H:%M:%S') if self.test_start_time else 'N/A',
                        f"{test_duration:.2f}秒",
                        len(self.publish_msg_count),
                        len(self.receive_msg_count),
                        f"{(1 - len(self.receive_msg_count) / max(1, len(self.publish_msg_count))) * 100:.2f}%",
                        f"{len(self.publish_msg_count) / max(1, test_duration):.2f}",
                        f"{len(self.receive_msg_count) / max(1, test_duration):.2f}",
                        len(self.connect_elapsed_time),
                        self.connection_failures,
                        self.disconnections,
                        self.reconnections
                    ]
                }
                
                # 添加QoS数据
                for qos in sorted(self.qos_success.keys()):
                    total = self.qos_success[qos] + self.qos_failure[qos]
                    if total > 0:
                        success_rate = (self.qos_success[qos] / total) * 100
                    else:
                        success_rate = 0
                    summary_data["测试指标"].append(f"QoS {qos} 成功率")
                    summary_data["值"].append(f"{success_rate:.2f}%")
                
                # 创建DataFrame并写入Excel
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='测试概况', index=False)
                
                # 2. 连接性能指标
                connection_data = {
                    "连接指标": [
                        "最小连接时间(毫秒)",
                        "最大连接时间(毫秒)",
                        "连接标准差(毫秒)",
                        "平均连接时间(毫秒)",
                        "总连接数",
                        "成功连接率"
                    ],
                    "值": [
                        f"{self.min_connect_time:.2f}",
                        f"{self.max_connect_time:.2f}",
                        f"{self.avg_connect_time:.2f}",
                        f"{self.conn_time_std_dev:.2f}",
                        len(self.connect_elapsed_time),
                        f"{(len(self.connect_elapsed_time) - self.connection_failures) / max(1, len(self.connect_elapsed_time)) * 100:.2f}%"
                    ]
                }
                connection_df = pd.DataFrame(connection_data)
                connection_df.to_excel(writer, sheet_name='连接性能', index=False)
                
                # 3. 延迟分布
                latency_data = {
                    "延迟区间": list(self.latency_buckets.keys()),
                    "消息数量": list(self.latency_buckets.values())
                }
                
                # 计算百分比
                total_messages = sum(self.latency_buckets.values())
                latency_data["百分比"] = [
                    f"{(count / total_messages) * 100:.2f}%" if total_messages > 0 else "0.00%" 
                    for count in self.latency_buckets.values()
                ]
                
                latency_df = pd.DataFrame(latency_data)
                latency_df.to_excel(writer, sheet_name='延迟分布', index=False)
                
                # 4. 主题性能统计（如果有）
                if self.receive_msg_spend_time:
                    topic_data = {
                        "主题": [],
                        "接收消息数": [],
                        "平均延迟(毫秒)": [],
                        "最小延迟(毫秒)": [],
                        "最大延迟(毫秒)": []
                    }
                    
                    for topic, latencies in self.receive_msg_spend_time.items():
                        if latencies:
                            topic_data["主题"].append(topic)
                            topic_data["接收消息数"].append(len(latencies))
                            topic_data["平均延迟(毫秒)"].append(f"{sum(latencies) / len(latencies):.2f}")
                            topic_data["最小延迟(毫秒)"].append(f"{min(latencies):.2f}")
                            topic_data["最大延迟(毫秒)"].append(f"{max(latencies):.2f}")
                    
                    if topic_data["主题"]:
                        topic_df = pd.DataFrame(topic_data)
                        topic_df.to_excel(writer, sheet_name='主题性能', index=False)
            
            self.logger.info(f"Excel报告已保存至: {report_path}")
            print(f"\n报告已保存至: {report_path}")
            
            return report_path
            
        except Exception as e:
            self.logger.error(f"生成Excel报告时出错: {e}")
            traceback.print_exc()
            return None

    def print_performance_summary(self):
        """打印性能摘要"""
        try:
            # 计算测试持续时间
            test_duration = time.time() - self.start_time
            
            # 计算连接时间的统计信息
            conn_time_std_dev = 0
            conn_time_variance = 0
            if self.connect_elapsed_time:
                if len(self.connect_elapsed_time) > 1:
                    conn_time_variance = sum((x - self.avg_connect_time) ** 2 for x in self.connect_elapsed_time) / len(self.connect_elapsed_time)
                    conn_time_std_dev = conn_time_variance ** 0.5
            
            # 打印摘要表格
            print("\n")
            print("=" * 60)
            print("MQTT性能测试摘要")
            print("=" * 60)
            
            # 基本信息表格
            print(f"{'测试开始时间':<20} {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'测试持续时间':<20} {test_duration:.2f}秒")
            print(f"{'发布消息总数':<20} {len(self.publish_msg_count)}")
            print(f"{'接收消息总数':<20} {len(self.receive_msg_count)}")
            
            # 计算消息丢失率
            loss_rate = ((len(self.publish_msg_count) - len(self.receive_msg_count)) / len(self.publish_msg_count) * 100) if len(self.publish_msg_count) > 0 else 0
            print(f"{'消息丢失率':<20} {loss_rate:.2f}%")
            
            # 计算消息速率
            publish_rate = len(self.publish_msg_count) / test_duration if test_duration > 0 else 0
            receive_rate = len(self.receive_msg_count) / test_duration if test_duration > 0 else 0
            print(f"{'发布速率':<20} {publish_rate:.2f} 消息/秒")
            print(f"{'接收速率':<20} {receive_rate:.2f} 消息/秒")
            
            # 连接统计
            print("\n" + "-" * 40)
            print("连接指标                值")
            print("-" * 40)
            print(f"{'最小连接时间(毫秒)':<20} {self.min_connect_time:.2f}")
            print(f"{'最大连接时间(毫秒)':<20} {self.max_connect_time:.2f}")
            print(f"{'平均连接时间(毫秒)':<20} {self.avg_connect_time:.2f}")
            print(f"{'连接时间方差':<20} {conn_time_variance:.2f}")
            print(f"{'连接时间标准差':<20} {conn_time_std_dev:.2f}")
            print(f"{'总连接数':<20} {len(self.connect_elapsed_time)}")
            
            conn_success_rate = (len(self.connect_elapsed_time) / (len(self.connect_elapsed_time) + self.connection_failures) * 100) if (len(self.connect_elapsed_time) + self.connection_failures) > 0 else 0
            print(f"{'连接成功率':<20} {conn_success_rate:.2f}%")
            
            # QoS统计
            print("\n" + "-" * 40)
            print("QoS指标                值")
            print("-" * 40)
            
            for qos in range(3):
                success = self.qos_success.get(qos, 0)
                failure = self.qos_failure.get(qos, 0)
                total = success + failure
                rate = (success / total * 100) if total > 0 else 0
                print(f"{'QoS ' + str(qos) + ' 成功率':<20} {rate:.2f}%")
            
            # 主题性能统计
            if self.receive_msg_spend_time:
                print("\n" + "-" * 60)
                print("主题性能统计")
                print("-" * 60)
                
                for topic, latencies in self.receive_msg_spend_time.items():
                    if latencies:
                        avg_latency = sum(latencies) / len(latencies)
                        min_latency = min(latencies)
                        max_latency = max(latencies)
                        
                        # 计算方差和标准差
                        variance = sum((x - avg_latency) ** 2 for x in latencies) / len(latencies) if len(latencies) > 1 else 0
                        std_dev = variance ** 0.5
                        
                        print(f"\n主题: {topic}")
                        print(f"{'消息数':<20} {len(latencies)}")
                        print(f"{'平均延迟(ms)':<20} {avg_latency:.2f}")
                        print(f"{'最小延迟(ms)':<20} {min_latency:.2f}")
                        print(f"{'最大延迟(ms)':<20} {max_latency:.2f}")
                        print(f"{'延迟方差':<20} {variance:.2f}")
                        print(f"{'延迟标准差':<20} {std_dev:.2f}")
            
            print("=" * 60)
            
        except Exception as e:
            self.logger.error(f"打印性能摘要时出错: {e}")
            traceback.print_exc()


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='MQTT性能测试工具')
    parser.add_argument('-c', '--config', help='配置文件路径')
    return parser.parse_args()


def main():
    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description='MQTT负载测试工具')
        parser.add_argument('-c', '--config', help='配置文件路径', default='config.json')
        args = parser.parse_args()

        # 创建并运行测试实例
        tester = MQTTLoadTester(config_file=args.config)
        tester.run_test()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断！正在尝试生成报告...")
        if 'tester' in locals():
            tester.running = False
            tester.generate_final_report()
            tester.generate_excel_report()
            tester.cleanup()
        print("中断处理完成，已尽可能生成报告。")
    except Exception as e:
        print(f"程序出现错误: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
