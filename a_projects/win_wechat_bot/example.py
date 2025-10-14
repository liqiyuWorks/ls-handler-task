"""
微信群监控使用示例
演示基本功能和群聊管理
"""

from wechat_monitor import WeChatGroupMonitor


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建监控器
    monitor = WeChatGroupMonitor()
    
    # 连接微信
    if not monitor.connect_wechat():
        print("连接微信失败")
        return
    
    # 显示配置文件中的监控群聊
    monitored_groups = monitor.get_monitor_groups()
    print(f"配置文件中的监控群聊: {monitored_groups}")
    
    # 获取所有群聊列表
    groups = monitor.get_group_list()
    print(f"找到 {len(groups)} 个群聊")
    
    # 如果配置文件中有监控群聊，使用它们
    if monitored_groups:
        for group_name in monitored_groups:
            print(f"\n正在获取群 '{group_name}' 的消息...")
            messages = monitor.get_group_messages(group_name, limit=3)
            for msg in messages:
                print(f"[{msg.sender}]: {msg.content}")
    else:
        # 如果没有配置，添加第一个群聊作为示例
        if groups:
            group_name = groups[0]
            monitor.add_monitor_group(group_name)
            print(f"已添加监控群聊: {group_name}")
            
            # 获取消息
            messages = monitor.get_group_messages(group_name, limit=5)
            for msg in messages:
                print(f"[{msg.sender}]: {msg.content}")


def example_group_management():
    """群聊管理示例"""
    print("\n=== 群聊管理示例 ===")
    
    monitor = WeChatGroupMonitor()
    
    # 添加监控群聊
    test_groups = ["测试群", "工作群"]
    for group in test_groups:
        if monitor.add_monitor_group(group):
            print(f"✅ 已添加: {group}")
        else:
            print(f"⚠️ 已存在: {group}")
    
    # 查看监控列表
    monitored = monitor.get_monitor_groups()
    print(f"当前监控的群聊: {monitored}")
    
    # 移除监控群聊
    if monitored:
        removed = monitor.remove_monitor_group(monitored[0])
        print(f"移除结果: {removed}")


def example_message_operations():
    """消息操作示例"""
    print("\n=== 消息操作示例 ===")
    
    monitor = WeChatGroupMonitor()
    
    if not monitor.connect_wechat():
        return
    
    groups = monitor.get_group_list()
    if not groups:
        return
    
    group_name = groups[0]
    
    # 搜索消息
    keyword = "测试"
    matched_messages = monitor.search_messages(keyword, group_name)
    print(f"搜索关键词 '{keyword}' 找到 {len(matched_messages)} 条消息")
    
    # 导出消息
    messages = monitor.get_group_messages(group_name, limit=10)
    if messages:
        monitor.export_messages_to_csv(messages, f"{group_name}_export.csv")
        print("消息已导出到CSV文件")


def example_config_management():
    """配置管理示例"""
    print("\n=== 配置管理示例 ===")
    
    monitor = WeChatGroupMonitor()
    
    # 显示当前配置
    print("当前监控的群聊:")
    monitored = monitor.get_monitor_groups()
    for group in monitored:
        print(f"  - {group}")
    
    # 重新加载配置
    print("\n重新加载配置文件...")
    if monitor.reload_config():
        print("配置重新加载成功")
        print("更新后的监控群聊:")
        for group in monitor.get_monitor_groups():
            print(f"  - {group}")
    else:
        print("配置重新加载失败")


def example_monitoring():
    """实时监控示例"""
    print("\n=== 实时监控示例 ===")
    print("注意: 这会持续运行，按 Ctrl+C 停止")
    
    monitor = WeChatGroupMonitor()
    
    if not monitor.connect_wechat():
        return
    
    # 使用配置文件中的群聊
    monitored_groups = monitor.get_monitor_groups()
    if not monitored_groups:
        print("配置文件中没有监控群聊，请先配置")
        return
    
    print(f"将监控以下群聊: {monitored_groups}")
    
    # 开始监控
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n监控已停止")


def main():
    """主函数"""
    print("微信群监控使用示例")
    print("=" * 40)
    
    try:
        example_basic_usage()
        example_group_management()
        example_message_operations()
        example_config_management()
        
        # 取消注释以启用实时监控示例
        # example_monitoring()
        
    except Exception as e:
        print(f"运行示例时出错: {e}")


if __name__ == "__main__":
    main()
