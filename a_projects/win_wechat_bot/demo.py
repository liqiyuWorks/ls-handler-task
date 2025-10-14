"""
微信群监控演示脚本
提供基本使用示例和快速开始功能
"""

from wechat_monitor import WeChatGroupMonitor


def quick_demo():
    """快速演示 - 最简单的使用方式"""
    print("微信群监控 - 快速演示")
    print("=" * 30)
    
    # 1. 创建监控器
    monitor = WeChatGroupMonitor()
    
    # 2. 连接微信
    print("正在连接微信客户端...")
    if not monitor.connect_wechat():
        print("❌ 连接失败！请确保：")
        print("   1. 微信客户端已打开")
        print("   2. 已登录微信账号")
        print("   3. 已安装 wxauto 库: pip install wxauto")
        return
    
    print("✅ 微信连接成功！")
    
    # 3. 显示配置的监控群聊
    monitored_groups = monitor.get_monitor_groups()
    print(f"\n配置的监控群聊: {monitored_groups}")
    
    # 4. 获取群聊列表
    print("\n正在获取群聊列表...")
    groups = monitor.get_group_list()
    
    if not groups:
        print("❌ 没有找到群聊")
        return
    
    print(f"✅ 找到 {len(groups)} 个群聊:")
    for i, group in enumerate(groups[:5], 1):  # 只显示前5个
        print(f"   {i}. {group}")
    
    # 5. 测试消息获取
    if monitored_groups:
        group_name = monitored_groups[0]
        print(f"\n正在测试群 '{group_name}' 的消息获取...")
        
        messages = monitor.get_group_messages(group_name, limit=3)
        
        if messages:
            print(f"✅ 获取到 {len(messages)} 条消息:")
            for msg in messages:
                print(f"   [{msg.sender}]: {msg.content[:50]}...")
        else:
            print("❌ 没有获取到消息")
    else:
        print("\n⚠️ 没有配置监控群聊")
        print("请修改 config.json 文件中的 monitor_groups 配置")
    
    # 6. 显示数据库统计
    if monitor.mongodb_storage:
        print(f"\n📊 数据库统计:")
        stats = monitor.get_database_statistics()
        if "error" not in stats:
            print(f"   总消息数: {stats.get('total_messages', 0)}")
            print(f"   最近24小时: {stats.get('recent_24h_messages', 0)}")
        else:
            print(f"   数据库错误: {stats['error']}")
    
    monitor.close()
    print("\n🎉 演示完成！")
    print("\n下一步可以：")
    print("1. 修改 config.json 配置要监控的群聊")
    print("2. 运行 python group_manager.py 启动群聊管理工具")
    print("3. 运行 python wechat_monitor.py 开始持续监控")


def test_message_filtering():
    """测试消息过滤功能"""
    print("\n=== 测试消息过滤功能 ===")
    
    monitor = WeChatGroupMonitor()
    
    if not monitor.connect_wechat():
        print("连接微信失败")
        return
    
    # 显示过滤配置
    filters = monitor.config['message_filters']
    print(f"关键词过滤: {filters['keywords']}")
    print(f"排除关键词: {filters['exclude_keywords']}")
    
    # 测试消息获取
    monitored_groups = monitor.get_monitor_groups()
    if monitored_groups:
        group_name = monitored_groups[0]
        print(f"\n测试群聊: {group_name}")
        
        messages = monitor.get_group_messages(group_name, limit=5)
        print(f"获取到 {len(messages)} 条过滤后的消息")
        
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. [{msg.sender}] {msg.content[:50]}...")
    
    monitor.close()


def show_tracking_stats():
    """显示消息跟踪统计"""
    print("\n=== 消息跟踪统计 ===")
    
    monitor = WeChatGroupMonitor()
    
    if not monitor.connect_wechat():
        print("连接微信失败")
        return
    
    stats = monitor.get_tracking_stats()
    print(f"已处理消息数: {stats['processed_messages_count']}")
    print(f"跟踪的群聊: {stats['tracked_groups']}")
    
    if stats['last_timestamps']:
        print("最后获取时间:")
        for group, timestamp in stats['last_timestamps'].items():
            print(f"  {group}: {timestamp}")
    
    monitor.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "filter":
            test_message_filtering()
        elif command == "stats":
            show_tracking_stats()
        else:
            print("可用命令:")
            print("  python demo.py          - 快速演示")
            print("  python demo.py filter   - 测试消息过滤")
            print("  python demo.py stats    - 显示跟踪统计")
    else:
        quick_demo()
