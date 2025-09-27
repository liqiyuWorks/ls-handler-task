#!/usr/bin/env python3
"""
RabbitMQ 快速启动脚本
提供简单的命令行接口来测试 RabbitMQ 连接和基本功能
"""

import sys
import argparse
import logging
from connection import RabbitMQConnection
from producer import RabbitMQProducer
from consumer import RabbitMQConsumer
from config import QUEUE_NAMES

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_connection():
    """测试连接"""
    print("🔗 测试 RabbitMQ 连接...")
    
    connection = RabbitMQConnection()
    
    try:
        if connection.connect():
            print("✅ 连接成功!")
            
            # 显示连接信息
            info = connection.get_connection_info()
            print(f"   主机: {info['host']}:{info['port']}")
            print(f"   虚拟主机: {info['virtual_host']}")
            print(f"   用户: {info['user']}")
            print(f"   连接状态: {'正常' if info['is_connected'] else '异常'}")
            
            return True
        else:
            print("❌ 连接失败!")
            return False
            
    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def send_test_message():
    """发送测试消息"""
    print("📤 发送测试消息...")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法发送消息")
            return False
        
        # 发送测试消息
        test_message = {
            "type": "test_message",
            "content": "Hello from RabbitMQ toolkit!",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        success = producer.send_message(test_message, QUEUE_NAMES["DEFAULT"])
        
        if success:
            print("✅ 测试消息发送成功!")
            
            # 显示队列信息
            queue_info = producer.get_queue_info(QUEUE_NAMES["DEFAULT"])
            if queue_info:
                print(f"   队列: {queue_info['queue_name']}")
                print(f"   消息数量: {queue_info['message_count']}")
                print(f"   消费者数量: {queue_info['consumer_count']}")
            
            return True
        else:
            print("❌ 测试消息发送失败!")
            return False
            
    except Exception as e:
        print(f"❌ 发送消息异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def receive_test_message():
    """接收测试消息"""
    print("📥 接收测试消息...")
    
    connection = RabbitMQConnection()
    consumer = RabbitMQConsumer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法接收消息")
            return False
        
        # 设置消息处理器
        received_count = 0
        
        def handle_message(message: str) -> bool:
            nonlocal received_count
            received_count += 1
            print(f"✅ 收到第 {received_count} 条消息: {message[:100]}...")
            return True
        
        consumer.set_text_handler(QUEUE_NAMES["DEFAULT"], handle_message)
        
        # 启动消费者
        if consumer.start_consuming(QUEUE_NAMES["DEFAULT"]):
            print("✅ 消费者启动成功，等待消息...")
            
            # 运行 10 秒
            consumer.run_with_timeout(10)
            
            if received_count > 0:
                print(f"✅ 成功接收 {received_count} 条消息!")
                return True
            else:
                print("⚠️  未收到任何消息")
                return False
        else:
            print("❌ 消费者启动失败!")
            return False
            
    except Exception as e:
        print(f"❌ 接收消息异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def send_business_data():
    """发送业务数据示例"""
    print("🚢 发送业务数据示例...")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法发送业务数据")
            return False
        
        # 发送重油数据
        fuel_data = {
            "vessel_id": "OCEAN_VESSEL_001",
            "fuel_type": "heavy_oil",
            "consumption_rate": 28.5,
            "temperature": 45.2,
            "density": 0.95,
            "sulfur_content": 3.2
        }
        
        success1 = producer.send_heavy_oil_data("OCEAN_VESSEL_001", fuel_data)
        print(f"重油数据发送: {'✅ 成功' if success1 else '❌ 失败'}")
        
        # 发送船舶性能数据
        performance_data = {
            "speed": 12.5,
            "fuel_consumption": 25.3,
            "engine_rpm": 1200,
            "weather_condition": "good"
        }
        
        success2 = producer.send_vessel_performance_data("OCEAN_VESSEL_001", performance_data)
        print(f"性能数据发送: {'✅ 成功' if success2 else '❌ 失败'}")
        
        # 发送天气数据
        weather_data = {
            "location": "Shanghai",
            "temperature": 22.5,
            "humidity": 65,
            "wind_speed": 15.2,
            "pressure": 1013.25
        }
        
        success3 = producer.send_weather_data(weather_data)
        print(f"天气数据发送: {'✅ 成功' if success3 else '❌ 失败'}")
        
        return success1 and success2 and success3
        
    except Exception as e:
        print(f"❌ 发送业务数据异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def show_queue_info():
    """显示队列信息"""
    print("📊 显示队列信息...")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("❌ 连接失败，无法获取队列信息")
            return False
        
        print("队列信息:")
        
        for queue_type, queue_name in QUEUE_NAMES.items():
            queue_info = producer.get_queue_info(queue_name)
            if queue_info:
                print(f"  {queue_type}: {queue_name}")
                print(f"    消息数量: {queue_info['message_count']}")
                print(f"    消费者数量: {queue_info['consumer_count']}")
            else:
                print(f"  {queue_type}: {queue_name} (队列不存在)")
        
        return True
        
    except Exception as e:
        print(f"❌ 获取队列信息异常: {str(e)}")
        return False
    finally:
        connection.disconnect()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RabbitMQ 快速启动工具")
    parser.add_argument(
        "action",
        choices=["test", "send", "receive", "business", "info", "all"],
        help="要执行的操作"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细日志"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("🐰 RabbitMQ 快速启动工具")
    print("=" * 40)
    
    success = False
    
    if args.action == "test":
        success = test_connection()
    elif args.action == "send":
        success = send_test_message()
    elif args.action == "receive":
        success = receive_test_message()
    elif args.action == "business":
        success = send_business_data()
    elif args.action == "info":
        success = show_queue_info()
    elif args.action == "all":
        print("🔄 执行完整测试流程...")
        
        results = []
        results.append(("连接测试", test_connection()))
        results.append(("发送消息", send_test_message()))
        results.append(("队列信息", show_queue_info()))
        results.append(("业务数据", send_business_data()))
        
        print("\n📋 测试结果:")
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")
        
        success = all(result for _, result in results)
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 操作完成!")
        sys.exit(0)
    else:
        print("⚠️  操作失败，请检查配置和连接")
        sys.exit(1)


if __name__ == "__main__":
    main()
