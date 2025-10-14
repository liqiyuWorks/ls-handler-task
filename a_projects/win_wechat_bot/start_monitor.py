"""
微信群监控启动脚本
直接启动监控功能
"""

from wechat_monitor import WeChatGroupMonitor


def main():
    """启动监控"""
    print("微信群监控系统启动中...")
    print("=" * 40)
    
    # 创建监控器
    monitor = WeChatGroupMonitor()
    
    # 显示配置信息
    print(f"监控群聊: {list(monitor.monitored_groups)}")
    print(f"检查间隔: {monitor.config.get('check_interval', 60)} 秒")
    print(f"关键词过滤: {monitor.config['message_filters']['keywords']}")
    print(f"MongoDB 存储: {'启用' if monitor.mongodb_storage else '禁用'}")
    
    # 连接微信
    print("\n正在连接微信客户端...")
    if not monitor.connect_wechat():
        print("❌ 连接失败！请确保：")
        print("   1. 微信客户端已打开")
        print("   2. 已登录微信账号")
        return
    
    print("✅ 微信连接成功！")
    
    # 显示跟踪状态
    stats = monitor.get_tracking_stats()
    print(f"已处理消息数: {stats['processed_messages_count']}")
    
    # 开始监控
    print("\n开始监控... (按 Ctrl+C 停止)")
    print("-" * 40)
    
    try:
        monitor.start_monitoring()
    except KeyboardInterrupt:
        print("\n\n监控已停止")
    except Exception as e:
        print(f"\n监控出错: {e}")
    finally:
        monitor.close()
        print("监控器已关闭")


if __name__ == "__main__":
    main()
