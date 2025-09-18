#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统 - 基础使用示例
Basic Usage Examples

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prediction_api import FuelPredictionAPI

def example_single_prediction():
    """单次预测示例"""
    print("🚢 单次预测示例")
    print("-" * 30)
    
    # 创建预测API
    api = FuelPredictionAPI('models/fuel_prediction_models.pkl')
    
    # 示例船舶数据
    ship_data = {
        '船舶类型': 'BULK CARRIER',
        '平均速度(kts)': 12.5,
        '船舶载重(t)': 75000,
        '船舶吃水(m)': 14.2,
        '船舶总长度(m)': 225,
        '载重状态': 'Laden',
        '航行距离(nm)': 240,
        '航行时间(hrs)': 20,
        '重油IFO(mt)': 20.5,
        '轻油MDO/MGO(mt)': 1.5,
        '重油cp': 24.0,
        '轻油cp': 0.0,
        '航速cp': 12.0,
        '船龄': 15
    }
    
    # 执行预测
    result = api.predict_single_voyage(ship_data)
    
    print(f"预测结果:")
    print(f"  小时油耗: {result['predicted_fuel_consumption']:.2f} mt/h")
    print(f"  日油耗: {result['predicted_fuel_consumption'] * 24:.1f} mt/day")
    print(f"  置信度: {result['confidence']}")
    
    return result

def example_batch_prediction():
    """批量预测示例"""
    print("\n📊 批量预测示例")
    print("-" * 30)
    
    api = FuelPredictionAPI('models/fuel_prediction_models.pkl')
    
    # 批量船舶数据
    ships_data = [
        {
            '船舶类型': 'BULK CARRIER',
            '平均速度(kts)': 11.0,
            '船舶载重(t)': 70000,
            '载重状态': 'Laden',
            '航行距离(nm)': 200,
            '航行时间(hrs)': 18
        },
        {
            '船舶类型': 'OPEN HATCH CARGO SHIP', 
            '平均速度(kts)': 13.0,
            '船舶载重(t)': 60000,
            '载重状态': 'Laden',
            '航行距离(nm)': 260,
            '航行时间(hrs)': 20
        },
        {
            '船舶类型': 'CHEMICAL/PRODUCTS TANKER',
            '平均速度(kts)': 12.0,
            '船舶载重(t)': 45000,
            '载重状态': 'Ballast',
            '航行距离(nm)': 180,
            '航行时间(hrs)': 15
        }
    ]
    
    # 批量预测
    results = api.batch_predict(ships_data)
    
    print("批量预测结果:")
    for i, result in enumerate(results, 1):
        ship_type = ships_data[i-1]['船舶类型']
        consumption = result.get('predicted_fuel_consumption', 0)
        print(f"  {i}. {ship_type}: {consumption:.2f} mt/h")
    
    return results

def example_speed_optimization():
    """速度优化示例"""
    print("\n⚡ 速度优化示例")
    print("-" * 30)
    
    api = FuelPredictionAPI('models/fuel_prediction_models.pkl')
    
    # 基础航行数据
    voyage_data = {
        '船舶类型': 'BULK CARRIER',
        '船舶载重(t)': 75000,
        '载重状态': 'Laden',
        '航行距离(nm)': 1000,
        '航行时间(hrs)': 80
    }
    
    # 速度优化
    optimization = api.optimize_speed(voyage_data, speed_range=(10, 16), step=2.0)
    
    if 'optimal_speed' in optimization:
        print(f"优化结果:")
        print(f"  最优速度: {optimization['optimal_speed']} kts")
        print(f"  节省潜力: {optimization['savings_potential']}")
        
        # 显示优化曲线
        print(f"  速度-油耗关系:")
        for point in optimization['optimization_curve']:
            print(f"    {point['speed']} kts -> {point['total_fuel']:.0f} mt")
    
    return optimization

def main():
    """主函数"""
    print("🚢 船舶油耗预测系统 - 基础使用示例")
    print("=" * 50)
    
    try:
        # 1. 单次预测示例
        example_single_prediction()
        
        # 2. 批量预测示例
        example_batch_prediction()
        
        # 3. 速度优化示例
        example_speed_optimization()
        
        print(f"\n✅ 所有示例运行完成!")
        
    except Exception as e:
        print(f"❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
