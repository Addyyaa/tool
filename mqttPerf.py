import ast
import math
import time
import paho.mqtt.client as mqtt
import threading
import random
import string
import logging
from colorama import Fore, Style, init

# 设置连接参数
BROKER = "139.224.192.36"  # MQTT Broker 地址
PORT = 1883  # 默认端口
USERNAME = "mqtttest"
PASSWORD = "mqtttest2022"
NUM_SUBSCRIBERS = 500  # 订阅用户数
NUM_PUBLISHERS = 10  # 发布用户数
NUM_HEARTBEATS = 500
SUB_TOPIC = [
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
]

PUB_TOPIC = [
    "/screen/magicframe/cloud/downloadpicture[-flat]/mf50"
]

HEARTBEAT = [
    "mf50/screen/cloud/screengroupstatus[-flat]/"
]

init(autoreset=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - Line %(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

connect_elapsed_time = []
connections_count = NUM_PUBLISHERS + NUM_SUBSCRIBERS
sub_spend_time = {}
sub_spend_time_list = []
for i in SUB_TOPIC:
    sub_spend_time[i] = []

receive_msg_spend_time = {}
receive_msg_spend_time_list = []
receive_msg_count = []


# 发布消息的功能
def publish_messages(client, pub_topic, interval=1, diy_msg=False):
    # print(f"{client._client_id} 发布主题：{pub_topic}")
    try:
        while True:
            # 随机生成消息
            if diy_msg:
                msg = diy_msg
            else:
                msg = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            # msg = f"{str(time.time())}\t" + msg
            msg = {
                "time": time.time(),
                "msg": msg
            }
            msg = str(msg)
            client.publish(pub_topic, msg)
            if "heart" in msg:
                logger.info(f"{client._client_id} 发布消息：{Fore.BLUE}{msg}{Style.RESET_ALL}, 主题：{pub_topic}")
            else:
                logger.info(f"{client._client_id} 发布消息：{msg}, 主题：{pub_topic}")
            time.sleep(int(interval))  # 每秒发布一次消息
    except Exception as e:
        logger.error(f"{client._client_id} 发布消息失败: {e}")


# 定义 MQTT 客户端连接函数
def conn_mqtt(client_id, subscribe=False):
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
    client.username_pw_set(USERNAME, PASSWORD)
    client.user_data_set({"subscribe": subscribe, "message_count": 0, "start_time": time.time(), "reconnected": False})

    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    for i in SUB_TOPIC:
        # i = client_id + i  # 若要获取每一个设备该主题下的消息接收情况则取消该注释
        receive_msg_spend_time[i] = []

    try:
        client.connect(BROKER, PORT)
        client.loop_start()

        # 订阅客户端连接时订阅主题
        if subscribe:
            for topic in SUB_TOPIC:
                topic = client._client_id.decode('utf-8') + topic
                client.subscribe(topic, qos=2)
                logger.info(f"==========>{client._client_id} 订阅主题：{topic}")
    except Exception as e:
        logger.error(f"MQTT 客户端 {client_id} 连接失败: {e}")

    return client


# 连接回调函数
def on_connect(client, userdata, flags, reason_code, properties):
    logger.info(f"{client._client_id} 连接成功，返回码: {reason_code}")
    if reason_code == mqtt.CONNACK_ACCEPTED:
        logger.info(f"MQTT 客户端 {client._client_id} 已连接")
        end_time = time.time()
        token_time = round((end_time - userdata['start_time']) * 1000, 2)
        connect_elapsed_time.append(token_time)
        logger.info(f"{client._client_id} 连接耗时：{token_time} ms")
        if userdata["subscribe"] and userdata["reconnected"]:
            userdata["reconnected"] = False
            for topic in SUB_TOPIC:
                topic = client._client_id.decode('utf-8') + topic
                client.subscribe(topic, qos=2)
                logger.info(f"==========>{client._client_id} 重新订阅主题：{topic}")


def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        logger.error(f"{client._client_id} 连接断开，返回码: {rc}")
    else:
        logger.info(f"{client._client_id} 正常断开连接")
    if properties:
        logger.error(f"断开连接时的属性: {properties}")
    userdata["reconnected"] = True


# 消息回调函数
def on_message(client, userdata, msg):
    timestamp = ast.literal_eval(msg.payload.decode('utf-8'))['time']
    end_time = time.time()
    spend_time = round((end_time - timestamp) * 1000, 2)
    key = msg.topic.replace(client._client_id.decode('utf-8'), '')
    # key = msg.topic   # 若要获取每一个设备该主题下的消息接收情况则使用该行代码
    receive_msg_spend_time[key].append(spend_time)
    receive_msg_count.append(1)
    logger.info(f"{client._client_id} 收到消息，耗时：{spend_time} ms：{msg.topic} 内容：{msg.payload.decode('utf-8')}")


def on_subscribe(client, userdata, mid, reason_code_list, properties):
    if "Granted" in str(reason_code_list[0]):
        logging.info(f"{client._client_id} 订阅成功，reason_code_list：{reason_code_list}, mid：{mid}")
        end_time = time.time()
        token_time = round((end_time - userdata['start_time']) * 1000, 2)
        if mid > 0 :
            sub_spend_time[SUB_TOPIC[mid - 1]].append(token_time)
        logger.info(f"{client._client_id} 订阅耗时：{token_time} ms")


# 启动多个发布和订阅客户端
def start_mqtt_clients():
    subscriber_threads = []
    publisher_threads = []

    # 启动订阅客户端
    for i in range(NUM_SUBSCRIBERS):
        client_id = f"conn_subscriber_{i + 1}"
        client = conn_mqtt(client_id, subscribe=True)

        # 启动订阅客户端线程
        sub_thread = threading.Thread(target=client.loop_start)
        sub_thread.daemon = True
        sub_thread.start()
        subscriber_threads.append(sub_thread)

    # 启动发布客户端
    for i in range(NUM_PUBLISHERS):
        client_id = f"conn_publisher_{i + 1}"
        pub_topic = f"conn_subscriber_{i + 1}" + PUB_TOPIC[0]
        client = conn_mqtt(client_id, subscribe=False)
        # 启动发布客户端线程
        pub_thread = threading.Thread(target=publish_messages, args=(client, pub_topic, 1))
        pub_thread.daemon = True  # 设置为守护线程，主程序退出时该线程会自动退出
        pub_thread.start()
        publisher_threads.append(pub_thread)

    # # 启动心跳报文发布客户端
    for i in range(NUM_HEARTBEATS):
        client_id = f"conn_heartbeat_{i + 1}"
        pub_topic = PUB_TOPIC[0] + f"conn_heartbeat_{i + 1}"
        client = conn_mqtt(client_id, subscribe=False)
        # 启动发布客户端线程
        pub_thread = threading.Thread(target=publish_messages, args=(client, pub_topic, 30, "心跳包"))
        pub_thread.daemon = True  # 设置为守护线程，主程序退出时该线程会自动退出
        pub_thread.start()
        publisher_threads.append(pub_thread)

    # 保持主线程活跃
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("性能测试结束")
        sdt_dev, average, fastest, slowest = calculate_squared_diffs(connect_elapsed_time)
        # 连接耗时
        logging.info(
            f"平均连接速度：{average} ms，最快连接时间：{fastest} ms，最慢连接时间：{slowest} ms， 连接标准差：{sdt_dev}")
        # 订阅耗时
        calculate_sub_spendtime()
        for i in sub_spend_time_list:
            print(i)
        for i in receive_msg_spend_time_list:
            print(i)
        # 等待所有线程结束
        for sub_thread in subscriber_threads:
            sub_thread.join()
        for pub_thread in publisher_threads:
            pub_thread.join()


def calculate_squared_diffs(connect_elapsed_time):
    if len(connect_elapsed_time) == 0:
        return 0
    fastest = min(connect_elapsed_time)
    slowest = max(connect_elapsed_time)
    mean_time = sum(connect_elapsed_time) / len(connect_elapsed_time)
    suqared_diffs = [(t - mean_time) ** 2 for t in connect_elapsed_time]
    if len(suqared_diffs) == 0:
        return 0
    variance = sum(suqared_diffs) / len(suqared_diffs)
    stddev = math.sqrt(variance)

    def save_2_decimal(num):
        return round(num, 2)

    return save_2_decimal(stddev), save_2_decimal(mean_time), save_2_decimal(fastest), save_2_decimal(slowest)


def calculate_sub_spendtime():
    for key, value in sub_spend_time.items():
        sdt_dev, average, fastest, slowest = calculate_squared_diffs(value)
        sub_spend_time_list.append(
            f'样本数：{NUM_SUBSCRIBERS}\t{key}：平均耗时：{average} ms，最快耗时：{fastest} ms，最慢耗时：{slowest} '
            f'ms，耗时标准差'
            f'：{sdt_dev}')
    for key, value in receive_msg_spend_time.items():
        if len(value) > 0:
            sdt_dev, average, fastest, slowest = calculate_squared_diffs(value)
            sub_spend_time_list.append(
                f'消息接收情况：\n样本数：{len(receive_msg_count)}\t{key}：平均耗时：{average} ms，最快耗时：{fastest} ms，最慢耗时：{slowest} '
                f'ms，耗时标准差'
                f'：{sdt_dev}')


if __name__ == "__main__":
    start_mqtt_clients()
