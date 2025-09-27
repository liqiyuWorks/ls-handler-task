# RabbitMQ 操作工具库

这是一个用于操作 RabbitMQ 的 Python 工具库，专为海洋船舶数据处理系统设计。支持消息发送、接收、队列管理等功能。

## 功能特性

- 🔗 **连接管理**: 自动重连、连接池、连接状态监控
- 📤 **消息发送**: 支持文本、JSON、批量消息发送
- 📥 **消息接收**: 支持多种消息处理器、自动确认机制
- 🏗️ **队列管理**: 自动声明队列、交换机、绑定关系
- 🔄 **业务集成**: 针对重油数据、船舶性能、天气数据等业务场景优化
- 🛡️ **错误处理**: 完善的异常处理和重试机制
- 📊 **监控支持**: 队列信息查询、连接状态监控

## 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `pika==1.3.2` - RabbitMQ Python 客户端

## 快速开始

### 1. 基本连接测试

```python
from connection import RabbitMQConnection

# 创建连接
connection = RabbitMQConnection()

# 测试连接
if connection.connect():
    print("连接成功!")
    connection.disconnect()
```

### 2. 发送消息

```python
from producer import RabbitMQProducer
from config import QUEUE_NAMES

# 创建生产者
producer = RabbitMQProducer()

# 发送简单消息
message = {"message": "Hello RabbitMQ!", "timestamp": "2024-01-01T12:00:00"}
success = producer.send_message(message, QUEUE_NAMES["DEFAULT"])

if success:
    print("消息发送成功!")
```

### 3. 接收消息

```python
from consumer import RabbitMQConsumer
from config import QUEUE_NAMES

# 创建消费者
consumer = RabbitMQConsumer()

# 设置消息处理器
def handle_message(message: str) -> bool:
    print(f"收到消息: {message}")
    return True

consumer.set_text_handler(QUEUE_NAMES["DEFAULT"], handle_message)

# 开始消费
if consumer.start_consuming(QUEUE_NAMES["DEFAULT"]):
    consumer.run()  # 阻塞运行
```

## 配置说明

### RabbitMQ 连接配置

在 `config.py` 中配置连接信息：

```python
RABBITMQ_CONFIG = {
    "MQ_PROTOCOL": "amqp",
    "MQ_HOST": "121.36.7.32",
    "MQ_PORT": "5672",
    "MQ_USER": "ocean-ship",
    "MQ_PASS": "!d23oD@wree#",
    "MQ_VHOST": "ocean-prod",
}
```

### 队列配置

```python
# 预定义队列名称
QUEUE_NAMES = {
    "DEFAULT": "ocean.default",
    "HEAVY_OIL": "ocean.heavy_oil",
    "VESSEL_PERFORMANCE": "ocean.vessel_performance",
    "WEATHER_DATA": "ocean.weather_data",
    "TYPHOON_DATA": "ocean.typhoon_data",
}
```

## 使用示例

### 业务场景示例

#### 1. 重油数据处理

```python
from producer import RabbitMQProducer

producer = RabbitMQProducer()

# 发送重油数据
fuel_data = {
    "vessel_id": "OCEAN_VESSEL_001",
    "fuel_type": "heavy_oil",
    "consumption_rate": 28.5,
    "temperature": 45.2,
    "density": 0.95
}

success = producer.send_heavy_oil_data("OCEAN_VESSEL_001", fuel_data)
```

#### 2. 船舶性能数据处理

```python
# 发送船舶性能数据
performance_data = {
    "speed": 12.5,
    "fuel_consumption": 25.3,
    "engine_rpm": 1200,
    "weather_condition": "good"
}

success = producer.send_vessel_performance_data("VESSEL_001", performance_data)
```

#### 3. 天气数据处理

```python
# 发送天气数据
weather_data = {
    "location": "Shanghai",
    "temperature": 22.5,
    "humidity": 65,
    "wind_speed": 15.2,
    "pressure": 1013.25
}

success = producer.send_weather_data(weather_data)
```

### 高级用法

#### 1. 批量消息发送

```python
messages = [
    {"id": 1, "data": "message 1"},
    {"id": 2, "data": "message 2"},
    {"id": 3, "data": "message 3"}
]

results = producer.send_batch_messages(messages, QUEUE_NAMES["DEFAULT"])
print(f"成功: {results['success']}, 失败: {results['failed']}")
```

#### 2. 交换机路由

```python
from config import EXCHANGE_NAMES

# 声明交换机
producer.declare_exchange(EXCHANGE_NAMES["TOPIC"], "topic")

# 发送路由消息
producer.send_message_to_exchange(
    data, 
    EXCHANGE_NAMES["TOPIC"], 
    "weather.alert.storm"
)
```

#### 3. 连接池使用

```python
from connection import RabbitMQConnectionPool

# 创建连接池
pool = RabbitMQConnectionPool(max_connections=5)

# 获取连接
conn = pool.get_connection()

# 使用连接...

# 归还连接
pool.return_connection(conn)

# 关闭所有连接
pool.close_all()
```

## 文件结构

```
handle_rabbitmq/
├── config.py          # 配置文件
├── connection.py      # 连接管理
├── producer.py        # 消息生产者
├── consumer.py        # 消息消费者
├── examples.py        # 使用示例
├── test_connection.py # 连接测试
├── requirements.txt   # 依赖文件
└── README.md         # 说明文档
```

## 测试

### 运行连接测试

```bash
python test_connection.py
```

测试包括：
- 连接测试
- 生产者测试
- 消费者测试
- 端到端测试

### 运行示例

```bash
python examples.py
```

## API 参考

### RabbitMQConnection

连接管理类，负责建立和维护 RabbitMQ 连接。

**主要方法：**
- `connect()` - 建立连接
- `disconnect()` - 断开连接
- `reconnect()` - 重新连接
- `is_connected()` - 检查连接状态
- `get_channel()` - 获取通道

### RabbitMQProducer

消息生产者类，负责发送消息。

**主要方法：**
- `send_message(message, queue_name)` - 发送消息到队列
- `send_message_to_exchange(message, exchange_name, routing_key)` - 发送消息到交换机
- `send_batch_messages(messages, queue_name)` - 批量发送消息
- `send_heavy_oil_data(vessel_id, fuel_data)` - 发送重油数据
- `send_vessel_performance_data(vessel_id, performance_data)` - 发送船舶性能数据
- `send_weather_data(weather_data)` - 发送天气数据

### RabbitMQConsumer

消息消费者类，负责接收和处理消息。

**主要方法：**
- `set_text_handler(queue_name, callback)` - 设置文本消息处理器
- `set_json_handler(queue_name, callback)` - 设置 JSON 消息处理器
- `start_consuming(queue_name)` - 开始消费消息
- `run()` - 运行消费者（阻塞）
- `run_with_timeout(timeout)` - 运行消费者（带超时）
- `stop_consuming()` - 停止消费

## 错误处理

库提供了完善的错误处理机制：

1. **连接错误**: 自动重连、连接状态监控
2. **消息发送错误**: 异常捕获、重试机制
3. **消息处理错误**: 消息确认、重新入队
4. **配置错误**: 参数验证、默认值处理

## 性能优化

1. **连接复用**: 支持连接池，避免频繁建立连接
2. **批量处理**: 支持批量发送消息
3. **异步处理**: 支持消息处理器的异步回调
4. **QoS 控制**: 支持消息预取数量控制

## 监控和调试

### 日志配置

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 队列信息查询

```python
# 获取队列信息
queue_info = producer.get_queue_info(queue_name)
print(f"消息数量: {queue_info['message_count']}")
print(f"消费者数量: {queue_info['consumer_count']}")
```

### 连接状态监控

```python
# 获取连接信息
info = connection.get_connection_info()
print(f"连接状态: {info['is_connected']}")
```

## 常见问题

### Q: 连接失败怎么办？
A: 检查网络连接、RabbitMQ 服务状态、用户名密码和虚拟主机配置。

### Q: 消息发送失败怎么办？
A: 检查队列是否存在、消息格式是否正确、RabbitMQ 服务是否正常。

### Q: 消息处理失败怎么办？
A: 检查消息处理器逻辑、异常处理机制、确认机制配置。

### Q: 如何提高性能？
A: 使用连接池、批量发送、调整 QoS 参数、优化消息处理器逻辑。

## 版本兼容性

- Python 3.7+
- RabbitMQ 3.7.17+
- pika 1.3.2

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个工具库。

## 联系方式

如有问题或建议，请联系开发团队。
