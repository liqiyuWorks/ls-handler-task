"""
RabbitMQ 连接管理类
负责建立和维护 RabbitMQ 连接
"""

import pika
import logging
import time
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from config import get_connection_params, RABBITMQ_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """RabbitMQ 连接管理类"""
    
    def __init__(self, connection_params: Optional[Dict[str, Any]] = None):
        """
        初始化 RabbitMQ 连接管理器
        
        Args:
            connection_params: 连接参数，如果为 None 则使用默认配置
        """
        self.connection_params = connection_params or get_connection_params()
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
        self._is_connected = False
        
    def connect(self) -> bool:
        """
        建立 RabbitMQ 连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"正在连接到 RabbitMQ: {self.connection_params['host']}:{self.connection_params['port']}")
            
            # 创建连接参数
            credentials = pika.PlainCredentials(
                self.connection_params['user'],
                self.connection_params['password']
            )
            
            connection_params = pika.ConnectionParameters(
                host=self.connection_params['host'],
                port=self.connection_params['port'],
                virtual_host=self.connection_params['virtual_host'],
                credentials=credentials,
                heartbeat=self.connection_params.get('heartbeat', 600),
                blocked_connection_timeout=self.connection_params.get('blocked_connection_timeout', 300),
                connection_attempts=self.connection_params.get('connection_attempts', 3),
                retry_delay=self.connection_params.get('retry_delay', 2),
            )
            
            # 建立连接
            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()
            self._is_connected = True
            
            logger.info("RabbitMQ 连接成功")
            return True
            
        except Exception as e:
            logger.error(f"RabbitMQ 连接失败: {str(e)}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """断开 RabbitMQ 连接"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
                
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                
            self._is_connected = False
            logger.info("RabbitMQ 连接已断开")
            
        except Exception as e:
            logger.error(f"断开 RabbitMQ 连接时出错: {str(e)}")
    
    def reconnect(self) -> bool:
        """
        重新连接 RabbitMQ
        
        Returns:
            bool: 重连是否成功
        """
        self.disconnect()
        time.sleep(1)  # 等待一秒再重连
        return self.connect()
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self._is_connected:
            return False
            
        try:
            # 检查连接是否有效
            if self.connection and self.connection.is_closed:
                self._is_connected = False
                return False
                
            if self.channel and self.channel.is_closed:
                self._is_connected = False
                return False
                
            return True
            
        except Exception:
            self._is_connected = False
            return False
    
    def get_channel(self) -> Optional[pika.channel.Channel]:
        """
        获取通道
        
        Returns:
            pika.channel.Channel: 通道对象，如果连接失败则返回 None
        """
        if not self.is_connected():
            if not self.connect():
                return None
                
        return self.channel
    
    def ensure_connection(self) -> bool:
        """
        确保连接有效，如果连接断开则自动重连
        
        Returns:
            bool: 连接是否有效
        """
        if not self.is_connected():
            logger.warning("连接已断开，尝试重新连接...")
            return self.connect()
        return True
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "host": self.connection_params['host'],
            "port": self.connection_params['port'],
            "virtual_host": self.connection_params['virtual_host'],
            "user": self.connection_params['user'],
            "is_connected": self.is_connected(),
            "connection_closed": self.connection.is_closed if self.connection else True,
            "channel_closed": self.channel.is_closed if self.channel else True,
        }
    
    @contextmanager
    def get_connection_context(self):
        """
        连接上下文管理器，自动管理连接的开启和关闭
        
        Usage:
            with rabbit_conn.get_connection_context() as channel:
                # 使用 channel 进行操作
                pass
        """
        try:
            if not self.ensure_connection():
                raise ConnectionError("无法建立 RabbitMQ 连接")
            yield self.channel
        except Exception as e:
            logger.error(f"连接上下文出错: {str(e)}")
            raise
        finally:
            # 注意：这里不自动断开连接，让用户手动管理
            pass
    
    def __enter__(self):
        """上下文管理器入口"""
        if not self.connect():
            raise ConnectionError("无法建立 RabbitMQ 连接")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()


class RabbitMQConnectionPool:
    """RabbitMQ 连接池（简单实现）"""
    
    def __init__(self, max_connections: int = 5, connection_params: Optional[Dict[str, Any]] = None):
        """
        初始化连接池
        
        Args:
            max_connections: 最大连接数
            connection_params: 连接参数
        """
        self.max_connections = max_connections
        self.connection_params = connection_params or get_connection_params()
        self.connections = []
        self.available_connections = []
        
    def get_connection(self) -> RabbitMQConnection:
        """获取一个可用连接"""
        if self.available_connections:
            return self.available_connections.pop()
        
        if len(self.connections) < self.max_connections:
            conn = RabbitMQConnection(self.connection_params)
            if conn.connect():
                self.connections.append(conn)
                return conn
        
        # 如果所有连接都在使用中，等待或创建新连接
        raise RuntimeError("连接池已满，无法获取连接")
    
    def return_connection(self, connection: RabbitMQConnection):
        """归还连接到池中"""
        if connection.is_connected():
            self.available_connections.append(connection)
        else:
            # 连接已断开，从池中移除
            if connection in self.connections:
                self.connections.remove(connection)
    
    def close_all(self):
        """关闭所有连接"""
        for conn in self.connections:
            conn.disconnect()
        self.connections.clear()
        self.available_connections.clear()


# 全局连接实例（可选）
_global_connection: Optional[RabbitMQConnection] = None

def get_global_connection() -> RabbitMQConnection:
    """获取全局连接实例"""
    global _global_connection
    if _global_connection is None or not _global_connection.is_connected():
        _global_connection = RabbitMQConnection()
        if not _global_connection.connect():
            raise ConnectionError("无法建立全局 RabbitMQ 连接")
    return _global_connection

def close_global_connection():
    """关闭全局连接"""
    global _global_connection
    if _global_connection:
        _global_connection.disconnect()
        _global_connection = None
