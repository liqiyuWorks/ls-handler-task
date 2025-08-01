#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试坏天气性能计算核心功能
"""

import math
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class SpeedStats:
    """速度统计累加器"""
    total: float = 0.0
    count: int = 0

    def add(self, speed: float):
        """添加速度值"""
        self.total += speed
        self.count += 1

    def average(self) -> float:
        """计算平均速度"""
        return round(self.total / self.count, 2) if self.count > 0 else 0.0


def classify_weather_conditions(wind_level: int, wave_height: float) -> Dict[str, Any]:
    """
    分类天气条件，提供详细的天气判断标准
    
    参考标准：
    - IMO航行安全指南
    - 中国海事局船舶航行安全规定
    - 航运业实践经验
    - 国际气象组织(WMO)标准
    
    :param wind_level: 风力等级 (0-12)
    :param wave_height: 浪高 (米)
    :return: 天气分类结果
    """
    result = {
        'weather_type': 'normal',  # normal, moderate_bad, severe_bad
        'description': '',
        'safety_level': 'safe',   # safe, caution, dangerous
        'speed_reduction_factor': 1.0,  # 速度降低因子
        'recommendations': []
    }
    
    # 风力等级判断
    if wind_level >= 8:
        result.update({
            'weather_type': 'severe_bad',
            'description': '大风天气',
            'safety_level': 'dangerous',
            'speed_reduction_factor': 0.6,
            'recommendations': ['建议减速航行', '注意船舶稳定性', '考虑避风锚地']
        })
    elif wind_level >= 6:
        result.update({
            'weather_type': 'severe_bad',
            'description': '强风天气',
            'safety_level': 'caution',
            'speed_reduction_factor': 0.7,
            'recommendations': ['建议适当减速', '注意风压影响']
        })
    elif wind_level >= 5:
        result.update({
            'weather_type': 'moderate_bad',
            'description': '清风天气',
            'safety_level': 'caution',
            'speed_reduction_factor': 0.85,
            'recommendations': ['注意风向变化']
        })
    
    # 浪高判断
    if wave_height >= 4.0:
        result.update({
            'weather_type': 'severe_bad',
            'description': '大浪天气',
            'safety_level': 'dangerous',
            'speed_reduction_factor': min(result['speed_reduction_factor'], 0.5),
            'recommendations': ['建议减速航行', '注意船舶稳定性', '考虑避风锚地']
        })
    elif wave_height >= 2.5:
        result.update({
            'weather_type': 'severe_bad',
            'description': '中浪天气',
            'safety_level': 'caution',
            'speed_reduction_factor': min(result['speed_reduction_factor'], 0.7),
            'recommendations': ['建议适当减速', '注意浪涌影响']
        })
    elif wave_height >= 1.5:
        result.update({
            'weather_type': 'moderate_bad',
            'description': '小浪天气',
            'safety_level': 'caution',
            'speed_reduction_factor': min(result['speed_reduction_factor'], 0.9),
            'recommendations': ['注意浪涌']
        })
    
    # 组合条件判断
    if wind_level >= 5 and wave_height >= 1.5:
        result.update({
            'weather_type': 'moderate_bad',
            'description': '风浪组合天气',
            'safety_level': 'caution',
            'speed_reduction_factor': min(result['speed_reduction_factor'], 0.8),
            'recommendations': ['注意风浪组合影响', '适当调整航速']
        })
    
    return result


def deal_bad_perf_list(data: List[Dict[str, Any]], DESIGN_DRAFT: float, DESIGN_SPEED: float) -> Dict[str, float]:
    """
    处理船舶数据列表，计算坏天气条件下的平均船速
    """
    # 设计吃水深度阈值
    EMPTY_LOAD = DESIGN_DRAFT * 0.7  # 70%
    FULL_LOAD = DESIGN_DRAFT * 0.8   # 80%

    # 初始化累加器
    stats = {
        'bad_weather': SpeedStats(),           # 坏天气总体统计
        'empty': SpeedStats(),                  # 空载统计
        'full': SpeedStats(),                   # 满载统计
        'severe_weather': SpeedStats(),        # 恶劣天气统计
        'moderate_bad_weather': SpeedStats(),  # 中等坏天气统计
    }

    # 数据预处理和验证
    valid_data = []
    for item in data:
        try:
            # 基础数据验证
            wind_level = int(item.get("wind_level", 5))
            wave_height = float(item.get("wave_height", 1.26))
            sog = float(item.get("sog", 0.0))
            draught = float(item.get("draught"))
            hdg = float(item.get("hdg"))

            # 使用天气分类函数判断坏天气条件
            weather_info = classify_weather_conditions(wind_level, wave_height)
            is_bad_weather = weather_info['weather_type'] in ['moderate_bad', 'severe_bad']
            weather_severity = weather_info['weather_type']

            # 确保船舶在航行状态
            if is_bad_weather and sog >= DESIGN_SPEED * 0.3:
                valid_data.append({
                    'draught': draught,
                    'sog': sog,
                    'hdg': hdg,
                    'weather_severity': weather_severity
                })
        except (ValueError, TypeError):
            continue

    # 处理有效数据
    for item in valid_data:
        draught = item['draught']
        sog = item['sog']
        weather_severity = item['weather_severity']

        # 判断载重状态
        is_empty = draught < EMPTY_LOAD
        is_full = draught > FULL_LOAD

        # 更新总体坏天气统计
        stats['bad_weather'].add(sog)
        
        # 更新天气严重程度统计
        if weather_severity == "severe_bad":
            stats['severe_weather'].add(sog)
        elif weather_severity == "moderate_bad":
            stats['moderate_bad_weather'].add(sog)

        # 更新载重相关统计
        if is_empty:
            stats['empty'].add(sog)
        elif is_full:
            stats['full'].add(sog)

    # 构建结果
    performance = {
        "avg_bad_weather_speed": stats['bad_weather'].average(),
        "avg_severe_weather_speed": stats['severe_weather'].average(),
        "avg_moderate_bad_weather_speed": stats['moderate_bad_weather'].average(),
    }

    # 添加载重相关统计
    if stats['empty'].count > 0:
        performance.update({
            "avg_ballast_bad_weather_speed": stats['empty'].average(),
        })

    if stats['full'].count > 0:
        performance.update({
            "avg_laden_bad_weather_speed": stats['full'].average(),
        })

    # 打印统计信息
    print(f"坏天气数据统计: 总体={stats['bad_weather'].count}, "
          f"空载={stats['empty'].count}, 满载={stats['full'].count}, "
          f"恶劣天气={stats['severe_weather'].count}, 中等坏天气={stats['moderate_bad_weather'].count}")

    return performance


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
        },
        {
            "wind_level": 7,
            "wave_height": 3.0,
            "hdg": 95.0,
            "sog": 10.5,
            "draught": 8.2,
        },
        {
            "wind_level": 5,
            "wave_height": 1.8,
            "hdg": 88.0,
            "sog": 13.2,
            "draught": 7.8,
        },
        {
            "wind_level": 8,
            "wave_height": 4.5,
            "hdg": 92.0,
            "sog": 8.5,
            "draught": 8.5,
        }
    ]
    
    # 测试坏天气性能计算
    draught = 10.0  # 设计吃水
    design_speed = 16.0  # 设计速度
    
    bad_weather_perf = deal_bad_perf_list(mock_trace_data, draught, design_speed)
    print("坏天气性能数据:")
    for key, value in bad_weather_perf.items():
        print(f"  {key}: {value}")
    print()


def main():
    """主测试函数"""
    print("开始测试坏天气性能计算核心功能...\n")
    
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