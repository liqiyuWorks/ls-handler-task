"""
配置文件管理工具
用于管理微信群监控的配置文件
"""

import json
import os
from typing import List, Dict, Any


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "monitor_groups": [],
            "save_messages": True,
            "output_dir": "messages",
            "log_level": "INFO",
            "check_interval": 10,
            "max_messages_per_file": 1000,
            "message_filters": {
                "keywords": [],
                "exclude_keywords": [
                    "撤回了一条消息",
                    "拍了拍",
                    "加入了群聊",
                    "退出了群聊",
                    "修改群名为",
                    "邀请",
                    "开启了朋友验证"
                ],
                "sender_whitelist": [],
                "sender_blacklist": []
            },
            "auto_save": True,
            "export_format": "json"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                print("使用默认配置")
        
        return default_config
    
    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"✅ 配置已保存到: {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def show_config(self):
        """显示当前配置"""
        print("\n" + "=" * 50)
        print("当前配置信息")
        print("=" * 50)
        
        print(f"监控群聊数量: {len(self.config.get('monitor_groups', []))}")
        if self.config.get('monitor_groups'):
            print("监控的群聊:")
            for i, group in enumerate(self.config['monitor_groups'], 1):
                print(f"  {i}. {group}")
        
        print(f"\n保存消息: {self.config.get('save_messages', True)}")
        print(f"输出目录: {self.config.get('output_dir', 'messages')}")
        print(f"日志级别: {self.config.get('log_level', 'INFO')}")
        print(f"检查间隔: {self.config.get('check_interval', 10)} 秒")
        print(f"自动保存: {self.config.get('auto_save', True)}")
        print(f"导出格式: {self.config.get('export_format', 'json')}")
        
        # 显示过滤配置
        filters = self.config.get('message_filters', {})
        print(f"\n消息过滤配置:")
        print(f"  关键词过滤: {len(filters.get('keywords', []))} 个")
        print(f"  排除关键词: {len(filters.get('exclude_keywords', []))} 个")
        print(f"  发送者白名单: {len(filters.get('sender_whitelist', []))} 个")
        print(f"  发送者黑名单: {len(filters.get('sender_blacklist', []))} 个")
    
    def add_monitor_group(self, group_name: str) -> bool:
        """添加监控群聊"""
        if group_name not in self.config.get('monitor_groups', []):
            if 'monitor_groups' not in self.config:
                self.config['monitor_groups'] = []
            self.config['monitor_groups'].append(group_name)
            print(f"✅ 已添加监控群聊: {group_name}")
            return True
        else:
            print(f"⚠️ 群聊 {group_name} 已在监控列表中")
            return False
    
    def remove_monitor_group(self, group_name: str) -> bool:
        """移除监控群聊"""
        if group_name in self.config.get('monitor_groups', []):
            self.config['monitor_groups'].remove(group_name)
            print(f"✅ 已移除监控群聊: {group_name}")
            return True
        else:
            print(f"❌ 群聊 {group_name} 不在监控列表中")
            return False
    
    def clear_monitor_groups(self):
        """清空监控群聊列表"""
        self.config['monitor_groups'] = []
        print("✅ 已清空监控群聊列表")
    
    def set_check_interval(self, interval: int):
        """设置检查间隔"""
        if interval > 0:
            self.config['check_interval'] = interval
            print(f"✅ 检查间隔已设置为: {interval} 秒")
        else:
            print("❌ 检查间隔必须大于0")
    
    def set_log_level(self, level: str):
        """设置日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level.upper() in valid_levels:
            self.config['log_level'] = level.upper()
            print(f"✅ 日志级别已设置为: {level.upper()}")
        else:
            print(f"❌ 无效的日志级别，有效值: {valid_levels}")
    
    def add_keyword_filter(self, keyword: str):
        """添加关键词过滤"""
        if 'message_filters' not in self.config:
            self.config['message_filters'] = {}
        if 'keywords' not in self.config['message_filters']:
            self.config['message_filters']['keywords'] = []
        
        if keyword not in self.config['message_filters']['keywords']:
            self.config['message_filters']['keywords'].append(keyword)
            print(f"✅ 已添加关键词过滤: {keyword}")
        else:
            print(f"⚠️ 关键词 {keyword} 已存在")
    
    def remove_keyword_filter(self, keyword: str):
        """移除关键词过滤"""
        if keyword in self.config.get('message_filters', {}).get('keywords', []):
            self.config['message_filters']['keywords'].remove(keyword)
            print(f"✅ 已移除关键词过滤: {keyword}")
        else:
            print(f"❌ 关键词 {keyword} 不存在")
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "=" * 50)
        print("配置文件管理工具")
        print("=" * 50)
        print("1. 查看当前配置")
        print("2. 添加监控群聊")
        print("3. 移除监控群聊")
        print("4. 清空监控群聊")
        print("5. 设置检查间隔")
        print("6. 设置日志级别")
        print("7. 添加关键词过滤")
        print("8. 移除关键词过滤")
        print("9. 保存配置")
        print("0. 退出")
        print("=" * 50)
    
    def run(self):
        """运行配置管理器"""
        while True:
            self.show_menu()
            choice = input("\n请选择操作 (0-9): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            elif choice == "1":
                self.show_config()
            elif choice == "2":
                group_name = input("请输入要添加的群聊名称: ").strip()
                if group_name:
                    self.add_monitor_group(group_name)
            elif choice == "3":
                groups = self.config.get('monitor_groups', [])
                if groups:
                    print("当前监控的群聊:")
                    for i, group in enumerate(groups, 1):
                        print(f"  {i}. {group}")
                    group_name = input("请输入要移除的群聊名称: ").strip()
                    if group_name:
                        self.remove_monitor_group(group_name)
                else:
                    print("当前没有监控任何群聊")
            elif choice == "4":
                confirm = input("确认清空所有监控群聊? (y/N): ").strip().lower()
                if confirm == 'y':
                    self.clear_monitor_groups()
            elif choice == "5":
                try:
                    interval = int(input("请输入检查间隔(秒): ").strip())
                    self.set_check_interval(interval)
                except ValueError:
                    print("❌ 请输入有效的数字")
            elif choice == "6":
                level = input("请输入日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL): ").strip()
                self.set_log_level(level)
            elif choice == "7":
                keyword = input("请输入要添加的关键词: ").strip()
                if keyword:
                    self.add_keyword_filter(keyword)
            elif choice == "8":
                keywords = self.config.get('message_filters', {}).get('keywords', [])
                if keywords:
                    print("当前关键词过滤:")
                    for i, kw in enumerate(keywords, 1):
                        print(f"  {i}. {kw}")
                    keyword = input("请输入要移除的关键词: ").strip()
                    if keyword:
                        self.remove_keyword_filter(keyword)
                else:
                    print("当前没有设置关键词过滤")
            elif choice == "9":
                self.save_config()
            else:
                print("❌ 无效的选择，请重新输入")
            
            input("\n按回车键继续...")


def main():
    """主函数"""
    manager = ConfigManager()
    manager.run()


if __name__ == "__main__":
    main()
