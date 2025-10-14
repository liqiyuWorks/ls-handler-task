"""
微信群监控快速开始脚本
最简单的使用方式，适合快速测试
"""

from wechat_monitor import WeChatGroupMonitor


def quick_start():
    """快速开始 - 最简单的使用方式"""
    print("微信群监控 - 快速开始")
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
    
    # 3. 获取群聊列表
    print("\n正在获取群聊列表...")
    groups = monitor.get_group_list()
    
    if not groups:
        print("❌ 没有找到群聊")
        return
    
    print(f"✅ 找到 {len(groups)} 个群聊:")
    for i, group in enumerate(groups, 1):
        print(f"   {i}. {group}")
    
    # 4. 获取第一个群的消息
    if groups:
        group_name = groups[0]
        print(f"\n正在获取群 '{group_name}' 的消息...")
        
        messages = monitor.get_group_messages(group_name, limit=5)
        
        if messages:
            print(f"✅ 获取到 {len(messages)} 条消息:")
            for msg in messages:
                print(f"   [{msg.sender}]: {msg.content}")
        else:
            print("❌ 没有获取到消息")
    
    print("\n🎉 快速开始完成！")
    print("\n下一步可以：")
    print("1. 修改 config.json 配置要监控的群聊")
    print("2. 运行 example_usage.py 查看更多示例")
    print("3. 运行 python wechat_group_monitor.py 开始监控")


if __name__ == "__main__":
    quick_start()
