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
    
    def get_group_messages(self, group_name: str, limit: int = 20) -> List[GroupMessage]:
        """
        获取指定群聊的消息
        
        Args:
            group_name: 群聊名称
            limit: 获取消息数量限制
            
        Returns:
            List[GroupMessage]: 消息列表
        """
        if not self.wx:
            self.logger.error("微信客户端未连接")
            return []
        
        try:
            # 切换到指定群聊
            self.wx.ChatWith(group_name)
            time.sleep(3)  # 等待页面加载
            
            # 获取消息
            messages = self.wx.GetAllMessage()
            
            group_messages = []
            if messages:
                self.logger.info(f"获取到 {len(messages)} 条原始消息")
                
                # 处理消息对象
                for i, msg in enumerate(messages[-limit:]):
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
                        if content and content.strip() and not self._is_system_message(content):
                            if self._should_include_message(content, sender):
                                group_message = GroupMessage(
                                    timestamp=datetime.now().isoformat(),
                                    sender=sender or "未知用户",
                                    content=content,
                                    group_name=group_name,
                                    message_type=msg_type,
                                    raw_data=str(msg)
                                )
                                group_messages.append(group_message)
                    
                    except Exception as msg_error:
                        self.logger.debug(f"处理第 {i} 条消息时出错: {msg_error}")
                        continue
            
            self.logger.info(f"从群 '{group_name}' 成功处理 {len(group_messages)} 条消息")
            return group_messages
            
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
    
    def save_messages(self, messages: List[GroupMessage], group_name: str = None):
        """保存消息到文件"""
        if not self.config['save_messages'] or not messages:
            return
        
        # 创建输出目录
        output_dir = self.config['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if group_name:
            filename = f"{group_name}_{timestamp}.json"
        else:
            filename = f"messages_{timestamp}.json"
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            # 转换为字典格式
            messages_data = [asdict(msg) for msg in messages]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"消息已保存到: {filepath}")
        except Exception as e:
            self.logger.error(f"保存消息失败: {e}")
    
    def search_messages(self, keyword: str, group_name: str = None) -> List[GroupMessage]:
        """搜索包含关键词的消息"""
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
                for group_name in self.monitored_groups:
                    try:
                        messages = self.get_group_messages(group_name, limit=10)
                        if messages:
                            self.save_messages(messages, group_name)
                            
                            # 打印新消息
                            for msg in messages:
                                print(f"[{group_name}] {msg.sender}: {msg.content}")
                    
                    except Exception as e:
                        self.logger.error(f"监控群 '{group_name}' 时出错: {e}")
                
                # 等待下次检查
                time.sleep(self.config.get('check_interval', 5))
                
        except KeyboardInterrupt:
            self.logger.info("监控已停止")
        except Exception as e:
            self.logger.error(f"监控过程中出错: {e}")


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
