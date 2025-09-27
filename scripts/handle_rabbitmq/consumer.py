"""
RabbitMQ 消息消费者类
负责从 RabbitMQ 接收和处理消息
"""

import json
import logging
import signal
import sys
import threading
import time
import pika
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime
from connection import RabbitMQConnection, get_global_connection
from config import DEFAULT_QUEUE_CONFIG, CONSUMER_CONFIG, QUEUE_NAMES

# 配置日志
logger = logging.getLogger(__name__)


class MessageHandler:
    """消息处理器基类"""
    
    def handle(self, message: Any, properties: Dict[str, Any]) -> bool:
        """
        处理消息
        
        Args:
            message: 消息内容
            properties: 消息属性
            
        Returns:
            bool: 处理是否成功
        """
        raise NotImplementedError("子类必须实现 handle 方法")


class JsonMessageHandler(MessageHandler):
    """JSON 消息处理器"""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], bool]):
        """
        初始化 JSON 消息处理器
        
        Args:
            callback: 处理函数，接收解析后的 JSON 数据，返回处理结果
        """
        self.callback = callback
    
    def handle(self, message: str, properties: Dict[str, Any]) -> bool:
        """
        处理 JSON 消息
        
        Args:
            message: JSON 字符串消息
            properties: 消息属性
            
        Returns:
            bool: 处理是否成功
        """
        try:
            data = json.loads(message)
            return self.callback(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}, 消息: {message}")
            return False
        except Exception as e:
            logger.error(f"消息处理失败: {str(e)}")
            return False


class TextMessageHandler(MessageHandler):
    """文本消息处理器"""
    
    def __init__(self, callback: Callable[[str], bool]):
        """
        初始化文本消息处理器
        
        Args:
            callback: 处理函数，接收文本消息，返回处理结果
        """
        self.callback = callback
    
    def handle(self, message: str, properties: Dict[str, Any]) -> bool:
        """
        处理文本消息
        
        Args:
            message: 文本消息
            properties: 消息属性
            
        Returns:
            bool: 处理是否成功
        """
        try:
            return self.callback(message)
        except Exception as e:
            logger.error(f"消息处理失败: {str(e)}")
            return False


class RabbitMQConsumer:
    """RabbitMQ 消息消费者"""
    
    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        """
        初始化消费者
        
        Args:
            connection: RabbitMQ 连接对象，如果为 None 则使用全局连接
        """
        self.connection = connection or get_global_connection()
        self.channel = None
        self.is_consuming = False
        self.message_handlers: Dict[str, MessageHandler] = {}
        self.consumer_tag = None
        self._stop_event = threading.Event()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"接收到信号 {signum}，正在停止消费者...")
        self.stop_consuming()
    
    def _ensure_channel(self):
        """确保通道可用"""
        if not self.connection.ensure_connection():
            raise ConnectionError("RabbitMQ 连接不可用")
        self.channel = self.connection.get_channel()
    
    def set_message_handler(self, queue_name: str, handler: MessageHandler):
        """
        设置消息处理器
        
        Args:
            queue_name: 队列名称
            handler: 消息处理器
        """
        self.message_handlers[queue_name] = handler
    
    def set_json_handler(self, queue_name: str, callback: Callable[[Dict[str, Any]], bool]):
        """
        设置 JSON 消息处理器
        
        Args:
            queue_name: 队列名称
            callback: 处理函数
        """
        self.set_message_handler(queue_name, JsonMessageHandler(callback))
    
    def set_text_handler(self, queue_name: str, callback: Callable[[str], bool]):
        """
        设置文本消息处理器
        
        Args:
            queue_name: 队列名称
            callback: 处理函数
        """
        self.set_message_handler(queue_name, TextMessageHandler(callback))
    
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
    
    def _message_callback(self, channel, method, properties, body):
        """
        消息回调函数
        
        Args:
            channel: 通道对象
            method: 方法对象
            properties: 消息属性
            body: 消息体
        """
        try:
            queue_name = method.routing_key
            message = body.decode('utf-8')
            
            # 转换属性为字典
            props_dict = {
                'content_type': properties.content_type,
                'delivery_mode': properties.delivery_mode,
                'priority': properties.priority,
                'correlation_id': properties.correlation_id,
                'reply_to': properties.reply_to,
                'expiration': properties.expiration,
                'message_id': properties.message_id,
                'timestamp': properties.timestamp,
                'type': properties.type,
                'user_id': properties.user_id,
                'app_id': properties.app_id,
                'cluster_id': properties.cluster_id,
            }
            
            logger.info(f"接收到消息 from {queue_name}: {message[:100]}...")
            
            # 查找对应的处理器
            handler = self.message_handlers.get(queue_name)
            if handler:
                success = handler.handle(message, props_dict)
                if success:
                    # 确认消息
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"消息处理成功: {queue_name}")
                else:
                    # 拒绝消息（重新入队）
                    channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    logger.warning(f"消息处理失败，重新入队: {queue_name}")
            else:
                logger.warning(f"未找到队列 {queue_name} 的消息处理器")
                # 拒绝消息（不重新入队）
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                
        except Exception as e:
            logger.error(f"消息处理异常: {str(e)}")
            try:
                # 拒绝消息（重新入队）
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            except:
                pass
    
    def start_consuming(self, queue_name: str, consumer_config: Optional[Dict[str, Any]] = None,
                       auto_declare_queue: bool = True) -> bool:
        """
        开始消费消息
        
        Args:
            queue_name: 队列名称
            consumer_config: 消费者配置
            auto_declare_queue: 是否自动声明队列
            
        Returns:
            bool: 启动是否成功
        """
        try:
            self._ensure_channel()
            
            # 自动声明队列
            if auto_declare_queue:
                if not self.declare_queue(queue_name):
                    return False
            
            # 设置 QoS
            config = consumer_config or CONSUMER_CONFIG
            self.channel.basic_qos(
                prefetch_count=config.get('prefetch_count', 1),
                prefetch_size=config.get('prefetch_size', 0),
                global_qos=config.get('global_qos', False)
            )
            
            # 开始消费
            self.consumer_tag = self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._message_callback,
                auto_ack=config.get('no_ack', False),
                exclusive=config.get('exclusive', False),
                consumer_tag=config.get('consumer_tag', None),
                arguments=config.get('arguments', None)
            )
            
            self.is_consuming = True
            logger.info(f"开始消费队列 {queue_name}, consumer_tag: {self.consumer_tag}")
            return True
            
        except Exception as e:
            logger.error(f"启动消费失败 {queue_name}: {str(e)}")
            return False
    
    def start_consuming_multiple(self, queue_configs: List[Dict[str, Any]]) -> bool:
        """
        开始消费多个队列
        
        Args:
            queue_configs: 队列配置列表，每个配置包含 queue_name, consumer_config, auto_declare_queue
            
        Returns:
            bool: 启动是否成功
        """
        try:
            self._ensure_channel()
            
            for config in queue_configs:
                queue_name = config['queue_name']
                consumer_config = config.get('consumer_config')
                auto_declare_queue = config.get('auto_declare_queue', True)
                
                if not self.start_consuming(queue_name, consumer_config, auto_declare_queue):
                    logger.error(f"启动队列 {queue_name} 消费失败")
                    return False
            
            self.is_consuming = True
            logger.info(f"开始消费 {len(queue_configs)} 个队列")
            return True
            
        except Exception as e:
            logger.error(f"启动多队列消费失败: {str(e)}")
            return False
    
    def run(self):
        """运行消费者（阻塞模式）"""
        if not self.is_consuming:
            logger.error("消费者未启动，请先调用 start_consuming")
            return
        
        try:
            logger.info("消费者开始运行...")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("接收到中断信号，停止消费者...")
        except Exception as e:
            logger.error(f"消费者运行异常: {str(e)}")
        finally:
            self.stop_consuming()
    
    def run_with_timeout(self, timeout: Optional[int] = None):
        """
        运行消费者（带超时）
        
        Args:
            timeout: 超时时间（秒），None 表示无超时
        """
        if not self.is_consuming:
            logger.error("消费者未启动，请先调用 start_consuming")
            return
        
        try:
            logger.info(f"消费者开始运行 (超时: {timeout}秒)...")
            
            if timeout:
                # 使用 threading 实现超时
                import threading
                
                def timeout_handler():
                    time.sleep(timeout)
                    self.stop_consuming()
                
                timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
                timeout_thread.start()
            
            self.channel.start_consuming()
        except Exception as e:
            logger.error(f"消费者运行异常: {str(e)}")
        finally:
            self.stop_consuming()
    
    def stop_consuming(self):
        """停止消费"""
        if self.is_consuming and self.consumer_tag:
            try:
                self.channel.basic_cancel(self.consumer_tag)
                self.channel.stop_consuming()
                logger.info(f"消费者已停止: {self.consumer_tag}")
            except Exception as e:
                logger.error(f"停止消费者失败: {str(e)}")
        
        self.is_consuming = False
        self.consumer_tag = None
        self._stop_event.set()
    
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


# 业务特定的消费者类
class HeavyOilDataConsumer(RabbitMQConsumer):
    """重油数据消费者"""
    
    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        super().__init__(connection)
        self.set_json_handler(QUEUE_NAMES["HEAVY_OIL"], self._handle_heavy_oil_data)
    
    def _handle_heavy_oil_data(self, data: Dict[str, Any]) -> bool:
        """
        处理重油数据
        
        Args:
            data: 重油数据
            
        Returns:
            bool: 处理是否成功
        """
        try:
            vessel_id = data.get('vessel_id')
            fuel_data = data.get('data', {})
            
            logger.info(f"处理重油数据 - 船舶ID: {vessel_id}")
            logger.info(f"燃料数据: {fuel_data}")
            
            # 在这里添加具体的业务逻辑
            # 例如：保存到数据库、计算燃油消耗等
            
            return True
            
        except Exception as e:
            logger.error(f"处理重油数据失败: {str(e)}")
            return False


class VesselPerformanceConsumer(RabbitMQConsumer):
    """船舶性能数据消费者"""
    
    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        super().__init__(connection)
        self.set_json_handler(QUEUE_NAMES["VESSEL_PERFORMANCE"], self._handle_performance_data)
    
    def _handle_performance_data(self, data: Dict[str, Any]) -> bool:
        """
        处理船舶性能数据
        
        Args:
            data: 性能数据
            
        Returns:
            bool: 处理是否成功
        """
        try:
            vessel_id = data.get('vessel_id')
            performance_data = data.get('data', {})
            
            logger.info(f"处理船舶性能数据 - 船舶ID: {vessel_id}")
            logger.info(f"性能数据: {performance_data}")
            
            # 在这里添加具体的业务逻辑
            # 例如：更新性能指标、生成报告等
            
            return True
            
        except Exception as e:
            logger.error(f"处理船舶性能数据失败: {str(e)}")
            return False


class WeatherDataConsumer(RabbitMQConsumer):
    """天气数据消费者"""
    
    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        super().__init__(connection)
        self.set_json_handler(QUEUE_NAMES["WEATHER_DATA"], self._handle_weather_data)
    
    def _handle_weather_data(self, data: Dict[str, Any]) -> bool:
        """
        处理天气数据
        
        Args:
            data: 天气数据
            
        Returns:
            bool: 处理是否成功
        """
        try:
            weather_data = data.get('data', {})
            
            logger.info(f"处理天气数据: {weather_data}")
            
            # 在这里添加具体的业务逻辑
            # 例如：更新天气数据库、发送预警等
            
            return True
            
        except Exception as e:
            logger.error(f"处理天气数据失败: {str(e)}")
            return False
