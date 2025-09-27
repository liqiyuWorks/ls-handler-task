"""
RabbitMQ 连接测试脚本
用于测试 RabbitMQ 连接和基本功能
"""

import sys
import time
from connection import RabbitMQConnection
from producer import RabbitMQProducer
from consumer import RabbitMQConsumer
from config import QUEUE_NAMES, get_connection_info

def test_connection():
    """测试 RabbitMQ 连接"""
    print("=== RabbitMQ 连接测试 ===")
    
    connection = RabbitMQConnection()
    
    try:
        # 测试连接
        print("正在测试连接...")
        if connection.connect():
            print("✅ 连接成功!")
            
            # 获取连接信息
            info = connection.get_connection_info()
            print(f"连接信息:")
            for key, value in info.items():
                print(f"  {key}: {value}")
            
            # 测试连接状态
            print(f"\n连接状态: {'✅ 正常' if connection.is_connected() else '❌ 异常'}")
            
            return True
        else:
            print("❌ 连接失败!")
            return False
            
    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")
        return False
    finally:
        connection.disconnect()
        print("连接已断开")


def test_producer():
    """测试生产者"""
    print("\n=== RabbitMQ 生产者测试 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法测试生产者")
            return False
        
        print("✅ 生产者连接成功")
        
        # 测试发送消息
        test_message = {
            "test": "connection_test",
            "timestamp": time.time(),
            "message": "这是一条测试消息"
        }
        
        success = producer.send_message(test_message, QUEUE_NAMES["DEFAULT"])
        
        if success:
            print("✅ 消息发送成功")
            
            # 获取队列信息
            queue_info = producer.get_queue_info(QUEUE_NAMES["DEFAULT"])
            if queue_info:
                print(f"队列信息: {queue_info}")
            
            return True
        else:
            print("❌ 消息发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 生产者测试异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def test_consumer():
    """测试消费者"""
    print("\n=== RabbitMQ 消费者测试 ===")
    
    connection = RabbitMQConnection()
    consumer = RabbitMQConsumer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法测试消费者")
            return False
        
        print("✅ 消费者连接成功")
        
        # 设置消息处理器
        received_messages = []
        
        def test_handler(message: str) -> bool:
            received_messages.append(message)
            print(f"✅ 收到消息: {message}")
            return True
        
        consumer.set_text_handler(QUEUE_NAMES["DEFAULT"], test_handler)
        
        # 启动消费者
        if consumer.start_consuming(QUEUE_NAMES["DEFAULT"]):
            print("✅ 消费者启动成功")
            
            # 运行 5 秒
            consumer.run_with_timeout(5)
            
            print(f"测试期间收到 {len(received_messages)} 条消息")
            return True
        else:
            print("❌ 消费者启动失败")
            return False
            
    except Exception as e:
        print(f"❌ 消费者测试异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def test_end_to_end():
    """端到端测试"""
    print("\n=== RabbitMQ 端到端测试 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    consumer = RabbitMQConsumer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法进行端到端测试")
            return False
        
        print("✅ 连接成功，开始端到端测试")
        
        # 设置消费者
        received_count = 0
        
        def count_handler(message: str) -> bool:
            nonlocal received_count
            received_count += 1
            print(f"收到第 {received_count} 条消息")
            return True
        
        consumer.set_text_handler(QUEUE_NAMES["DEFAULT"], count_handler)
        
        # 启动消费者
        if not consumer.start_consuming(QUEUE_NAMES["DEFAULT"]):
            print("❌ 消费者启动失败")
            return False
        
        print("✅ 消费者启动成功")
        
        # 发送测试消息
        test_messages = [
            "端到端测试消息 1",
            "端到端测试消息 2", 
            "端到端测试消息 3"
        ]
        
        print("发送测试消息...")
        for i, msg in enumerate(test_messages):
            success = producer.send_message(msg, QUEUE_NAMES["DEFAULT"])
            if success:
                print(f"✅ 消息 {i+1} 发送成功")
            else:
                print(f"❌ 消息 {i+1} 发送失败")
        
        # 等待消息处理
        print("等待消息处理...")
        time.sleep(3)
        
        # 停止消费者
        consumer.stop_consuming()
        
        # 检查结果
        if received_count == len(test_messages):
            print(f"✅ 端到端测试成功！发送 {len(test_messages)} 条，收到 {received_count} 条")
            return True
        else:
            print(f"❌ 端到端测试失败！发送 {len(test_messages)} 条，收到 {received_count} 条")
            return False
            
    except Exception as e:
        print(f"❌ 端到端测试异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def main():
    """主测试函数"""
    print("RabbitMQ 连接和功能测试")
    print("=" * 50)
    
    # 显示配置信息
    print("当前配置:")
    config_info = get_connection_info()
    for key, value in config_info.items():
        print(f"  {key}: {value}")
    print()
    
    # 运行测试
    tests = [
        ("连接测试", test_connection),
        ("生产者测试", test_producer),
        ("消费者测试", test_consumer),
        ("端到端测试", test_end_to_end),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"\n开始 {test_name}...")
            result = test_func()
            results[test_name] = result
            print(f"{test_name} {'通过' if result else '失败'}")
        except Exception as e:
            print(f"{test_name} 异常: {str(e)}")
            results[test_name] = False
        
        time.sleep(1)  # 测试间暂停
    
    # 显示测试结果摘要
    print("\n" + "=" * 50)
    print("测试结果摘要:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！RabbitMQ 连接和功能正常。")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败，请检查 RabbitMQ 连接和配置。")
        sys.exit(1)


if __name__ == "__main__":
    main()
