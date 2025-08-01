#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试坏天气性能计算功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tasks.navgreen.subtasks.calc_vessel_performance_details_from_wmy import (
    CalcVesselPerformanceDetailsFromWmy,
    classify_weather_conditions
)

def test_weather_classification():
    """测试天气分类功能"""
    print("=== 测试天气分类功能 ===")
    
    test_cases = [
        (3, 1.0, "正常天气"),
        (5, 1.2, "中等坏天气"),
        (6, 1.8, "恶劣天气"),
        (8, 3.0, "恶劣天气"),
        (4, 2.0, "中等坏天气"),
        (7, 1.0, "恶劣天气"),
    ]
    
    for wind_level, wave_height, expected in test_cases:
        result = classify_weather_conditions(wind_level, wave_height)
        print(f"风力{wind_level}级, 浪高{wave_height}米 -> {result['weather_type']} ({result['description']})")
        print(f"  安全等级: {result['safety_level']}")
        print(f"  速度降低因子: {result['speed_reduction_factor']}")
        print(f"  建议: {result['recommendations']}")
        print()

def test_bad_weather_performance():
    """测试坏天气性能计算"""
    print("=== 测试坏天气性能计算 ===")
    
    # 模拟轨迹数据
    mock_trace_data = [
        {
            "wind_level": 6,
            "wave_height": 2.5,
            "hdg": 90.0,
            "sog": 12.0,
            "draught": 8.0,
            "current_u": 0.5,
            "current_v": 0.3
        },
        {
            "wind_level": 7,
            "wave_height": 3.0,
            "hdg": 95.0,
            "sog": 10.5,
            "draught": 8.2,
            "current_u": 0.6,
            "current_v": 0.4
        },
        {
            "wind_level": 5,
            "wave_height": 1.8,
            "hdg": 88.0,
            "sog": 13.2,
            "draught": 7.8,
            "current_u": 0.4,
            "current_v": 0.2
        },
        {
            "wind_level": 8,
            "wave_height": 4.5,
            "hdg": 92.0,
            "sog": 8.5,
            "draught": 8.5,
            "current_u": 0.7,
            "current_v": 0.5
        }
    ]
    
    # 模拟好天气数据
    mock_good_weather_data = [
        {
            "wind_level": 3,
            "wave_height": 1.0,
            "hdg": 90.0,
            "sog": 15.5,
            "draught": 8.0,
            "current_u": 0.5,
            "current_v": 0.3
        },
        {
            "wind_level": 2,
            "wave_height": 0.8,
            "hdg": 95.0,
            "sog": 16.2,
            "draught": 8.2,
            "current_u": 0.6,
            "current_v": 0.4
        }
    ]
    
    calc_vessel = CalcVesselPerformanceDetailsFromWmy()
    
    # 测试坏天气性能计算
    draught = 10.0  # 设计吃水
    design_speed = 16.0  # 设计速度
    
    bad_weather_perf = calc_vessel.deal_bad_perf_list(mock_trace_data, draught, design_speed)
    print("坏天气性能数据:")
    for key, value in bad_weather_perf.items():
        print(f"  {key}: {value}")
    print()
    
    # 测试好天气性能计算
    good_weather_perf = calc_vessel.deal_good_perf_list(mock_good_weather_data, draught, design_speed)
    print("好天气性能数据:")
    for key, value in good_weather_perf.items():
        print(f"  {key}: {value}")
    print()
    
    # 测试性能对比分析
    analysis = calc_vessel.analyze_performance_comparison(
        good_weather_perf, bad_weather_perf, design_speed
    )
    print("性能对比分析:")
    print(f"  性能对比: {analysis['performance_comparison']}")
    print(f"  速度降低分析: {analysis['speed_reduction_analysis']}")
    print(f"  安全建议: {analysis['safety_recommendations']}")
    print(f"  操作洞察: {analysis['operational_insights']}")

def main():
    """主测试函数"""
    print("开始测试坏天气性能计算功能...\n")
    
    try:
        test_weather_classification()
        test_bad_weather_performance()
        print("所有测试完成！")
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 