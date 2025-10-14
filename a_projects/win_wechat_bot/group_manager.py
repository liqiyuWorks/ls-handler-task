"""
微信群聊管理工具
用于管理监控的群聊列表
"""

import json
from wechat_monitor import WeChatGroupMonitor


class GroupManager:
    """群聊管理器"""
    
    def __init__(self):
        self.monitor = WeChatGroupMonitor()
    
    def show_menu(self):
        """显示菜单"""
        print("\n" + "=" * 50)
        print("微信群聊管理工具")
        print("=" * 50)
        print("1. 连接微信")
        print("2. 查看所有群聊")
        print("3. 查看监控的群聊")
        print("4. 添加监控群聊")
        print("5. 移除监控群聊")
        print("6. 测试群聊消息")
        print("7. 开始监控")
        print("8. 重新加载配置")
        print("0. 退出")
        print("=" * 50)
    
    def connect_wechat(self):
        """连接微信"""
        print("正在连接微信...")
        if self.monitor.connect_wechat():
            print("✅ 微信连接成功")
            return True
        else:
            print("❌ 微信连接失败")
            return False
    
    def show_all_groups(self):
        """显示所有群聊"""
        if not self.monitor.wx:
            print("❌ 请先连接微信")
            return
        
        groups = self.monitor.get_group_list()
        if groups:
            print(f"\n📋 找到 {len(groups)} 个群聊:")
            for i, group in enumerate(groups, 1):
                status = "🔍" if group in self.monitor.get_monitor_groups() else "⚪"
                print(f"  {i:2d}. {status} {group}")
        else:
            print("❌ 没有找到群聊")
    
    def show_monitored_groups(self):
        """显示监控的群聊"""
        monitored = self.monitor.get_monitor_groups()
        if monitored:
            print(f"\n🔍 当前监控 {len(monitored)} 个群聊:")
            for i, group in enumerate(monitored, 1):
                print(f"  {i}. {group}")
        else:
            print("\n⚠️ 当前没有监控任何群聊")
    
    def add_group(self):
        """添加监控群聊"""
        if not self.monitor.wx:
            print("❌ 请先连接微信")
            return
        
        # 显示所有群聊
        groups = self.monitor.get_group_list()
        if not groups:
            print("❌ 没有找到群聊")
            return
        
        print("\n📋 可用的群聊:")
        for i, group in enumerate(groups, 1):
            status = "🔍" if group in self.monitor.get_monitor_groups() else "⚪"
            print(f"  {i:2d}. {status} {group}")
        
        try:
            choice = input("\n请输入要添加的群聊编号 (或直接输入群聊名称): ").strip()
            
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(groups):
                    group_name = groups[idx]
                else:
                    print("❌ 无效的编号")
                    return
            else:
                group_name = choice
            
            if self.monitor.add_monitor_group(group_name):
                print(f"✅ 已添加监控群聊: {group_name}")
            else:
                print(f"⚠️ 群聊 {group_name} 已在监控列表中")
                
        except ValueError:
            print("❌ 输入格式错误")
    
    def remove_group(self):
        """移除监控群聊"""
        monitored = self.monitor.get_monitor_groups()
        if not monitored:
            print("⚠️ 当前没有监控任何群聊")
            return
        
        print("\n🔍 当前监控的群聊:")
        for i, group in enumerate(monitored, 1):
            print(f"  {i}. {group}")
        
        try:
            choice = input("\n请输入要移除的群聊编号: ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(monitored):
                group_name = monitored[idx]
                if self.monitor.remove_monitor_group(group_name):
                    print(f"✅ 已移除监控群聊: {group_name}")
                else:
                    print(f"❌ 移除失败")
            else:
                print("❌ 无效的编号")
                
        except ValueError:
            print("❌ 输入格式错误")
    
    def test_group_messages(self):
        """测试群聊消息"""
        if not self.monitor.wx:
            print("❌ 请先连接微信")
            return
        
        monitored = self.monitor.get_monitor_groups()
        if not monitored:
            print("⚠️ 当前没有监控任何群聊")
            return
        
        print("\n🔍 选择要测试的群聊:")
        for i, group in enumerate(monitored, 1):
            print(f"  {i}. {group}")
        
        try:
            choice = input("\n请输入群聊编号: ").strip()
            idx = int(choice) - 1
            
            if 0 <= idx < len(monitored):
                group_name = monitored[idx]
                print(f"\n正在获取群 '{group_name}' 的消息...")
                
                messages = self.monitor.get_group_messages(group_name, limit=5)
                if messages:
                    print(f"✅ 获取到 {len(messages)} 条消息:")
                    for msg in messages:
                        print(f"  [{msg.sender}]: {msg.content}")
                else:
                    print("❌ 没有获取到消息")
            else:
                print("❌ 无效的编号")
                
        except ValueError:
            print("❌ 输入格式错误")
    
    def start_monitoring(self):
        """开始监控"""
        if not self.monitor.wx:
            print("❌ 请先连接微信")
            return
        
        monitored = self.monitor.get_monitor_groups()
        if not monitored:
            print("⚠️ 当前没有监控任何群聊，请先添加群聊")
            return
        
        print(f"\n🚀 开始监控 {len(monitored)} 个群聊...")
        print("按 Ctrl+C 停止监控")
        
        try:
            self.monitor.start_monitoring()
        except KeyboardInterrupt:
            print("\n⏹️ 监控已停止")
    
    def reload_config(self):
        """重新加载配置"""
        print("正在重新加载配置文件...")
        if self.monitor.reload_config():
            print("✅ 配置重新加载成功")
            # 显示当前监控的群聊
            monitored = self.monitor.get_monitor_groups()
            if monitored:
                print(f"当前监控的群聊: {monitored}")
            else:
                print("当前没有监控任何群聊")
        else:
            print("❌ 配置重新加载失败")
    
    def run(self):
        """运行管理器"""
        while True:
            self.show_menu()
            choice = input("\n请选择操作 (0-8): ").strip()
            
            if choice == "0":
                print("👋 再见!")
                break
            elif choice == "1":
                self.connect_wechat()
            elif choice == "2":
                self.show_all_groups()
            elif choice == "3":
                self.show_monitored_groups()
            elif choice == "4":
                self.add_group()
            elif choice == "5":
                self.remove_group()
            elif choice == "6":
                self.test_group_messages()
            elif choice == "7":
                self.start_monitoring()
            elif choice == "8":
                self.reload_config()
            else:
                print("❌ 无效的选择，请重新输入")
            
            input("\n按回车键继续...")


def main():
    """主函数"""
    manager = GroupManager()
    manager.run()


if __name__ == "__main__":
    main()
