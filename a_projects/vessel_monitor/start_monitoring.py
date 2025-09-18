#!/usr/bin/env python3
"""
船舶监控系统启动脚本
提供交互式界面来配置和启动监控
"""

import json
import sys
from vessel_warn import VesselMonitor, VesselConfig


def load_config_from_file():
    """从配置文件加载船舶配置"""
    try:
        with open('vessel_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('vessels', [])
    except FileNotFoundError:
        print("❌ 配置文件 vessel_config.json 不存在")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件格式错误: {e}")
        return []


def create_interactive_config():
    """交互式创建船舶配置"""
    print("\n=== 交互式配置船舶 ===")
    vessels = []
    
    while True:
        print(f"\n当前已配置 {len(vessels)} 艘船舶")
        
        mmsi = input("请输入MMSI号 (留空结束): ").strip()
        if not mmsi:
            break
            
        name = input("请输入船舶名称 (可选): ").strip()
        
        try:
            speed_threshold = float(input("请输入停航阈值(节) [默认1.0]: ") or "1.0")
            slow_down_threshold = float(input("请输入降速阈值(节) [默认5.0]: ") or "5.0")
            normal_speed = float(input("请输入正常航速(节) [默认10.0]: ") or "10.0")
            check_interval = int(input("请输入检查间隔(秒) [默认30]: ") or "30")
            alert_cooldown = int(input("请输入预警冷却时间(秒) [默认300]: ") or "300")
        except ValueError:
            print("❌ 输入格式错误，使用默认值")
            speed_threshold = 1.0
            slow_down_threshold = 5.0
            normal_speed = 10.0
            check_interval = 30
            alert_cooldown = 300
        
        vessel = VesselConfig(
            mmsi=mmsi,
            name=name,
            speed_threshold=speed_threshold,
            slow_down_threshold=slow_down_threshold,
            normal_speed=normal_speed,
            check_interval=check_interval,
            alert_cooldown=alert_cooldown
        )
        
        vessels.append(vessel)
        print(f"✅ 已添加船舶: {name or mmsi}")
    
    return vessels


def display_menu():
    """显示主菜单"""
    print("\n" + "="*50)
    print("🚢 智能航运监控系统")
    print("="*50)
    print("1. 从配置文件加载船舶")
    print("2. 交互式配置船舶")
    print("3. 使用默认配置")
    print("4. 查看当前配置")
    print("5. 测试API连接")
    print("6. 开始监控")
    print("0. 退出")
    print("="*50)


def test_api_connection(monitor):
    """测试API连接"""
    print("\n=== 测试API连接 ===")
    
    test_mmsi = input("请输入测试MMSI号 [默认367560102]: ").strip() or "367560102"
    
    print(f"正在测试船舶 {test_mmsi} 的API连接...")
    status = monitor.get_vessel_data(test_mmsi)
    
    if status:
        print("✅ API连接成功!")
        print(f"   航速: {status.speed} 节")
        print(f"   状态: {status.status}")
        print(f"   时间: {status.timestamp}")
    else:
        print("❌ API连接失败，请检查网络和token")


def display_current_config(monitor):
    """显示当前配置"""
    print("\n=== 当前配置 ===")
    
    if not monitor.vessels:
        print("❌ 没有配置任何船舶")
        return
    
    print(f"总共配置了 {len(monitor.vessels)} 艘船舶:")
    print("-" * 60)
    
    for mmsi, config in monitor.vessels.items():
        print(f"船舶名称: {config.name or '未命名'}")
        print(f"MMSI: {config.mmsi}")
        print(f"停航阈值: {config.speed_threshold} 节")
        print(f"降速阈值: {config.slow_down_threshold} 节")
        print(f"正常航速: {config.normal_speed} 节")
        print(f"检查间隔: {config.check_interval} 秒")
        print(f"预警冷却: {config.alert_cooldown} 秒")
        print("-" * 60)


def main():
    """主函数"""
    monitor = VesselMonitor()
    
    while True:
        display_menu()
        choice = input("请选择操作 [0-6]: ").strip()
        
        if choice == '0':
            print("👋 再见!")
            break
            
        elif choice == '1':
            vessels_data = load_config_from_file()
            if vessels_data:
                for vessel_data in vessels_data:
                    vessel = VesselConfig(**vessel_data)
                    monitor.add_vessel(vessel)
                print(f"✅ 已从配置文件加载 {len(vessels_data)} 艘船舶")
            else:
                print("❌ 无法加载配置文件")
                
        elif choice == '2':
            vessels = create_interactive_config()
            for vessel in vessels:
                monitor.add_vessel(vessel)
            print(f"✅ 已交互式配置 {len(vessels)} 艘船舶")
            
        elif choice == '3':
            # 默认配置
            default_vessels = [
                VesselConfig(mmsi="367560102", name="货轮001"),
                VesselConfig(mmsi="414281000", name="货轮002")
            ]
            for vessel in default_vessels:
                monitor.add_vessel(vessel)
            print("✅ 已加载默认配置")
            
        elif choice == '4':
            display_current_config(monitor)
            
        elif choice == '5':
            test_api_connection(monitor)
            
        elif choice == '6':
            if not monitor.vessels:
                print("❌ 请先配置船舶")
                continue
                
            print("\n🚀 开始监控...")
            print("按 Ctrl+C 停止监控")
            try:
                monitor.monitor_vessels()
            except KeyboardInterrupt:
                print("\n⏹️ 监控已停止")
                # 显示监控摘要
                summary = monitor.get_monitoring_summary()
                print(f"\n📊 监控摘要: 共监控 {summary['total_vessels']} 艘船舶")
            except Exception as e:
                print(f"❌ 监控过程中发生错误: {e}")
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序发生错误: {e}")
        sys.exit(1)
