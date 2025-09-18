#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统 - 主运行入口
简化版本，快速启动和演示

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import sys
import os

def print_banner():
    """打印系统横幅"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                    船舶油耗预测系统                          ║
║              Ship Fuel Consumption Prediction System         ║
║                                                              ║
║    基于航运行业CP条款和专业知识的智能化油耗预测系统          ║
║                                                              ║
║    版本: v1.0.1 (稳定版)                                     ║
║    日期: 2025-09-18                                          ║
╚══════════════════════════════════════════════════════════════╝
    """)

def show_menu():
    """显示功能菜单"""
    print("🚀 请选择要运行的功能:")
    print("   1. 简单演示 (推荐)")
    print("   2. API功能测试")
    print("   3. 数据分析演示")
    print("   4. CP条款分析演示")
    print("   5. 查看预测结果文件")
    print("   6. 系统状态检查")
    print("   0. 退出")
    print("-" * 50)

def run_simple_demo():
    """运行简单演示"""
    print("🚢 运行简单演示...")
    try:
        os.system("python simple_demo.py")
        return True
    except Exception as e:
        print(f"❌ 简单演示失败: {e}")
        return False

def run_api_test():
    """运行API测试"""
    print("🔧 运行API功能测试...")
    try:
        os.system("python prediction_api.py")
        return True
    except Exception as e:
        print(f"❌ API测试失败: {e}")
        return False

def run_data_analysis():
    """运行数据分析演示"""
    print("📊 运行数据分析演示...")
    try:
        from src.data_analyzer import ShipFuelDataAnalyzer
        
        analyzer = ShipFuelDataAnalyzer('data/油耗数据ALL（0804）.csv')
        stats = analyzer.get_basic_statistics()
        
        print(f"✅ 数据分析完成:")
        print(f"   数据总量: {stats['数据总量']:,} 条")
        print(f"   船舶数量: {stats['船舶数量']} 艘")
        print(f"   主要船型:")
        for ship_type, count in list(stats['船型分布'].items())[:5]:
            print(f"     {ship_type}: {count:,} 条")
        
        return True
    except Exception as e:
        print(f"❌ 数据分析失败: {e}")
        return False

def run_cp_analysis():
    """运行CP条款分析演示"""
    print("⚖️ 运行CP条款分析演示...")
    try:
        from src.cp_clause_definitions import CPClauseCalculator, ShipType, LoadCondition
        
        calculator = CPClauseCalculator()
        
        # 示例计算
        warranted_speed = calculator.calculate_warranted_speed(
            ShipType.BULK_CARRIER, LoadCondition.LADEN, 75000
        )
        warranted_consumption = calculator.calculate_warranted_consumption(
            ShipType.BULK_CARRIER, LoadCondition.LADEN, 75000, 12.5
        )
        
        print(f"✅ CP条款分析完成:")
        print(f"   船型: 散货船 (75,000 DWT)")
        print(f"   载重状态: 满载")
        print(f"   保证航速: {warranted_speed} kts")
        print(f"   保证日油耗: {warranted_consumption['total']:.1f} mt/day")
        
        # 性能偏差分析
        deviation = calculator.calculate_performance_deviation(
            12.5, 25.0, warranted_speed, warranted_consumption['total']
        )
        print(f"   性能指数: {deviation['performance_index']:.1f}")
        
        return True
    except Exception as e:
        print(f"❌ CP条款分析失败: {e}")
        return False

def show_prediction_results():
    """显示预测结果文件"""
    print("📄 查看预测结果文件...")
    
    result_files = [
        ('outputs/model_predictions.csv', '预测结果表格'),
        ('outputs/model_predictions.json', '详细预测结果'),
        ('outputs/test_report.json', '测试报告'),
        ('reports/analysis_report.md', '数据分析报告'),
        ('reports/model_report.md', '模型性能报告')
    ]
    
    print("📋 可用的结果文件:")
    for file_path, description in result_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > 1024:
                size_str = f"{size/1024:.1f} KB"
            else:
                size_str = f"{size} B"
            print(f"   ✅ {file_path} - {description} ({size_str})")
        else:
            print(f"   ❌ {file_path} - {description} (不存在)")
    
    # 显示CSV文件内容预览
    csv_path = 'outputs/model_predictions.csv'
    if os.path.exists(csv_path):
        print(f"\n📊 预测结果预览 (前5行):")
        os.system(f"head -6 {csv_path}")

def run_system_check():
    """运行系统检查"""
    print("🔍 运行系统状态检查...")
    try:
        # 使用archive中的system_check.py
        if os.path.exists('archive/system_check.py'):
            os.system("cd archive && python system_check.py")
        else:
            print("❌ 系统检查文件不存在")
        return True
    except Exception as e:
        print(f"❌ 系统检查失败: {e}")
        return False

def main():
    """主函数"""
    print_banner()
    
    while True:
        show_menu()
        
        try:
            choice = input("请输入选择 (0-6): ").strip()
            
            if choice == '0':
                print("👋 感谢使用船舶油耗预测系统！")
                break
            elif choice == '1':
                run_simple_demo()
            elif choice == '2':
                run_api_test()
            elif choice == '3':
                run_data_analysis()
            elif choice == '4':
                run_cp_analysis()
            elif choice == '5':
                show_prediction_results()
            elif choice == '6':
                run_system_check()
            else:
                print("❌ 无效选择，请输入0-6之间的数字")
            
            print("\n" + "="*50)
            input("按回车键继续...")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 程序已退出")
            break
        except Exception as e:
            print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    main()
