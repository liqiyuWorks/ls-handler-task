#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶油耗预测系统 - 简单演示
Simple Demo for Ship Fuel Consumption Prediction

作者: 船舶油耗预测系统
日期: 2025-09-18
"""

from prediction_api import FuelPredictionAPI
import json

def main():
    """简单演示主函数"""
    print("🚢 船舶油耗预测系统 - 简单演示")
    print("=" * 50)
    
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
    
    print("📋 船舶信息:")
    print(f"   船型: {ship_data['船舶类型']}")
    print(f"   载重吨: {ship_data['船舶载重(t)']:,} t")
    print(f"   航行速度: {ship_data['平均速度(kts)']} kts")
    print(f"   载重状态: {ship_data['载重状态']}")
    print(f"   航行距离: {ship_data['航行距离(nm)']} nm")
    
    # 执行预测
    print(f"\n🎯 预测结果:")
    result = api.predict_single_voyage(ship_data)
    
    print(f"   预测小时油耗: {result['predicted_fuel_consumption']:.2f} mt/h")
    print(f"   预测日油耗: {result['predicted_fuel_consumption'] * 24:.1f} mt/day")
    print(f"   预测航行总油耗: {result['predicted_fuel_consumption'] * ship_data['航行时间(hrs)']:.1f} mt")
    print(f"   置信度: {result['confidence']}")
    print(f"   预测方法: {result['method']}")
    
    # 显示建议
    if 'recommendations' in result:
        print(f"\n💡 优化建议:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"   {i}. {rec}")
    
    # CP条款分析
    if 'cp_clause_analysis' in result:
        cp_analysis = result['cp_clause_analysis']
        print(f"\n⚖️ CP条款分析:")
        if 'warranted_speed' in cp_analysis:
            print(f"   保证航速: {cp_analysis['warranted_speed']} kts")
        if 'warranted_daily_consumption' in cp_analysis:
            print(f"   保证日油耗: {cp_analysis['warranted_daily_consumption']} mt/day")
        if 'cp_compliance' in cp_analysis:
            compliance = "✅ 符合" if cp_analysis['cp_compliance'] else "❌ 不符合"
            print(f"   CP条款合规: {compliance}")
    
    # 速度优化
    print(f"\n⚡ 速度优化分析:")
    optimization = api.optimize_speed(ship_data, speed_range=(10, 16), step=2.0)
    
    if 'optimal_speed' in optimization:
        print(f"   最优速度: {optimization['optimal_speed']} kts")
        if 'savings_potential' in optimization:
            print(f"   节省潜力: {optimization['savings_potential']}")
    
    print(f"\n✅ 演示完成!")
    print(f"=" * 50)

if __name__ == "__main__":
    main()
