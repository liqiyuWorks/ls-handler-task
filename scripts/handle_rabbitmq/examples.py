"""
RabbitMQ 使用示例和测试代码
包含各种使用场景的示例
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

from connection import RabbitMQConnection
from producer import RabbitMQProducer
from consumer import RabbitMQConsumer, JsonMessageHandler, TextMessageHandler
from config import QUEUE_NAMES, EXCHANGE_NAMES

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_producer():
    """基本生产者示例"""
    print("\n=== 基本生产者示例 ===")
    
    # 创建连接和生产者
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        # 连接 RabbitMQ
        if not connection.connect():
            print("连接失败")
            return
        
        # 发送简单消息
        message = {"message": "Hello RabbitMQ!", "timestamp": datetime.now().isoformat()}
        success = producer.send_message(message, QUEUE_NAMES["DEFAULT"])
        
        if success:
            print("消息发送成功")
        else:
            print("消息发送失败")
            
    finally:
        connection.disconnect()


def example_basic_consumer():
    """基本消费者示例"""
    print("\n=== 基本消费者示例 ===")
    
    # 创建连接和消费者
    connection = RabbitMQConnection()
    consumer = RabbitMQConsumer(connection)
    
    try:
        # 连接 RabbitMQ
        if not connection.connect():
            print("连接失败")
            return
        
        # 设置消息处理器
        def handle_message(message: str) -> bool:
            print(f"收到消息: {message}")
            return True
        
        consumer.set_text_handler(QUEUE_NAMES["DEFAULT"], handle_message)
        
        # 开始消费
        if consumer.start_consuming(QUEUE_NAMES["DEFAULT"]):
            print("开始消费消息...")
            # 运行 10 秒
            consumer.run_with_timeout(10)
        else:
            print("启动消费者失败")
            
    finally:
        connection.disconnect()


def example_json_producer_consumer():
    """JSON 消息生产者和消费者示例"""
    print("\n=== JSON 消息示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    consumer = RabbitMQConsumer(connection)
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 设置 JSON 消息处理器
        def handle_json_message(data: Dict[str, Any]) -> bool:
            print(f"收到 JSON 消息: {json.dumps(data, ensure_ascii=False, indent=2)}")
            return True
        
        consumer.set_json_handler(QUEUE_NAMES["VESSEL_PERFORMANCE"], handle_json_message)
        
        # 启动消费者
        if consumer.start_consuming(QUEUE_NAMES["VESSEL_PERFORMANCE"]):
            print("JSON 消费者已启动")
            
            # 发送 JSON 消息
            vessel_data = {
                "vessel_id": "VESSEL_001",
                "timestamp": datetime.now().isoformat(),
                "performance": {
                    "speed": 12.5,
                    "fuel_consumption": 25.3,
                    "engine_rpm": 1200,
                    "weather_condition": "good"
                }
            }
            
            success = producer.send_message(vessel_data, QUEUE_NAMES["VESSEL_PERFORMANCE"])
            print(f"JSON 消息发送{'成功' if success else '失败'}")
            
            # 运行 5 秒
            consumer.run_with_timeout(5)
            
    finally:
        connection.disconnect()


def example_heavy_oil_data():
    """重油数据示例"""
    print("\n=== 重油数据示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 发送重油数据
        fuel_data = {
            "vessel_id": "OCEAN_VESSEL_001",
            "fuel_type": "heavy_oil",
            "consumption_rate": 28.5,
            "temperature": 45.2,
            "density": 0.95,
            "sulfur_content": 3.2,
            "location": {
                "latitude": 31.2304,
                "longitude": 121.4737
            }
        }
        
        success = producer.send_heavy_oil_data("OCEAN_VESSEL_001", fuel_data)
        print(f"重油数据发送{'成功' if success else '失败'}")
        
        # 获取队列信息
        queue_info = producer.get_queue_info(QUEUE_NAMES["HEAVY_OIL"])
        if queue_info:
            print(f"重油队列信息: {queue_info}")
            
    finally:
        connection.disconnect()


def example_weather_data():
    """天气数据示例"""
    print("\n=== 天气数据示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 发送天气数据
        weather_data = {
            "location": "Shanghai",
            "temperature": 22.5,
            "humidity": 65,
            "wind_speed": 15.2,
            "wind_direction": "NNE",
            "pressure": 1013.25,
            "visibility": 10,
            "weather_condition": "partly_cloudy",
            "forecast": [
                {"time": "2024-01-01T12:00:00", "temperature": 24, "condition": "sunny"},
                {"time": "2024-01-01T18:00:00", "temperature": 20, "condition": "cloudy"}
            ]
        }
        
        success = producer.send_weather_data(weather_data)
        print(f"天气数据发送{'成功' if success else '失败'}")
        
    finally:
        connection.disconnect()


def example_typhoon_data():
    """台风数据示例"""
    print("\n=== 台风数据示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 发送台风数据
        typhoon_data = {
            "typhoon_id": "TYPHOON_2024_001",
            "name": "Typhoon Maria",
            "category": 3,
            "center_position": {
                "latitude": 25.5,
                "longitude": 130.2
            },
            "wind_speed": 45,  # m/s
            "pressure": 950,   # hPa
            "movement": {
                "speed": 25,   # km/h
                "direction": "NW"
            },
            "forecast_path": [
                {"time": "2024-01-01T00:00:00", "lat": 25.5, "lon": 130.2},
                {"time": "2024-01-01T06:00:00", "lat": 26.0, "lon": 129.5},
                {"time": "2024-01-01T12:00:00", "lat": 26.5, "lon": 128.8}
            ]
        }
        
        success = producer.send_typhoon_data(typhoon_data)
        print(f"台风数据发送{'成功' if success else '失败'}")
        
    finally:
        connection.disconnect()


def example_batch_messages():
    """批量消息示例"""
    print("\n=== 批量消息示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 准备批量消息
        messages = []
        for i in range(10):
            message = {
                "batch_id": f"BATCH_{i:03d}",
                "message": f"批量消息 {i+1}",
                "timestamp": datetime.now().isoformat(),
                "sequence": i+1
            }
            messages.append(message)
        
        # 批量发送
        results = producer.send_batch_messages(messages, QUEUE_NAMES["DEFAULT"])
        print(f"批量发送结果: 成功 {results['success']} 条, 失败 {results['failed']} 条")
        
    finally:
        connection.disconnect()


def example_exchange_routing():
    """交换机路由示例"""
    print("\n=== 交换机路由示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 声明交换机
        exchange_name = EXCHANGE_NAMES["TOPIC"]
        producer.declare_exchange(exchange_name, "topic")
        
        # 声明队列并绑定
        queue_name = "ocean.weather.alerts"
        producer.declare_queue(queue_name)
        producer.bind_queue_to_exchange(queue_name, exchange_name, "weather.alert.*")
        
        # 发送路由消息
        alert_data = {
            "alert_type": "storm_warning",
            "severity": "high",
            "message": "台风预警：预计未来24小时将有强台风影响",
            "affected_areas": ["Shanghai", "Ningbo", "Zhoushan"],
            "timestamp": datetime.now().isoformat()
        }
        
        success = producer.send_message_to_exchange(
            alert_data, 
            exchange_name, 
            "weather.alert.storm",
            declare_exchange=False
        )
        
        print(f"路由消息发送{'成功' if success else '失败'}")
        
    finally:
        connection.disconnect()


def example_connection_pool():
    """连接池示例"""
    print("\n=== 连接池示例 ===")
    
    from connection import RabbitMQConnectionPool
    
    # 创建连接池
    pool = RabbitMQConnectionPool(max_connections=3)
    
    try:
        # 获取连接
        conn1 = pool.get_connection()
        conn2 = pool.get_connection()
        
        print(f"连接1状态: {conn1.is_connected()}")
        print(f"连接2状态: {conn2.is_connected()}")
        
        # 归还连接
        pool.return_connection(conn1)
        pool.return_connection(conn2)
        
        print("连接已归还到池中")
        
    finally:
        pool.close_all()


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    connection = RabbitMQConnection()
    producer = RabbitMQProducer(connection)
    
    try:
        # 尝试发送到不存在的队列（不自动声明）
        message = {"test": "error handling"}
        success = producer.send_message(message, "non_existent_queue", declare_queue=False)
        print(f"发送到不存在队列: {'成功' if success else '失败'}")
        
        # 尝试发送无效 JSON
        invalid_message = "这不是有效的JSON"
        success = producer.send_message(invalid_message, QUEUE_NAMES["DEFAULT"])
        print(f"发送无效消息: {'成功' if success else '失败'}")
        
    except Exception as e:
        print(f"捕获异常: {str(e)}")
    finally:
        connection.disconnect()


def example_consumer_with_business_logic():
    """带业务逻辑的消费者示例"""
    print("\n=== 业务逻辑消费者示例 ===")
    
    connection = RabbitMQConnection()
    consumer = RabbitMQConsumer(connection)
    
    def process_heavy_oil_data(data: Dict[str, Any]) -> bool:
        """处理重油数据的业务逻辑"""
        try:
            vessel_id = data.get('vessel_id')
            fuel_data = data.get('data', {})
            
            print(f"处理船舶 {vessel_id} 的重油数据:")
            print(f"  燃料消耗率: {fuel_data.get('consumption_rate', 'N/A')} L/h")
            print(f"  温度: {fuel_data.get('temperature', 'N/A')} °C")
            print(f"  密度: {fuel_data.get('density', 'N/A')}")
            print(f"  硫含量: {fuel_data.get('sulfur_content', 'N/A')}%")
            
            # 模拟业务处理
            time.sleep(0.5)
            
            # 检查数据有效性
            if fuel_data.get('consumption_rate', 0) > 50:
                print("  ⚠️  警告：燃料消耗率过高")
                return False  # 处理失败，消息将重新入队
            
            print("  ✅ 数据处理成功")
            return True
            
        except Exception as e:
            print(f"  ❌ 处理失败: {str(e)}")
            return False
    
    try:
        if not connection.connect():
            print("连接失败")
            return
        
        # 设置处理器
        consumer.set_json_handler(QUEUE_NAMES["HEAVY_OIL"], process_heavy_oil_data)
        
        # 启动消费者
        if consumer.start_consuming(QUEUE_NAMES["HEAVY_OIL"]):
            print("业务逻辑消费者已启动，等待消息...")
            consumer.run_with_timeout(10)
        
    finally:
        connection.disconnect()


def run_all_examples():
    """运行所有示例"""
    examples = [
        example_basic_producer,
        example_basic_consumer,
        example_json_producer_consumer,
        example_heavy_oil_data,
        example_weather_data,
        example_typhoon_data,
        example_batch_messages,
        example_exchange_routing,
        example_connection_pool,
        example_error_handling,
        example_consumer_with_business_logic,
    ]
    
    for example in examples:
        try:
            example()
            time.sleep(1)  # 示例间暂停
        except Exception as e:
            print(f"示例 {example.__name__} 执行失败: {str(e)}")
        print("-" * 50)


if __name__ == "__main__":
    print("RabbitMQ 使用示例")
    print("=" * 50)
    
    # 运行所有示例
    run_all_examples()
    
    print("\n所有示例执行完成！")
