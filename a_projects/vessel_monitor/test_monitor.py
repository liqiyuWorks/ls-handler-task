#!/usr/bin/env python3
"""
船舶监控系统测试脚本
用于验证监控功能是否正常工作
"""

import time
from vessel_warn import VesselMonitor, VesselConfig, AlertType


def test_vessel_data_retrieval():
    """测试船舶数据获取功能"""
    print("=== 测试船舶数据获取 ===")
    
    monitor = VesselMonitor()
    
    # 测试MMSI
    test_mmsi = "367560102"
    print(f"正在获取船舶 {test_mmsi} 的数据...")
    
    status = monitor.get_vessel_data(test_mmsi)
    if status:
        print(f"✅ 成功获取数据:")
        print(f"   MMSI: {status.mmsi}")
        print(f"   航速: {status.speed} 节")
        print(f"   时间: {status.timestamp}")
        print(f"   位置: {status.position}")
        print(f"   航向: {status.heading}")
        print(f"   状态: {status.status}")
    else:
        print("❌ 获取数据失败")


def test_speed_analysis():
    """测试航速分析功能"""
    print("\n=== 测试航速分析 ===")
    
    monitor = VesselMonitor()
    
    # 添加测试船舶
    config = VesselConfig(
        mmsi="367560102",
        name="测试船舶",
        speed_threshold=1.0,
        slow_down_threshold=5.0,
        normal_speed=10.0
    )
    monitor.add_vessel(config)
    
    # 模拟不同的航速情况
    test_cases = [
        (0.5, "停航状态"),
        (3.0, "降速状态"),
        (12.0, "正常航速"),
        (8.0, "恢复状态")
    ]
    
    for speed, description in test_cases:
        from vessel_warn import VesselStatus
        from datetime import datetime
        
        status = VesselStatus(
            mmsi="367560102",
            speed=speed,
            timestamp=datetime.now()
        )
        
        alert_type = monitor.analyze_speed_change("367560102", status)
        
        print(f"航速 {speed} 节 ({description}): ", end="")
        if alert_type:
            print(f"⚠️ 触发预警: {alert_type.value}")
        else:
            print("✅ 正常")
        
        # 更新状态用于下次比较
        monitor.vessel_status["367560102"] = status


def test_alert_system():
    """测试预警系统"""
    print("\n=== 测试预警系统 ===")
    
    monitor = VesselMonitor()
    
    config = VesselConfig(
        mmsi="367560102",
        name="测试船舶",
        speed_threshold=1.0,
        slow_down_threshold=5.0,
        normal_speed=10.0
    )
    monitor.add_vessel(config)
    
    # 模拟停航预警
    from vessel_warn import VesselStatus
    from datetime import datetime
    
    status = VesselStatus(
        mmsi="367560102",
        speed=0.5,
        timestamp=datetime.now()
    )
    
    print("模拟停航预警...")
    monitor.send_alert("367560102", AlertType.STOPPED, status)


def test_monitoring_summary():
    """测试监控摘要功能"""
    print("\n=== 测试监控摘要 ===")
    
    monitor = VesselMonitor()
    
    # 添加多个测试船舶
    vessels = [
        VesselConfig(mmsi="367560102", name="货轮001"),
        VesselConfig(mmsi="414281000", name="货轮002"),
    ]
    
    for vessel in vessels:
        monitor.add_vessel(vessel)
    
    # 获取摘要
    summary = monitor.get_monitoring_summary()
    print("监控摘要:")
    print(f"  总船舶数: {summary['total_vessels']}")
    print(f"  生成时间: {summary['timestamp']}")
    print("  船舶列表:")
    for vessel in summary['monitored_vessels']:
        print(f"    - {vessel['name']} (MMSI: {vessel['mmsi']})")


def run_quick_monitoring_test():
    """运行快速监控测试"""
    print("\n=== 快速监控测试 ===")
    print("注意: 这将进行实际的API调用")
    
    monitor = VesselMonitor()
    
    # 添加测试船舶
    config = VesselConfig(
        mmsi="367560102",
        name="测试船舶",
        speed_threshold=1.0,
        slow_down_threshold=5.0,
        normal_speed=10.0,
        check_interval=10,  # 10秒检查一次
        alert_cooldown=30   # 30秒冷却
    )
    monitor.add_vessel(config)
    
    print("开始监控测试 (30秒)...")
    print("按 Ctrl+C 提前停止")
    
    try:
        start_time = time.time()
        while time.time() - start_time < 30:  # 运行30秒
            for mmsi, vessel_config in monitor.vessels.items():
                status = monitor.get_vessel_data(mmsi)
                if status:
                    alert_type = monitor.analyze_speed_change(mmsi, status)
                    if alert_type:
                        monitor.send_alert(mmsi, alert_type, status)
                    monitor.vessel_status[mmsi] = status
                    print(f"船舶 {mmsi}: 航速 {status.speed} 节")
                
                time.sleep(vessel_config.check_interval)
                
    except KeyboardInterrupt:
        print("\n测试已停止")
    
    print("监控测试完成")


if __name__ == "__main__":
    print("船舶监控系统测试")
    print("=" * 50)
    
    # 运行各项测试
    test_vessel_data_retrieval()
    test_speed_analysis()
    test_alert_system()
    test_monitoring_summary()
    
    # 询问是否运行快速监控测试
    response = input("\n是否运行快速监控测试? (y/n): ")
    if response.lower() == 'y':
        run_quick_monitoring_test()
    
    print("\n测试完成!")
