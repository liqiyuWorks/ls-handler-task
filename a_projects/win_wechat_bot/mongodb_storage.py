"""
MongoDB 消息存储模块
用于存储微信群消息到 MongoDB 数据库
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict
import pymongo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import json


class MongoDBStorage:
    """MongoDB 消息存储类"""
    
    def __init__(self, 
                 host: str = "153.35.96.86",
                 port: int = 27017,
                 database: str = "aquabridge",
                 username: str = "aquabridge",
                 password: str = "Aquabridge#2025",
                 collection: str = "wechat_messages"):
        """
        初始化 MongoDB 连接
        
        Args:
            host: MongoDB 主机地址
            port: MongoDB 端口
            database: 数据库名称
            username: 用户名
            password: 密码
            collection: 集合名称
        """
        self.host = host
        self.port = port
        self.database_name = database
        self.username = username
        self.password = password
        self.collection_name = collection
        
        self.client = None
        self.db = None
        self.collection = None
        self.logger = self._setup_logger()
        
        # 连接数据库
        self._connect()
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('MongoDBStorage')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _connect(self) -> bool:
        """
        连接到 MongoDB 数据库
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 构建连接字符串
            connection_string = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}"
            
            # 连接 MongoDB
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            
            # 测试连接
            self.client.admin.command('ping')
            
            # 获取数据库和集合
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            # 创建索引
            self._create_indexes()
            
            self.logger.info(f"成功连接到 MongoDB: {self.host}:{self.port}/{self.database_name}")
            return True
            
        except ConnectionFailure as e:
            self.logger.error(f"连接 MongoDB 失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"初始化 MongoDB 连接时出错: {e}")
            return False
    
    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # 创建消息哈希索引（用于去重）
            self.collection.create_index("message_hash", unique=True)
            
            # 创建群聊名称索引
            self.collection.create_index("group_name")
            
            # 创建时间戳索引
            self.collection.create_index("timestamp")
            
            # 创建发送者索引
            self.collection.create_index("sender")
            
            # 创建关键词索引（用于快速搜索）
            self.collection.create_index("keywords")
            
            # 创建复合索引：群聊名称 + 时间戳
            self.collection.create_index([("group_name", 1), ("timestamp", -1)])
            
            # 创建复合索引：关键词 + 群聊名称（用于关键词搜索优化）
            self.collection.create_index([("keywords", 1), ("group_name", 1)])
            
            self.logger.info("数据库索引创建成功")
            
        except Exception as e:
            self.logger.warning(f"创建索引时出错: {e}")
    
    def _generate_message_hash(self, message: Union[Dict, Any]) -> str:
        """
        生成消息的唯一哈希值，用于去重
        
        Args:
            message: 群消息对象或字典
            
        Returns:
            str: 消息哈希值
        """
        # 处理不同类型的消息对象
        if isinstance(message, dict):
            group_name = message.get('group_name', '')
            sender = message.get('sender', '')
            content = message.get('content', '')
            timestamp = message.get('timestamp', '')
        else:
            # 假设是 GroupMessage 对象
            group_name = getattr(message, 'group_name', '')
            sender = getattr(message, 'sender', '')
            content = getattr(message, 'content', '')
            timestamp = getattr(message, 'timestamp', '')
        
        # 使用消息的关键信息生成哈希
        hash_string = f"{group_name}|{sender}|{content}|{timestamp}"
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def save_message(self, message: Union[Dict, Any]) -> bool:
        """
        保存单条消息到数据库
        
        Args:
            message: 群消息对象或字典
            
        Returns:
            bool: 保存是否成功
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return False
        
        try:
            # 生成消息哈希
            message_hash = self._generate_message_hash(message)
            
            # 转换为字典格式
            if isinstance(message, dict):
                message_dict = message.copy()
            else:
                message_dict = asdict(message)
            
            message_dict['message_hash'] = message_hash
            message_dict['created_at'] = datetime.now()
            
            # 插入到数据库
            self.collection.insert_one(message_dict)
            self.logger.debug(f"消息已保存到数据库: {message_hash}")
            return True
            
        except DuplicateKeyError:
            self.logger.debug(f"消息已存在，跳过保存: {message_hash}")
            return False
        except Exception as e:
            self.logger.error(f"保存消息失败: {e}")
            return False
    
    def save_messages(self, messages: List[Union[Dict, Any]]) -> Dict[str, int]:
        """
        批量保存消息到数据库
        
        Args:
            messages: 消息列表
            
        Returns:
            Dict[str, int]: 保存结果统计
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return {"saved": 0, "duplicates": 0, "errors": 0}
        
        saved_count = 0
        duplicate_count = 0
        error_count = 0
        
        for message in messages:
            try:
                # 生成消息哈希
                message_hash = self._generate_message_hash(message)
                
                # 转换为字典格式
                if isinstance(message, dict):
                    message_dict = message.copy()
                else:
                    message_dict = asdict(message)
                
                message_dict['message_hash'] = message_hash
                message_dict['created_at'] = datetime.now()
                
                # 插入到数据库
                self.collection.insert_one(message_dict)
                saved_count += 1
                
            except DuplicateKeyError:
                duplicate_count += 1
                self.logger.debug(f"消息已存在，跳过保存: {message_hash}")
            except Exception as e:
                error_count += 1
                self.logger.error(f"保存消息失败: {e}")
        
        result = {
            "saved": saved_count,
            "duplicates": duplicate_count,
            "errors": error_count
        }
        
        self.logger.info(f"批量保存完成: 新增 {saved_count} 条, 重复 {duplicate_count} 条, 错误 {error_count} 条")
        return result
    
    def get_messages(self, 
                    group_name: str = None,
                    sender: str = None,
                    limit: int = 100,
                    start_time: datetime = None,
                    end_time: datetime = None) -> List[Dict]:
        """
        从数据库查询消息
        
        Args:
            group_name: 群聊名称
            sender: 发送者
            limit: 限制数量
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[Dict]: 消息列表
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return []
        
        try:
            # 构建查询条件
            query = {}
            
            if group_name:
                query['group_name'] = group_name
            
            if sender:
                query['sender'] = sender
            
            if start_time or end_time:
                query['timestamp'] = {}
                if start_time:
                    query['timestamp']['$gte'] = start_time.isoformat()
                if end_time:
                    query['timestamp']['$lte'] = end_time.isoformat()
            
            # 查询消息
            cursor = self.collection.find(query).sort('timestamp', -1).limit(limit)
            messages = list(cursor)
            
            # 移除 MongoDB 的 _id 字段
            for message in messages:
                message.pop('_id', None)
                message.pop('message_hash', None)
                message.pop('created_at', None)
            
            self.logger.info(f"查询到 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            self.logger.error(f"查询消息失败: {e}")
            return []
    
    def search_messages(self, keyword: str, group_name: str = None, limit: int = 100) -> List[Dict]:
        """
        搜索包含关键词的消息（优化版本，优先使用keywords字段）
        
        Args:
            keyword: 搜索关键词
            group_name: 群聊名称
            limit: 限制数量
            
        Returns:
            List[Dict]: 匹配的消息列表
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return []
        
        try:
            # 构建查询条件 - 优先使用keywords字段进行精确匹配
            query = {
                '$or': [
                    {'keywords': {'$in': [keyword]}},  # 精确匹配keywords字段
                    {'content': {'$regex': keyword, '$options': 'i'}}  # 回退到内容搜索
                ]
            }
            
            if group_name:
                query['group_name'] = group_name
            
            # 查询消息，按时间戳倒序
            cursor = self.collection.find(query).sort('timestamp', -1).limit(limit)
            messages = list(cursor)
            
            # 移除 MongoDB 的 _id 字段
            for message in messages:
                message.pop('_id', None)
                message.pop('message_hash', None)
                message.pop('created_at', None)
            
            self.logger.info(f"搜索关键词 '{keyword}' 找到 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            self.logger.error(f"搜索消息失败: {e}")
            return []
    
    def search_by_keywords(self, keywords: List[str], group_name: str = None, limit: int = 100) -> List[Dict]:
        """
        根据关键词列表精确搜索消息（最高性能）
        
        Args:
            keywords: 关键词列表
            group_name: 群聊名称
            limit: 限制数量
            
        Returns:
            List[Dict]: 匹配的消息列表
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return []
        
        try:
            # 构建查询条件 - 使用keywords字段进行精确匹配
            query = {
                'keywords': {'$in': keywords}  # 匹配任意一个关键词
            }
            
            if group_name:
                query['group_name'] = group_name
            
            # 查询消息，按时间戳倒序
            cursor = self.collection.find(query).sort('timestamp', -1).limit(limit)
            messages = list(cursor)
            
            # 移除 MongoDB 的 _id 字段
            for message in messages:
                message.pop('_id', None)
                message.pop('message_hash', None)
                message.pop('created_at', None)
            
            self.logger.info(f"根据关键词 {keywords} 找到 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            self.logger.error(f"根据关键词搜索消息失败: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return {}
        
        try:
            # 总消息数
            total_messages = self.collection.count_documents({})
            
            # 按群聊统计
            group_stats = list(self.collection.aggregate([
                {'$group': {'_id': '$group_name', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}}
            ]))
            
            # 按发送者统计
            sender_stats = list(self.collection.aggregate([
                {'$group': {'_id': '$sender', 'count': {'$sum': 1}}},
                {'$sort': {'count': -1}},
                {'$limit': 10}
            ]))
            
            # 最近24小时的消息数
            from datetime import timedelta
            yesterday = datetime.now() - timedelta(days=1)
            recent_messages = self.collection.count_documents({
                'timestamp': {'$gte': yesterday.isoformat()}
            })
            
            stats = {
                'total_messages': total_messages,
                'recent_24h_messages': recent_messages,
                'group_statistics': group_stats,
                'top_senders': sender_stats
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {}
    
    def delete_old_messages(self, days: int = 30) -> int:
        """
        删除指定天数之前的旧消息
        
        Args:
            days: 保留天数
            
        Returns:
            int: 删除的消息数量
        """
        if self.collection is None:
            self.logger.error("数据库连接未建立")
            return 0
        
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            result = self.collection.delete_many({
                'timestamp': {'$lt': cutoff_date.isoformat()}
            })
            
            deleted_count = result.deleted_count
            self.logger.info(f"删除了 {deleted_count} 条 {days} 天前的旧消息")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"删除旧消息失败: {e}")
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB 连接已关闭")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


def main():
    """测试 MongoDB 存储功能"""
    print("MongoDB 消息存储测试")
    print("=" * 40)
    
    # 创建存储实例
    storage = MongoDBStorage()
    
    if storage.collection is None:
        print("❌ 数据库连接失败")
        return
    
    print("✅ 数据库连接成功")
    
    # 获取统计信息
    stats = storage.get_statistics()
    print(f"\n📊 数据库统计信息:")
    print(f"总消息数: {stats.get('total_messages', 0)}")
    print(f"最近24小时消息数: {stats.get('recent_24h_messages', 0)}")
    
    # 显示群聊统计
    group_stats = stats.get('group_statistics', [])
    if group_stats:
        print(f"\n📋 群聊统计:")
        for group in group_stats[:5]:  # 显示前5个
            print(f"  {group['_id']}: {group['count']} 条消息")
    
    # 显示活跃发送者
    sender_stats = stats.get('top_senders', [])
    if sender_stats:
        print(f"\n👥 活跃发送者:")
        for sender in sender_stats[:5]:  # 显示前5个
            print(f"  {sender['_id']}: {sender['count']} 条消息")
    
    # 关闭连接
    storage.close()


if __name__ == "__main__":
    main()
