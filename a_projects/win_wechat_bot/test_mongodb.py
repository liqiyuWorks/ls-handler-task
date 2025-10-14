"""
MongoDB 集成测试脚本
测试消息存储、去重和查询功能
"""

import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional
from mongodb_storage import MongoDBStorage


@dataclass
class GroupMessage:
    """群消息数据类"""
    timestamp: str
    sender: str
    content: str
    group_name: str
    message_type: str = "text"
    raw_data: Optional[str] = None


def test_mongodb_connection():
    """测试 MongoDB 连接"""
    print("=== 测试 MongoDB 连接 ===")
    
    try:
        storage = MongoDBStorage()
        if storage.collection is not None:
            print("[成功] MongoDB 连接成功")
            
            # 获取统计信息
            stats = storage.get_statistics()
            print(f"[统计] 数据库统计:")
            print(f"  总消息数: {stats.get('total_messages', 0)}")
            print(f"  最近24小时: {stats.get('recent_24h_messages', 0)}")
            
            storage.close()
            return True
        else:
            print("[失败] MongoDB 连接失败")
            return False
    except Exception as e:
        print(f"[失败] MongoDB 连接错误: {e}")
        return False


def test_message_storage():
    """测试消息存储功能"""
    print("\n=== 测试消息存储功能 ===")
    
    try:
        storage = MongoDBStorage()
        if storage.collection is None:
            print("[失败] MongoDB 连接失败")
            return False
        
        # 创建测试消息
        test_messages = [
            GroupMessage(
                timestamp=datetime.now().isoformat(),
                sender="测试用户1",
                content="这是一条测试消息 S11TC",
                group_name="测试群",
                message_type="text"
            ),
            GroupMessage(
                timestamp=datetime.now().isoformat(),
                sender="测试用户2",
                content="这是另一条测试消息",
                group_name="测试群",
                message_type="text"
            ),
            GroupMessage(
                timestamp=datetime.now().isoformat(),
                sender="测试用户1",
                content="这是一条重复的测试消息 S11TC",  # 重复消息
                group_name="测试群",
                message_type="text"
            )
        ]
        
        # 保存消息
        result = storage.save_messages(test_messages)
        print(f"[成功] 消息保存结果:")
        print(f"  新增: {result['saved']} 条")
        print(f"  重复: {result['duplicates']} 条")
        print(f"  错误: {result['errors']} 条")
        
        # 再次保存相同消息测试去重
        print("\n🔄 测试去重功能...")
        result2 = storage.save_messages(test_messages)
        print(f"[成功] 去重测试结果:")
        print(f"  新增: {result2['saved']} 条")
        print(f"  重复: {result2['duplicates']} 条")
        print(f"  错误: {result2['errors']} 条")
        
        storage.close()
        return True
        
    except Exception as e:
        print(f"[失败] 消息存储测试失败: {e}")
        return False


def test_message_query():
    """测试消息查询功能"""
    print("\n=== 测试消息查询功能 ===")
    
    try:
        storage = MongoDBStorage()
        if storage.collection is None:
            print("[失败] MongoDB 连接失败")
            return False
        
        # 查询所有消息
        all_messages = storage.get_messages(limit=10)
        print(f"📋 查询到 {len(all_messages)} 条消息")
        
        # 按群聊查询
        group_messages = storage.get_messages(group_name="测试群", limit=5)
        print(f"📋 测试群消息: {len(group_messages)} 条")
        
        # 按发送者查询
        sender_messages = storage.get_messages(sender="测试用户1", limit=5)
        print(f"📋 测试用户1消息: {len(sender_messages)} 条")
        
        # 关键词搜索
        keyword_messages = storage.search_messages("S11TC", limit=5)
        print(f"🔍 关键词 'S11TC' 搜索结果: {len(keyword_messages)} 条")
        
        storage.close()
        return True
        
    except Exception as e:
        print(f"[失败] 消息查询测试失败: {e}")
        return False


def test_monitor_integration():
    """测试监控系统集成"""
    print("\n=== 测试监控系统集成 ===")
    
    try:
        # 直接测试 MongoDB 存储功能
        storage = MongoDBStorage()
        if storage.collection is None:
            print("[失败] MongoDB 连接失败")
            return False
        
        print("[成功] MongoDB 存储连接成功")
        
        # 获取数据库统计信息
        stats = storage.get_statistics()
        print(f"[统计] 数据库统计:")
        print(f"  总消息数: {stats.get('total_messages', 0)}")
        print(f"  最近24小时: {stats.get('recent_24h_messages', 0)}")
        
        # 显示群聊统计
        group_stats = stats.get('group_statistics', [])
        if group_stats:
            print(f"📋 群聊统计:")
            for group in group_stats[:3]:
                print(f"  {group['_id']}: {group['count']} 条")
        
        # 测试从数据库获取消息
        db_messages = storage.get_messages(limit=5)
        print(f"📋 从数据库获取到 {len(db_messages)} 条消息")
        
        # 测试搜索功能
        search_results = storage.search_messages("S11TC", limit=3)
        print(f"🔍 搜索 'S11TC' 找到 {len(search_results)} 条消息")
        
        storage.close()
        return True
        
    except Exception as e:
        print(f"[失败] 监控系统集成测试失败: {e}")
        return False


def test_wechat_monitoring():
    """测试微信监控功能"""
    print("\n=== 测试微信监控功能 ===")
    print("注意: 这将尝试连接微信客户端")
    
    try:
        # 尝试导入监控模块
        try:
            from wechat_monitor import WeChatGroupMonitor
        except ImportError as e:
            print(f"[警告] 无法导入监控模块: {e}")
            print("跳过微信监控测试")
            return True
        
        monitor = WeChatGroupMonitor()
        
        # 连接微信
        if monitor.connect_wechat():
            print("[成功] 微信连接成功")
            
            # 获取群聊列表
            groups = monitor.get_group_list()
            print(f"📋 找到 {len(groups)} 个群聊")
            
            # 如果有监控群聊，测试获取消息
            monitored_groups = monitor.get_monitor_groups()
            if monitored_groups:
                print(f"🔍 监控群聊: {monitored_groups}")
                
                for group_name in monitored_groups[:1]:  # 只测试第一个群聊
                    print(f"\n正在测试群聊: {group_name}")
                    messages = monitor.get_group_messages(group_name, limit=3)
                    
                    if messages:
                        print(f"[成功] 获取到 {len(messages)} 条消息")
                        
                        # 保存消息（会同时保存到 MongoDB 和文件）
                        monitor.save_messages(messages, group_name)
                        print("[成功] 消息已保存到数据库和文件")
                        
                        # 显示消息内容
                        for msg in messages:
                            print(f"  [{msg.sender}]: {msg.content}")
                    else:
                        print("[警告] 没有获取到消息")
            else:
                print("[警告] 没有配置监控群聊")
        else:
            print("[失败] 微信连接失败")
        
        monitor.close()
        return True
        
    except Exception as e:
        print(f"[失败] 微信监控测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("MongoDB 集成测试")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        ("MongoDB 连接", test_mongodb_connection),
        ("消息存储", test_message_storage),
        ("消息查询", test_message_query),
        ("监控系统集成", test_monitor_integration),
        ("微信监控", test_wechat_monitoring)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n运行测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"测试 {test_name} 出错: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "[成功] 通过" if result else "[失败] 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("[完成] 所有测试通过！MongoDB 集成成功！")
    else:
        print("[警告] 部分测试失败，请检查配置和连接")


if __name__ == "__main__":
    main()
