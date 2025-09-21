#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速开始示例
Quick Start Example for Ship Fuel Consumption Prediction

演示如何使用船舶油耗预测系统的基本功能

作者: 船舶油耗预测系统
日期: 2025-09-21
"""

import sys
import os

# 添加核心模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from optimized_fuel_api import OptimizedFuelAPI

def main():
    """快速开始示例"""
    print("🚀 船舶油耗预测系统 - 快速开始")
    print("=" * 50)
    
    # 1. 初始化API
    print("\n1. 初始化API...")
    api = OptimizedFuelAPI()
    
    # 检查状态
    status = api.get_api_status()
    print(f"   系统状态: {'✅ 就绪' if status['model_loaded'] else '⚠️ 备用模式'}")
    
    # 2. 基本预测
    print("\n2. 基本预测示例:")
    
    # 散货船预测
    result = api.predict_single(
        ship_type='Bulk Carrier',
        speed=12.0,
        dwt=75000,
        load_condition='Laden'
    )
    
    if 'predicted_consumption' in result:
        print(f"   7.5万吨散货船@12节: {result['predicted_consumption']}mt/日")
        print(f"   预测置信度: {result['confidence']}")
        print(f"   预测范围: {result['prediction_range'][0]}-{result['prediction_range'][1]}mt")
    
    # 集装箱船预测
    result = api.predict_single(
        ship_type='Container Ship',
        speed=18.0,
        dwt=120000
    )
    
    if 'predicted_consumption' in result:
        print(f"   12万吨集装箱船@18节: {result['predicted_consumption']}mt/日")
    
    # 3. 速度优化建议
    print("\n3. 速度优化建议:")
    
    recommendation = api.get_ship_recommendations(
        ship_type='Bulk Carrier',
        target_consumption=25.0
    )
    
    if 'best_speed' in recommendation:
        print(f"   目标油耗25mt的最佳航速: {recommendation['best_speed']:.1f}节")
        print(f"   预测精度: {recommendation['accuracy']}")
    
    # 4. 船型对比
    print("\n4. 船型效率对比 (15节):")
    
    comparison = api.get_comparative_analysis(
        ship_types=['Bulk Carrier', 'Container Ship', 'Crude Oil Tanker'],
        speed=15.0
    )
    
    if comparison['comparison_results']:
        for result in comparison['comparison_results']:
            print(f"   {result['ship_type']}: {result['predicted_consumption']:.2f}mt "
                  f"(效率排名: {result['efficiency_rank']})")
    
    # 5. 统计信息
    print("\n5. 系统统计信息:")
    
    stats = api.get_summary_statistics()
    if 'total_combinations' in stats:
        print(f"   支持的船型-速度组合: {stats['total_combinations']}")
        print(f"   速度范围: {stats['speed_range']['min']:.1f}-{stats['speed_range']['max']:.1f}节")
        print(f"   油耗范围: {stats['fuel_consumption']['min']:.1f}-{stats['fuel_consumption']['max']:.1f}mt")
    
    print("\n✅ 快速开始示例完成!")
    print("\n💡 提示:")
    print("   • 更多功能请参考 comprehensive_demo.py")
    print("   • API文档请查看 README.md")
    print("   • 如需批量预测，请使用 predict_batch() 方法")

if __name__ == "__main__":
    main()
