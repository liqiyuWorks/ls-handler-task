"""
微信群监控系统
基于 wxauto 库实现微信群消息获取和监控
"""

import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import os

try:
    from wxauto import WeChat
except ImportError:
    print("请先安装 wxauto 库: pip install wxauto")
    raise

try:
    from mongodb_storage import MongoDBStorage
except ImportError:
    print("MongoDB 存储模块未找到，将使用文件存储")
    MongoDBStorage = None


@dataclass
class GroupMessage:
    """群消息数据类"""
    timestamp: str
    sender: str
    content: str
    group_name: str
    message_type: str = "text"
    raw_data: Optional[str] = None


class WeChatGroupMonitor:
    """微信群监控器"""
    
    def __init__(self, config_file: str = "config.json"):
        """
        初始化微信群监控器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self._load_config(config_file)
        self.wx = None
        self.logger = self._setup_logger()
        # 从配置文件加载监控群聊列表
        self.monitored_groups = set(self.config.get('monitor_groups', []))
        self.logger.info(f"从配置文件加载了 {len(self.monitored_groups)} 个监控群聊")
        
        # 初始化 MongoDB 存储
        self.mongodb_storage = None
        self._init_mongodb_storage()
        
        # 消息去重和增量获取相关
        self.last_message_timestamps = {}  # 记录每个群聊最后获取的消息时间戳
        self.processed_message_hashes = set()  # 记录已处理的消息哈希，避免重复
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "monitor_groups": [],
            "save_messages": True,
            "output_dir": "messages",
            "log_level": "INFO",
            "check_interval": 5,
            "message_filters": {
                "keywords": [],
                "exclude_keywords": ["撤回了一条消息", "拍了拍"],
                "sender_whitelist": [],
                "sender_blacklist": []
            }
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                print("使用默认配置")
        
        return default_config
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('SimpleWeChatMonitor')
        logger.setLevel(getattr(logging, self.config['log_level']))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_mongodb_storage(self):
        """初始化 MongoDB 存储"""
        if not MongoDBStorage:
            self.logger.warning("MongoDB 存储模块不可用")
            return
        
        mongodb_config = self.config.get('mongodb', {})
        if not mongodb_config.get('enabled', False):
            self.logger.info("MongoDB 存储已禁用")
            return
        
        try:
            self.mongodb_storage = MongoDBStorage(
                host=mongodb_config.get('host', '153.35.96.86'),
                port=mongodb_config.get('port', 27017),
                database=mongodb_config.get('database', 'aquabridge'),
                username=mongodb_config.get('username', 'aquabridge'),
                password=mongodb_config.get('password', 'Aquabridge#2025'),
                collection=mongodb_config.get('collection', 'wechat_messages')
            )
            
            if self.mongodb_storage.collection is not None:
                self.logger.info("MongoDB 存储初始化成功")
            else:
                self.logger.warning("MongoDB 存储初始化失败")
                self.mongodb_storage = None
                
        except Exception as e:
            self.logger.error(f"初始化 MongoDB 存储时出错: {e}")
            self.mongodb_storage = None
    
    def add_monitor_group(self, group_name: str) -> bool:
        """
        添加要监控的群聊
        
        Args:
            group_name: 群聊名称
            
        Returns:
            bool: 是否添加成功
        """
        if group_name not in self.monitored_groups:
            self.monitored_groups.add(group_name)
            self.config['monitor_groups'] = list(self.monitored_groups)
            self._save_config()
            self.logger.info(f"已添加监控群聊: {group_name}")
            return True
        return False
    
    def remove_monitor_group(self, group_name: str) -> bool:
        """
        移除监控的群聊
        
        Args:
            group_name: 群聊名称
            
        Returns:
            bool: 是否移除成功
        """
        if group_name in self.monitored_groups:
            self.monitored_groups.remove(group_name)
            self.config['monitor_groups'] = list(self.monitored_groups)
            self._save_config()
            self.logger.info(f"已移除监控群聊: {group_name}")
            return True
        return False
    
    def get_monitor_groups(self) -> List[str]:
        """
        获取当前监控的群聊列表
        
        Returns:
            List[str]: 监控群聊列表
        """
        return list(self.monitored_groups)
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            self.logger.info(f"配置已保存到: {self.config_file}")
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
    
    def reload_config(self):
        """重新加载配置文件"""
        try:
            self.config = self._load_config(self.config_file)
            # 更新监控群聊列表
            old_groups = self.monitored_groups.copy()
            self.monitored_groups = set(self.config.get('monitor_groups', []))
            
            # 记录变化
            added = self.monitored_groups - old_groups
            removed = old_groups - self.monitored_groups
            
            if added:
                self.logger.info(f"新增监控群聊: {list(added)}")
            if removed:
                self.logger.info(f"移除监控群聊: {list(removed)}")
            
            self.logger.info(f"配置重新加载完成，当前监控 {len(self.monitored_groups)} 个群聊")
            return True
        except Exception as e:
            self.logger.error(f"重新加载配置失败: {e}")
            return False
    
    def connect_wechat(self) -> bool:
        """
        连接微信客户端
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.logger.info("正在连接微信客户端...")
            self.wx = WeChat()
            self.logger.info("微信客户端连接成功")
            return True
        except Exception as e:
            self.logger.error(f"连接微信客户端失败: {e}")
            return False
    
    def get_group_list(self) -> List[str]:
        """
        获取所有群聊列表
        
        Returns:
            List[str]: 群聊名称列表
        """
        if not self.wx:
            self.logger.error("微信客户端未连接")
            return []
        
        try:
            # 尝试多种方法获取群聊列表
            groups = []
            
            # 方法1: 使用 GetContactGroups
            try:
                groups = self.wx.GetContactGroups()
                if groups:
                    self.logger.info(f"通过 GetContactGroups 找到 {len(groups)} 个群聊")
                    return groups
            except Exception as e:
                self.logger.debug(f"GetContactGroups 失败: {e}")
            
            # 方法2: 尝试获取所有联系人
            try:
                contacts = self.wx.GetContacts()
                if contacts:
                    # 过滤出群聊（通常群聊名称包含特殊字符或格式）
                    for contact in contacts:
                        if isinstance(contact, str) and ('群' in contact or len(contact) > 10):
                            groups.append(contact)
                    if groups:
                        self.logger.info(f"通过 GetContacts 找到 {len(groups)} 个可能的群聊")
                        return groups
            except Exception as e:
                self.logger.debug(f"GetContacts 失败: {e}")
            
            # 方法3: 手动输入群聊名称
            self.logger.warning("无法自动获取群聊列表，请手动输入群聊名称")
            return []
            
        except Exception as e:
            self.logger.error(f"获取群聊列表失败: {e}")
            return []
    
    def get_group_messages(self, group_name: str, limit: int = 3) -> List[GroupMessage]:
        """
        获取指定群聊的新消息（增量获取，避免重复）
        
        Args:
            group_name: 群聊名称
            limit: 获取含关键词消息的最大数量限制（默认3条）
            
        Returns:
            List[GroupMessage]: 新消息列表
        """
        if not self.wx:
            self.logger.error("微信客户端未连接")
            return []
        
        try:
            # 切换到指定群聊
            self.wx.ChatWith(group_name)
            time.sleep(3)  # 等待页面加载
            
            # 获取消息 - 使用多种方法
            messages = []
            
            # 方法1: 尝试 GetAllMessage
            try:
                messages = self.wx.GetAllMessage()
                self.logger.debug(f"GetAllMessage() 获取到 {len(messages) if messages else 0} 条消息")
            except Exception as e:
                self.logger.debug(f"GetAllMessage() 失败: {e}")
            
            # 方法2: 如果 GetAllMessage 失败，尝试 GetNextNewMessage
            if not messages:
                try:
                    new_msg_data = self.wx.GetNextNewMessage()
                    if new_msg_data and 'msg' in new_msg_data:
                        messages = new_msg_data['msg']
                        self.logger.debug(f"GetNextNewMessage() 获取到 {len(messages)} 条消息")
                except Exception as e:
                    self.logger.debug(f"GetNextNewMessage() 失败: {e}")
            
            # 方法3: 尝试 LoadMoreMessage
            if not messages:
                try:
                    more_messages = self.wx.LoadMoreMessage()
                    if more_messages and hasattr(more_messages, 'data'):
                        messages = more_messages.data
                        self.logger.debug(f"LoadMoreMessage() 获取到 {len(messages)} 条消息")
                except Exception as e:
                    self.logger.debug(f"LoadMoreMessage() 失败: {e}")
            
            if not messages:
                self.logger.debug(f"群聊 '{group_name}' 中没有获取到任何消息")
                return []
            
            self.logger.debug(f"获取到 {len(messages)} 条原始消息")
            
            # 处理消息对象，只获取含关键词的新消息
            new_messages = []
            keyword_messages_count = 0
            
            # 从最新消息开始处理（倒序）
            for msg in reversed(messages):
                if keyword_messages_count >= limit:
                    break
                    
                try:
                    # 尝试不同的属性访问方式
                    content = ""
                    sender = ""
                    msg_type = "text"
                    
                    # 检查消息对象的属性
                    if hasattr(msg, 'content'):
                        content = str(getattr(msg, 'content', ''))
                    elif hasattr(msg, 'text'):
                        content = str(getattr(msg, 'text', ''))
                    elif hasattr(msg, 'msg'):
                        content = str(getattr(msg, 'msg', ''))
                    
                    if hasattr(msg, 'sender'):
                        sender = str(getattr(msg, 'sender', ''))
                    elif hasattr(msg, 'from_user'):
                        sender = str(getattr(msg, 'from_user', ''))
                    elif hasattr(msg, 'user'):
                        sender = str(getattr(msg, 'user', ''))
                    
                    if hasattr(msg, 'type'):
                        msg_type = str(getattr(msg, 'type', 'text'))
                    
                    # 过滤空消息和系统消息
                    if not content or not content.strip() or self._is_system_message(content):
                        continue
                    
                    # 检查是否包含关键词
                    if not self._should_include_message(content, sender):
                        continue
                    
                    # 生成消息哈希，检查是否已处理过
                    message_hash = self._generate_message_hash(content, sender, group_name)
                    if self._is_message_processed(message_hash):
                        self.logger.debug(f"消息已处理过，跳过: {content[:30]}...")
                        continue
                    
                    # 创建消息对象
                    group_message = GroupMessage(
                        timestamp=datetime.now().isoformat(),
                        sender=sender or "未知用户",
                        content=content,
                        group_name=group_name,
                        message_type=msg_type,
                        raw_data=str(msg)
                    )
                    
                    new_messages.append(group_message)
                    self._mark_message_processed(message_hash)
                    keyword_messages_count += 1
                    
                    self.logger.info(f"发现新消息: [{sender}] {content[:50]}...")
                
                except Exception as msg_error:
                    self.logger.debug(f"处理消息时出错: {msg_error}")
                    continue
            
            # 更新最后获取时间戳
            if new_messages:
                self.last_message_timestamps[group_name] = datetime.now().isoformat()
            
            self.logger.info(f"从群 '{group_name}' 获取到 {len(new_messages)} 条新消息（含关键词）")
            return new_messages
            
        except Exception as e:
            self.logger.error(f"获取群 '{group_name}' 消息失败: {e}")
            return []
    
    def _is_system_message(self, content: str) -> bool:
        """判断是否为系统消息"""
        system_keywords = [
            "撤回了一条消息",
            "拍了拍",
            "加入了群聊",
            "退出了群聊",
            "修改群名为",
            "邀请",
            "开启了朋友验证"
        ]
        return any(keyword in content for keyword in system_keywords)
    
    def _should_include_message(self, content: str, sender: str) -> bool:
        """判断消息是否应该被包含"""
        content_lower = content.lower()
        
        # 检查关键词过滤
        if self.config['message_filters']['keywords']:
            if not any(keyword.lower() in content_lower for keyword in self.config['message_filters']['keywords']):
                return False
        
        # 检查排除关键词
        if self.config['message_filters']['exclude_keywords']:
            if any(keyword.lower() in content_lower for keyword in self.config['message_filters']['exclude_keywords']):
                return False
        
        # 检查发送者白名单
        if self.config['message_filters']['sender_whitelist']:
            if sender not in self.config['message_filters']['sender_whitelist']:
                return False
        
        # 检查发送者黑名单
        if self.config['message_filters']['sender_blacklist']:
            if sender in self.config['message_filters']['sender_blacklist']:
                return False
        
        return True
    
    def _generate_message_hash(self, content: str, sender: str, group_name: str) -> str:
        """生成消息的唯一哈希值，用于去重"""
        import hashlib
        hash_string = f"{group_name}|{sender}|{content}"
        return hashlib.md5(hash_string.encode('utf-8')).hexdigest()
    
    def _is_message_processed(self, message_hash: str) -> bool:
        """检查消息是否已经处理过"""
        return message_hash in self.processed_message_hashes
    
    def _mark_message_processed(self, message_hash: str):
        """标记消息为已处理"""
        self.processed_message_hashes.add(message_hash)
        
        # 限制已处理消息哈希集合的大小，避免内存无限增长
        if len(self.processed_message_hashes) > 10000:
            # 保留最近的一半
            self.processed_message_hashes = set(list(self.processed_message_hashes)[-5000:])
    
    def reset_message_tracking(self):
        """重置消息跟踪状态，清空已处理消息记录"""
        self.processed_message_hashes.clear()
        self.last_message_timestamps.clear()
        self.logger.info("消息跟踪状态已重置")
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """获取消息跟踪统计信息"""
        return {
            "processed_messages_count": len(self.processed_message_hashes),
            "tracked_groups": list(self.last_message_timestamps.keys()),
            "last_timestamps": self.last_message_timestamps.copy()
        }
    
    def save_messages(self, messages: List[GroupMessage], group_name: str = None):
        """保存消息到文件和/或数据库"""
        if not messages:
            return
        
        # 保存到 MongoDB（如果启用）
        if self.mongodb_storage:
            try:
                result = self.mongodb_storage.save_messages(messages)
                self.logger.info(f"MongoDB 保存结果: 新增 {result['saved']} 条, 重复 {result['duplicates']} 条, 错误 {result['errors']} 条")
            except Exception as e:
                self.logger.error(f"保存到 MongoDB 失败: {e}")
        
        # 保存到文件（如果启用）
        if self.config.get('save_messages', True):
            self._save_messages_to_file(messages, group_name)
    
    def _save_messages_to_file(self, messages: List[GroupMessage], group_name: str = None):
        """保存消息到文件"""
        try:
            # 创建输出目录
            output_dir = self.config.get('output_dir', 'messages')
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if group_name:
                filename = f"{group_name}_{timestamp}.json"
            else:
                filename = f"messages_{timestamp}.json"
            
            filepath = os.path.join(output_dir, filename)
            
            # 转换为字典格式
            messages_data = [asdict(msg) for msg in messages]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"消息已保存到文件: {filepath}")
        except Exception as e:
            self.logger.error(f"保存消息到文件失败: {e}")
    
    def search_messages(self, keyword: str, group_name: str = None) -> List[GroupMessage]:
        """搜索包含关键词的消息"""
        # 优先从 MongoDB 搜索
        if self.mongodb_storage:
            try:
                db_messages = self.mongodb_storage.search_messages(keyword, group_name)
                # 转换为 GroupMessage 对象
                matched_messages = []
                for msg_dict in db_messages:
                    msg = GroupMessage(
                        timestamp=msg_dict['timestamp'],
                        sender=msg_dict['sender'],
                        content=msg_dict['content'],
                        group_name=msg_dict['group_name'],
                        message_type=msg_dict.get('message_type', 'text'),
                        raw_data=msg_dict.get('raw_data')
                    )
                    matched_messages.append(msg)
                return matched_messages
            except Exception as e:
                self.logger.error(f"从 MongoDB 搜索消息失败: {e}")
        
        # 回退到本地搜索
        messages = self.get_group_messages(group_name) if group_name else []
        keyword_lower = keyword.lower()
        
        matched_messages = []
        for msg in messages:
            if keyword_lower in msg.content.lower():
                matched_messages.append(msg)
        
        return matched_messages
    
    def export_messages_to_csv(self, messages: List[GroupMessage], filename: str = None):
        """导出消息到CSV文件"""
        if not messages:
            return
        
        import csv
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"messages_export_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['timestamp', 'group_name', 'sender', 'content', 'message_type']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for msg in messages:
                    writer.writerow({
                        'timestamp': msg.timestamp,
                        'group_name': msg.group_name,
                        'sender': msg.sender,
                        'content': msg.content,
                        'message_type': msg.message_type
                    })
            
            self.logger.info(f"消息已导出到CSV文件: {filename}")
        except Exception as e:
            self.logger.error(f"导出CSV文件失败: {e}")
    
    def start_monitoring(self):
        """
        开始监控配置的群聊
        """
        if not self.wx:
            self.logger.error("微信客户端未连接")
            return
        
        if not self.monitored_groups:
            self.logger.warning("没有配置要监控的群聊")
            return
        
        self.logger.info(f"开始监控 {len(self.monitored_groups)} 个群聊")
        
        try:
            while True:
                total_new_messages = 0
                
                for group_name in self.monitored_groups:
                    try:
                        # 获取最多3条含关键词的新消息
                        messages = self.get_group_messages(group_name, limit=3)
                        if messages:
                            self.save_messages(messages, group_name)
                            total_new_messages += len(messages)
                            
                            # 打印新消息
                            for msg in messages:
                                print(f"[{group_name}] {msg.sender}: {msg.content}")
                        else:
                            self.logger.debug(f"群聊 '{group_name}' 没有新消息")
                    
                    except Exception as e:
                        self.logger.error(f"监控群 '{group_name}' 时出错: {e}")
                
                # 显示本轮监控结果
                if total_new_messages > 0:
                    self.logger.info(f"本轮监控获取到 {total_new_messages} 条新消息")
                else:
                    self.logger.debug("本轮监控没有新消息")
                
                # 等待下次检查
                time.sleep(self.config.get('check_interval', 5))
                
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
        except Exception as e:
            self.logger.error(f"监控过程中出错: {e}")
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        if not self.mongodb_storage:
            return {"error": "MongoDB 存储未启用"}
        
        try:
            return self.mongodb_storage.get_statistics()
        except Exception as e:
            self.logger.error(f"获取数据库统计信息失败: {e}")
            return {"error": str(e)}
    
    def get_messages_from_database(self, 
                                 group_name: str = None,
                                 sender: str = None,
                                 limit: int = 100) -> List[GroupMessage]:
        """从数据库获取消息"""
        if not self.mongodb_storage:
            self.logger.warning("MongoDB 存储未启用")
            return []
        
        try:
            db_messages = self.mongodb_storage.get_messages(
                group_name=group_name,
                sender=sender,
                limit=limit
            )
            
            # 转换为 GroupMessage 对象
            messages = []
            for msg_dict in db_messages:
                msg = GroupMessage(
                    timestamp=msg_dict['timestamp'],
                    sender=msg_dict['sender'],
                    content=msg_dict['content'],
                    group_name=msg_dict['group_name'],
                    message_type=msg_dict.get('message_type', 'text'),
                    raw_data=msg_dict.get('raw_data')
                )
                messages.append(msg)
            
            return messages
        except Exception as e:
            self.logger.error(f"从数据库获取消息失败: {e}")
            return []
    
    def close(self):
        """关闭连接"""
        if self.mongodb_storage:
            self.mongodb_storage.close()


def main():
    """主函数 - 示例用法"""
    monitor = WeChatGroupMonitor()
    
    # 连接微信
    if not monitor.connect_wechat():
        return
    
    # 获取所有群聊列表
    groups = monitor.get_group_list()
    print("可用的群聊:")
    for i, group in enumerate(groups, 1):
        print(f"{i}. {group}")
    
    # 如果没有自动获取到群聊，让用户手动输入
    if not groups:
        print("\n请手动输入要监控的群聊名称:")
        group_name = input("群聊名称: ").strip()
        if group_name:
            groups = [group_name]
    
    # 示例：获取指定群聊的消息
    if groups:
        group_name = groups[0]  # 选择第一个群聊
        print(f"\n正在获取群 '{group_name}' 的消息...")
        messages = monitor.get_group_messages(group_name, limit=10)
        
        print(f"\n群 '{group_name}' 的最新消息:")
        for msg in messages:
            print(f"[{msg.timestamp}] {msg.sender}: {msg.content}")
        
        # 保存消息
        if messages:
            monitor.save_messages(messages, group_name)


if __name__ == "__main__":
    main()
