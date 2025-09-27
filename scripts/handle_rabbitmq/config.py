"""
RabbitMQ 配置文件
包含连接信息和默认配置
"""

import os
from typing import Dict, Any

# RabbitMQ 连接配置
RABBITMQ_CONFIG = {
    "MQ_PROTOCOL": "amqp",
    "MQ_HOST": "121.36.7.32",
    "MQ_PORT": "5672",
    "MQ_USER": "ocean-ship",
    "MQ_PASS": "!d23oD@wree#",
    "MQ_VHOST": "ocean-prod",
}

# 默认队列配置
DEFAULT_QUEUE_CONFIG = {
    "durable": True,  # 队列持久化
    "exclusive": False,  # 非独占
    "auto_delete": False,  # 不自动删除
    "arguments": None
}

# 默认交换机配置
DEFAULT_EXCHANGE_CONFIG = {
    "durable": True,  # 交换机持久化
    "auto_delete": False,  # 不自动删除
    "internal": False,  # 不内部使用
    "arguments": None
}

# 消息配置
MESSAGE_CONFIG = {
    "delivery_mode": 2,  # 消息持久化
    "mandatory": False,  # 不强制路由
    "immediate": False,  # 不立即投递
    "priority": 0,  # 优先级
    "expiration": None,  # 过期时间
}

# 消费者配置
CONSUMER_CONFIG = {
    "no_ack": False,  # 需要确认
    "exclusive": False,  # 非独占
    "consumer_tag": None,  # 消费者标签
    "arguments": None,
    "callback": None,
    "prefetch_count": 1,  # 预取数量
    "prefetch_size": 0,  # 预取大小
    "global_qos": False,  # 全局QoS
}

def get_connection_url() -> str:
    """获取 RabbitMQ 连接 URL"""
    config = RABBITMQ_CONFIG
    return f"{config['MQ_PROTOCOL']}://{config['MQ_USER']}:{config['MQ_PASS']}@{config['MQ_HOST']}:{config['MQ_PORT']}/{config['MQ_VHOST']}"

def get_connection_params() -> Dict[str, Any]:
    """获取 RabbitMQ 连接参数"""
    config = RABBITMQ_CONFIG
    return {
        "host": config["MQ_HOST"],
        "port": int(config["MQ_PORT"]),
        "user": config["MQ_USER"],
        "password": config["MQ_PASS"],
        "virtual_host": config["MQ_VHOST"],
        "heartbeat": 600,  # 心跳间隔（秒）
        "blocked_connection_timeout": 300,  # 阻塞连接超时（秒）
        "connection_attempts": 3,  # 连接尝试次数
        "retry_delay": 2,  # 重试延迟（秒）
    }

def load_config_from_env() -> Dict[str, str]:
    """从环境变量加载配置（可选）"""
    env_config = {}
    for key in RABBITMQ_CONFIG.keys():
        env_value = os.getenv(key)
        if env_value:
            env_config[key] = env_value
    return env_config

# 常用队列名称（可根据需要修改）
QUEUE_NAMES = {
    "DEFAULT": "ocean.default",
    "HEAVY_OIL": "ocean.heavy_oil",
    "VESSEL_PERFORMANCE": "ocean.vessel_performance",
    "WEATHER_DATA": "ocean.weather_data",
    "TYPHOON_DATA": "ocean.typhoon_data",
    "SPIDER_DATA": "ocean.spider_data",
    "REPORT_DATA": "ocean.report_data",
}

# 常用交换机名称
EXCHANGE_NAMES = {
    "DIRECT": "ocean.direct",
    "TOPIC": "ocean.topic",
    "FANOUT": "ocean.fanout",
    "HEADERS": "ocean.headers",
}
