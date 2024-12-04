import time
import paho.mqtt.client as mqtt
import threading
import random
import string
import logging

# 设置连接参数
BROKER = "139.224.192.36"  # MQTT Broker 地址
PORT = 1883  # 默认端口
USERNAME = "mqtttest"
PASSWORD = "mqtttest2022"
NUM_SUBSCRIBERS = 1  # 订阅用户数
NUM_PUBLISHERS = 1  # 发布用户数
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - Line %(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)


# 发布消息的功能
def publish_messages(client, pub_topic, num):
    pub_topic = f'conn_subscriber_{str(num)}' + pub_topic
    # print(f"{client._client_id} 发布主题：{pub_topic}")
    try:
        while True:
            # 随机生成消息
            msg = ''.join(random.choices(string.ascii_letters + string.digits, k=100))
            client.publish(pub_topic, msg)
            # logger.info(f"{client._client_id} 发布消息：{msg}, 主题：{pub_topic}")
            time.sleep(1)  # 每秒发布一次消息
    except Exception as e:
        logger.error(f"{client._client_id} 发布消息失败: {e}")


# 定义 MQTT 客户端连接函数
def conn_mqtt(client_id, subscribe=False):
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
    client.username_pw_set(USERNAME, PASSWORD)
    client.user_data_set({"subscribe": subscribe})

    # 设置回调函数
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

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
        if userdata["subscribe"]:
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


# 消息回调函数
def on_message(client, userdata, msg):
    logger.info(f"{client._client_id} 收到消息：{msg.topic} 内容：{msg.payload.decode('utf-8')}")


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
        client = conn_mqtt(client_id, subscribe=False)

        # 启动发布客户端线程
        pub_thread = threading.Thread(target=publish_messages, args=(client, PUB_TOPIC[0], i + 1))
        pub_thread.daemon = True  # 设置为守护线程，主程序退出时该线程会自动退出
        pub_thread.start()
        publisher_threads.append(pub_thread)

    # 保持主线程活跃
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("性能测试结束")
        # 等待所有线程结束
        for sub_thread in subscriber_threads:
            sub_thread.join()
        for pub_thread in publisher_threads:
            pub_thread.join()


if __name__ == "__main__":
    start_mqtt_clients()
