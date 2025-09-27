"""
RabbitMQ 操作工具库

这是一个用于操作 RabbitMQ 的 Python 工具库，专为海洋船舶数据处理系统设计。

主要模块：
- config: 配置文件
- connection: 连接管理
- producer: 消息生产者
- consumer: 消息消费者
"""

from .config import (
    RABBITMQ_CONFIG,
    DEFAULT_QUEUE_CONFIG,
    DEFAULT_EXCHANGE_CONFIG,
    MESSAGE_CONFIG,
    CONSUMER_CONFIG,
    QUEUE_NAMES,
    EXCHANGE_NAMES,
    get_connection_url,
    get_connection_params
)

from .connection import (
    RabbitMQConnection,
    RabbitMQConnectionPool,
    get_global_connection,
    close_global_connection
)

from .producer import RabbitMQProducer

from .consumer import (
    RabbitMQConsumer,
    MessageHandler,
    JsonMessageHandler,
    TextMessageHandler,
    HeavyOilDataConsumer,
    VesselPerformanceConsumer,
    WeatherDataConsumer
)

__version__ = "1.0.0"
__author__ = "JiufangTech Team"
__description__ = "RabbitMQ operation toolkit for ocean vessel data processing"

__all__ = [
    # Config
    "RABBITMQ_CONFIG",
    "DEFAULT_QUEUE_CONFIG", 
    "DEFAULT_EXCHANGE_CONFIG",
    "MESSAGE_CONFIG",
    "CONSUMER_CONFIG",
    "QUEUE_NAMES",
    "EXCHANGE_NAMES",
    "get_connection_url",
    "get_connection_params",
    
    # Connection
    "RabbitMQConnection",
    "RabbitMQConnectionPool", 
    "get_global_connection",
    "close_global_connection",
    
    # Producer
    "RabbitMQProducer",
    
    # Consumer
    "RabbitMQConsumer",
    "MessageHandler",
    "JsonMessageHandler", 
    "TextMessageHandler",
    "HeavyOilDataConsumer",
    "VesselPerformanceConsumer",
    "WeatherDataConsumer",
]
