#!/usr/bin/env python3
"""
智能航运监控系统使用示例
演示如何配置和使用船舶监控功能
"""

import json
from vessel_warn import VesselMonitor, VesselConfig


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建监控器
    monitor = VesselMonitor()
    
    # 添加单艘船舶
    vessel = VesselConfig(
        mmsi="367560102",
        name="货轮001",
        speed_threshold=1.0,      # 停航阈值
        slow_down_threshold=5.0,  # 降速阈值
        normal_speed=12.0,        # 正常航速
        check_interval=30,        # 检查间隔30秒
        alert_cooldown=300        # 预警冷却5分钟
    )
    
    monitor.add_vessel(vessel)
    print(f"已添加船舶: {vessel.name} (MMSI: {vessel.mmsi})")


def example_config_file_usage():
    """配置文件使用示例"""
    print("\n=== 配置文件使用示例 ===")
    
    try:
        # 加载配置文件
        with open('vessel_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        monitor = VesselMonitor()
        
        # 从配置文件添加船舶
        for vessel_data in config['vessels']:
            vessel = VesselConfig(**vessel_data)
            monitor.add_vessel(vessel)
            print(f"已添加船舶: {vessel.name} (MMSI: {vessel.mmsi})")
        
        print(f"总共监控 {len(monitor.vessels)} 艘船舶")
        
    except FileNotFoundError:
        print("配置文件 vessel_config.json 不存在")
    except json.JSONDecodeError as e:
        print(f"配置文件格式错误: {e}")


def example_monitoring_summary():
    """监控摘要示例"""
    print("\n=== 监控摘要示例 ===")
    
    monitor = VesselMonitor()
    
    # 添加示例船舶
    vessels = [
        VesselConfig(mmsi="367560102", name="货轮001"),
        VesselConfig(mmsi="414281000", name="货轮002"),
    ]
    
    for vessel in vessels:
        monitor.add_vessel(vessel)
    
    # 模拟获取一些数据
    for mmsi in monitor.vessels.keys():
        status = monitor.get_vessel_data(mmsi)
        if status:
            monitor.vessel_status[mmsi] = status
    
    # 获取监控摘要
    summary = monitor.get_monitoring_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def example_custom_configuration():
    """自定义配置示例"""
    print("\n=== 自定义配置示例 ===")
    
    monitor = VesselMonitor()
    
    # 不同类型的船舶配置
    configurations = [
        # 货轮 - 正常监控
        VesselConfig(
            mmsi="123456789",
            name="货轮A",
            speed_threshold=1.0,
            slow_down_threshold=5.0,
            normal_speed=12.0,
            check_interval=60,    # 1分钟检查一次
            alert_cooldown=600    # 10分钟冷却
        ),
        # 客轮 - 频繁监控
        VesselConfig(
            mmsi="987654321",
            name="客轮B",
            speed_threshold=0.5,
            slow_down_threshold=3.0,
            normal_speed=15.0,
            check_interval=30,    # 30秒检查一次
            alert_cooldown=300    # 5分钟冷却
        ),
        # 渔船 - 宽松监控
        VesselConfig(
            mmsi="555666777",
            name="渔船C",
            speed_threshold=0.1,
            slow_down_threshold=2.0,
            normal_speed=8.0,
            check_interval=300,   # 5分钟检查一次
            alert_cooldown=1800   # 30分钟冷却
        )
    ]
    
    for config in configurations:
        monitor.add_vessel(config)
        print(f"已添加 {config.name}: 检查间隔{config.check_interval}秒, 冷却时间{config.alert_cooldown}秒")


if __name__ == "__main__":
    print("智能航运监控系统 - 使用示例")
    print("=" * 50)
    
    # 运行各种示例
    example_basic_usage()
    example_config_file_usage()
    example_monitoring_summary()
    example_custom_configuration()
    
    print("\n=== 开始监控示例 ===")
    print("注意: 这只是示例，实际监控需要有效的API token")
    print("要开始实际监控，请运行: python vessel_warn.py")
