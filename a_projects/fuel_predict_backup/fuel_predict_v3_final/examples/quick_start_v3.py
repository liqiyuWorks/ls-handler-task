#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统 V3.0 - 快速开始示例
Quick Start Example for Ship Fuel Prediction System V3.0

展示如何使用V3.0增强版本的多维度预测功能

作者: 船舶油耗预测系统
日期: 2025-09-21
版本: 3.0
"""

import sys
import os

# 添加核心模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'core'))

from enhanced_fuel_api_v3 import EnhancedFuelAPIV3

def main():
    """V3.0快速开始示例"""
    print("🚀 船舶油耗预测系统 V3.0 - 快速开始")
    print("=" * 60)
    
    # 1. 初始化V3.0 API
    print("\n1. 初始化V3.0 API...")
    api = EnhancedFuelAPIV3()
    
    # 检查状态
    status = api.get_api_status_v3()
    print(f"   系统状态: {'✅ 就绪' if status['model_loaded'] else '⚠️ 增强规则模式'}")
    print(f"   支持特征: {len(status['enhanced_features']['optional'])}个可选特征")
    
    # 2. 基础预测 (仅必需参数)
    print("\n2. 基础预测示例:")
    
    basic_result = api.predict_enhanced(
        ship_type='Bulk Carrier',
        speed=12.0
    )
    
    if 'predicted_consumption' in basic_result:
        print(f"   散货船@12节 (基础预测): {basic_result['predicted_consumption']}mt/日")
    
    # 3. 增强预测 (包含新特征)
    print("\n3. 增强预测示例 (包含船龄、载重状态等):")
    
    enhanced_result = api.predict_enhanced(
        ship_type='Bulk Carrier',
        speed=12.0,
        dwt=75000,
        ship_age=8,                    # 新增: 船龄
        load_condition='Laden',        # 新增: 载重状态
        draft=12.5,                    # 新增: 船舶吃水
        length=225,                    # 新增: 船舶长度
        latitude=35.0,                 # 新增: 纬度
        longitude=139.0,               # 新增: 经度
        heavy_fuel_cp=650              # 新增: 重油CP
    )
    
    if 'predicted_consumption' in enhanced_result:
        print(f"   散货船@12节 (增强预测): {enhanced_result['predicted_consumption']}mt/日")
        print(f"   预测方法: {enhanced_result['method']}")
        print(f"   置信度: {enhanced_result['confidence']}")
    
    # 4. 载重状态对比
    print("\n4. 载重状态影响分析:")
    
    ship_profile = {
        'ship_type': 'Container Ship',
        'speed': 18.0,
        'dwt': 120000,
        'ship_age': 5
    }
    
    load_comparison = api.compare_load_conditions(ship_profile)
    if 'consumption_difference' in load_comparison:
        diff = load_comparison['consumption_difference']
        print(f"   满载 vs 压载差异: {diff['absolute']}mt ({diff['percentage']}%)")
        print(f"   建议: {load_comparison['recommendation']}")
    
    # 5. 船龄影响分析
    print("\n5. 船龄影响分析:")
    
    age_analysis = api.analyze_ship_age_impact(ship_profile, age_range=(0, 20))
    if 'most_efficient_age' in age_analysis:
        best_age = age_analysis['most_efficient_age']
        print(f"   最经济船龄: {best_age['ship_age']}年")
        print(f"   对应油耗: {best_age['predicted_consumption']}mt")
        print(f"   效率范围: {age_analysis['efficiency_range']}mt")
    
    # 6. 速度优化建议
    print("\n6. 速度优化建议:")
    
    speed_opt = api.optimize_for_target_consumption(
        target_consumption=30.0,
        ship_profile=ship_profile,
        optimize_parameter='speed',
        parameter_range=(10, 22)
    )
    
    if 'best_value' in speed_opt:
        print(f"   目标30mt最佳速度: {speed_opt['best_value']}节")
        print(f"   预测精度: {speed_opt['accuracy']}")
    
    # 7. 特征影响分析
    print("\n7. 特征影响分析:")
    
    base_case = {
        'ship_type': 'Bulk Carrier',
        'speed': 12.0,
        'dwt': 75000,
        'ship_age': 10,
        'load_condition': 'Laden'
    }
    
    variations = {
        'ship_age': [5, 15, 20],
        'load_condition': ['Laden', 'Ballast'],
        'dwt': [50000, 100000, 150000]
    }
    
    impact_analysis = api.analyze_feature_impact(base_case, variations)
    
    if 'feature_impacts' in impact_analysis:
        print(f"   基准预测: {impact_analysis['base_prediction']}mt")
        for feature, impacts in impact_analysis['feature_impacts'].items():
            if impacts:
                max_impact = max(impacts, key=lambda x: abs(x['impact_percentage']))
                print(f"   {feature}最大影响: {max_impact['impact_percentage']}%")
    
    # 8. 系统功能总结
    print(f"\n8. V3.0系统功能总结:")
    print(f"   ✅ 支持12个输入特征 (3个必需 + 9个可选)")
    print(f"   ✅ 基于相关性的科学特征选择")
    print(f"   ✅ 集成学习算法 (RF + XGBoost + LightGBM)")
    print(f"   ✅ 多维度影响分析功能")
    print(f"   ✅ 智能优化建议")
    
    print("\n✅ V3.0快速开始示例完成!")
    print("\n💡 更多功能:")
    print("   • 详细分析请运行 feature_impact_demo.py")
    print("   • 完整文档请查看 docs/模型优化完成报告_V3.md")
    print("   • 训练新模型请运行 enhanced_fuel_predictor_v3.py")

if __name__ == "__main__":
    main()
