# MQTT性能测试工具

一个功能强大的MQTT性能测试工具，用于评估MQTT服务器的性能和可靠性指标，支持高并发连接、消息吞吐量测试与延迟分析。

## 目录

- [功能概述](#功能概述)

- [系统要求](#系统要求)

- [安装](#安装)

- [配置文件](#配置文件)

- [使用方法](#使用方法)

- [测试报告解读](#测试报告解读)

- [常见问题](#常见问题与故障排除)

- [高级用法](#高级用法)

- [最佳实践](#最佳实践)

## 功能概述

MQTT性能测试工具（mqttPerf）可以模拟大量客户端同时连接、发布和订阅消息，提供对MQTT服务器性能的全面分析，包括：

- 连接性能（建立速度、稳定性）

- 消息吞吐量（发布/订阅速率）

- 消息延迟（端到端传输时间）

- 服务质量（不同QoS级别的可靠性）

- 系统资源使用情况（CPU、内存）

## 系统要求

- Python 3.7+

- 依赖库：

  - paho-mqtt

  - pandas

  - openpyxl
  
  - psutil

  
## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/mqtt-performance-tool.git
cd mqtt-performance-tool

# 创建虚拟环境
python -m venv mqtt_test_env

# 激活虚拟环境
# Windows
mqtt_test_env\Scripts\activate
# Linux/Mac
source mqtt_test_env/bin/activate

# 安装依赖
pip install -r requirements.txt


## 配置文件

工具使用JSON格式的配置文件，默认为`config.json`：

```json
{
  "broker_host": "127.0.0.1",
  "broker_port": 1883,
  "username": "",
  "password": "",
  "client_id_prefix": "mqtt_perf_",
  "clean_session": true,
  "qos_level": 1,
  "num_subscribers": 10,
  "num_publishers": 10,
  "test_duration": 60,
  "sub_topics": ["/screen/magicframe/cloud/downloadpicture[-flat]/mf50"],
  "pub_topics": ["/screen/magicframe/cloud/downloadpicture[-flat]/mf50"],
  "message_size": 2048,
  "publish_interval": 1.0,
  "report_interval": 5,
  "excel_report_dir": "reports",
  "message_template": {
    "id": "${client_id}_${seq}",
    "type": "测试消息",
    "timestamp": "${timestamp}",
    "data": "${payload}"
  }
}
```


### 配置参数说明


| 参数 | 说明 |
|------|------|
| broker_host | MQTT代理地址 |
| broker_port | MQTT代理端口 |
| username | 用户名 |
| password | 密码 |
| client_id_prefix | 客户端ID前缀 |
| clean_session | 是否清理会话 |
| qos_level | QoS级别 |
| num_subscribers | 订阅者数量 |
| num_publishers | 发布者数量 |
| test_duration | 测试持续时间 |
| sub_topics | 订阅主题 |
| pub_topics | 发布主题 |
| message_size | 消息大小 |
| publish_interval | 发布间隔 |
| report_interval | 报告间隔 |
| excel_report_dir | 报告输出目录 |


## 使用方法


### 基本用法

```bash
python mqttPerf.py
```


### 指定配置文件

```bash
python mqttPerf.py -c custom_config.json
```


### 测试过程

测试开始后，工具会每隔固定时间显示当前状态：
===== 测试状态 (15秒) =====
活动连接: 20
已发布消息: 150
已接收消息: 148
================================


您可以随时按`Ctrl+C`中断测试，系统会生成中间报告。


### 报告解读

测试结束后，工具会生成详细的Excel报告，包含以下内容：

- 连接性能

- 消息吞吐量

- 消息延迟


## 高级用法

### 自定义消息内容

通过修改配置文件中的`message_template`：

```json
"message_template": {
  "id": "${client_id}_${seq}",
  "type": "测试消息",
  "timestamp": "${timestamp}",
  "data": "${payload}"
}
```

### 增加压力测试强度

逐步增加并发连接数和消息发布频率：

```json
"num_subscribers": 100,
"num_publishers": 50,
"publish_interval": 0.1
```

## 最佳实践

1. **渐进式测试**：从小规模开始，逐步增加测试负载
2. **多次测试**：进行多次测试并取平均值，提高结果可靠性
3. **模拟真实场景**：配置接近实际应用场景的参数
4. **监控服务器**：同时监控MQTT服务器的资源使用情况
5. **关注异常值**：特别注意延迟分布中的极端值

---

# requirements.txt
paho-mqtt>=1.6.1     # MQTT客户端库
pandas>=1.3.0        # 数据分析和Excel报告生成
openpyxl>=3.0.9      # Excel文件处理
psutil>=5.9.0        # 系统资源监控
matplotlib>=3.5.0    # 图表生成（可选，用于资源使用图表）
numpy>=1.20.0        # 科学计算库（pandas依赖）


