"""
RabbitMQ 消息生产者类
负责发送消息到 RabbitMQ
"""

import json
import logging
import time
import pika
from typing import Any, Dict, Optional, Union, List
from datetime import datetime
from connection import RabbitMQConnection, get_global_connection
from config import DEFAULT_QUEUE_CONFIG, DEFAULT_EXCHANGE_CONFIG, MESSAGE_CONFIG, QUEUE_NAMES, EXCHANGE_NAMES

# 配置日志
logger = logging.getLogger(__name__)


class RabbitMQProducer:
    """RabbitMQ 消息生产者"""
    
    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        """
        初始化生产者
        
        Args:
            connection: RabbitMQ 连接对象，如果为 None 则使用全局连接
        """
        self.connection = connection or get_global_connection()
        self.channel = None
        
    def _ensure_channel(self):
        """确保通道可用"""
        if not self.connection.ensure_connection():
            raise ConnectionError("RabbitMQ 连接不可用")
        self.channel = self.connection.get_channel()
    
    def declare_queue(self, queue_name: str, queue_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        声明队列
        
        Args:
            queue_name: 队列名称
            queue_config: 队列配置
            
        Returns:
            bool: 声明是否成功
        """
        try:
            self._ensure_channel()
            config = queue_config or DEFAULT_QUEUE_CONFIG
            
            result = self.channel.queue_declare(
                queue=queue_name,
                durable=config.get('durable', True),
                exclusive=config.get('exclusive', False),
                auto_delete=config.get('auto_delete', False),
                arguments=config.get('arguments', None)
            )
            
            logger.info(f"队列声明成功: {queue_name}, 消息数量: {result.method.message_count}")
            return True
            
        except Exception as e:
            logger.error(f"队列声明失败 {queue_name}: {str(e)}")
            return False
    
    def declare_exchange(self, exchange_name: str, exchange_type: str = 'direct', 
                        exchange_config: Optional[Dict[str, Any]] = None) -> bool:
        """
        声明交换机
        
        Args:
            exchange_name: 交换机名称
            exchange_type: 交换机类型 (direct, topic, fanout, headers)
            exchange_config: 交换机配置
            
        Returns:
            bool: 声明是否成功
        """
        try:
            self._ensure_channel()
            config = exchange_config or DEFAULT_EXCHANGE_CONFIG
            
            self.channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                durable=config.get('durable', True),
                auto_delete=config.get('auto_delete', False),
                internal=config.get('internal', False),
                arguments=config.get('arguments', None)
            )
            
            logger.info(f"交换机声明成功: {exchange_name} (类型: {exchange_type})")
            return True
            
        except Exception as e:
            logger.error(f"交换机声明失败 {exchange_name}: {str(e)}")
            return False
    
    def bind_queue_to_exchange(self, queue_name: str, exchange_name: str, routing_key: str = '') -> bool:
        """
        将队列绑定到交换机
        
        Args:
            queue_name: 队列名称
            exchange_name: 交换机名称
            routing_key: 路由键
            
        Returns:
            bool: 绑定是否成功
        """
        try:
            self._ensure_channel()
            
            self.channel.queue_bind(
                exchange=exchange_name,
                queue=queue_name,
                routing_key=routing_key
            )
            
            logger.info(f"队列绑定成功: {queue_name} -> {exchange_name} (routing_key: {routing_key})")
            return True
            
        except Exception as e:
            logger.error(f"队列绑定失败: {str(e)}")
            return False
    
    def send_message(self, message: Any, queue_name: str, 
                    message_config: Optional[Dict[str, Any]] = None,
                    declare_queue: bool = True) -> bool:
        """
        发送消息到指定队列
        
        Args:
            message: 要发送的消息
            queue_name: 队列名称
            message_config: 消息配置
            declare_queue: 是否自动声明队列
            
        Returns:
            bool: 发送是否成功
        """
        try:
            self._ensure_channel()
            
            # 自动声明队列
            if declare_queue:
                self.declare_queue(queue_name)
            
            # 准备消息
            if isinstance(message, (dict, list)):
                message_body = json.dumps(message, ensure_ascii=False)
                content_type = 'application/json'
            elif isinstance(message, str):
                message_body = message
                content_type = 'text/plain'
            else:
                message_body = str(message)
                content_type = 'text/plain'
            
            # 消息配置
            config = message_config or MESSAGE_CONFIG
            properties = pika.BasicProperties(
                content_type=content_type,
                delivery_mode=config.get('delivery_mode', 2),
                priority=config.get('priority', 0),
                expiration=config.get('expiration', None),
                timestamp=int(time.time()),
                message_id=f"{queue_name}_{int(time.time() * 1000)}"
            )
            
            # 发送消息
            self.channel.basic_publish(
                exchange='',  # 使用默认交换机
                routing_key=queue_name,
                body=message_body,
                properties=properties,
                mandatory=config.get('mandatory', False)
            )
            
            logger.info(f"消息发送成功到队列 {queue_name}: {message_body[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"消息发送失败到队列 {queue_name}: {str(e)}")
            return False
    
    def send_message_to_exchange(self, message: Any, exchange_name: str, routing_key: str,
                                message_config: Optional[Dict[str, Any]] = None,
                                declare_exchange: bool = True) -> bool:
        """
        发送消息到指定交换机
        
        Args:
            message: 要发送的消息
            exchange_name: 交换机名称
            routing_key: 路由键
            message_config: 消息配置
            declare_exchange: 是否自动声明交换机
            
        Returns:
            bool: 发送是否成功
        """
        try:
            self._ensure_channel()
            
            # 自动声明交换机
            if declare_exchange:
                self.declare_exchange(exchange_name)
            
            # 准备消息
            if isinstance(message, (dict, list)):
                message_body = json.dumps(message, ensure_ascii=False)
                content_type = 'application/json'
            elif isinstance(message, str):
                message_body = message
                content_type = 'text/plain'
            else:
                message_body = str(message)
                content_type = 'text/plain'
            
            # 消息配置
            config = message_config or MESSAGE_CONFIG
            properties = pika.BasicProperties(
                content_type=content_type,
                delivery_mode=config.get('delivery_mode', 2),
                priority=config.get('priority', 0),
                expiration=config.get('expiration', None),
                timestamp=int(time.time()),
                message_id=f"{exchange_name}_{routing_key}_{int(time.time() * 1000)}"
            )
            
            # 发送消息
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=message_body,
                properties=properties,
                mandatory=config.get('mandatory', False)
            )
            
            logger.info(f"消息发送成功到交换机 {exchange_name} (routing_key: {routing_key}): {message_body[:100]}...")
            return True
            
        except Exception as e:
            logger.error(f"消息发送失败到交换机 {exchange_name}: {str(e)}")
            return False
    
    def send_batch_messages(self, messages: List[Any], queue_name: str,
                           message_config: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
        """
        批量发送消息
        
        Args:
            messages: 消息列表
            queue_name: 队列名称
            message_config: 消息配置
            
        Returns:
            Dict[str, int]: 发送结果统计
        """
        results = {"success": 0, "failed": 0}
        
        for message in messages:
            if self.send_message(message, queue_name, message_config):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        logger.info(f"批量发送完成: 成功 {results['success']} 条, 失败 {results['failed']} 条")
        return results
    
    def send_heavy_oil_data(self, vessel_id: str, fuel_data: Dict[str, Any]) -> bool:
        """
        发送重油数据（业务特定方法）
        
        Args:
            vessel_id: 船舶ID
            fuel_data: 燃料数据
            
        Returns:
            bool: 发送是否成功
        """
        message = {
            "vessel_id": vessel_id,
            "timestamp": datetime.now().isoformat(),
            "data_type": "heavy_oil",
            "data": fuel_data
        }
        
        return self.send_message(message, QUEUE_NAMES["HEAVY_OIL"])
    
    def send_vessel_performance_data(self, vessel_id: str, performance_data: Dict[str, Any]) -> bool:
        """
        发送船舶性能数据（业务特定方法）
        
        Args:
            vessel_id: 船舶ID
            performance_data: 性能数据
            
        Returns:
            bool: 发送是否成功
        """
        message = {
            "vessel_id": vessel_id,
            "timestamp": datetime.now().isoformat(),
            "data_type": "vessel_performance",
            "data": performance_data
        }
        
        return self.send_message(message, QUEUE_NAMES["VESSEL_PERFORMANCE"])
    
    def send_weather_data(self, weather_data: Dict[str, Any]) -> bool:
        """
        发送天气数据（业务特定方法）
        
        Args:
            weather_data: 天气数据
            
        Returns:
            bool: 发送是否成功
        """
        message = {
            "timestamp": datetime.now().isoformat(),
            "data_type": "weather",
            "data": weather_data
        }
        
        return self.send_message(message, QUEUE_NAMES["WEATHER_DATA"])
    
    def send_typhoon_data(self, typhoon_data: Dict[str, Any]) -> bool:
        """
        发送台风数据（业务特定方法）
        
        Args:
            typhoon_data: 台风数据
            
        Returns:
            bool: 发送是否成功
        """
        message = {
            "timestamp": datetime.now().isoformat(),
            "data_type": "typhoon",
            "data": typhoon_data
        }
        
        return self.send_message(message, QUEUE_NAMES["TYPHOON_DATA"])
    
    def get_queue_info(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """
        获取队列信息
        
        Args:
            queue_name: 队列名称
            
        Returns:
            Dict[str, Any]: 队列信息，如果获取失败则返回 None
        """
        try:
            self._ensure_channel()
            
            result = self.channel.queue_declare(queue=queue_name, passive=True)
            
            return {
                "queue_name": queue_name,
                "message_count": result.method.message_count,
                "consumer_count": result.method.consumer_count,
            }
            
        except Exception as e:
            logger.error(f"获取队列信息失败 {queue_name}: {str(e)}")
            return None
