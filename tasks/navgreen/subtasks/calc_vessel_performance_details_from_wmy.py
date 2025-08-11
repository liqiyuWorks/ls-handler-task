#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymongo
from pkg.public.decorator import decorate
from pkg.public.models import BaseModel
from pkg.public.logger import logger
import requests
from datetime import datetime, timedelta
from datetime import timezone
import math
import traceback
import os
import time
import json
import urllib3
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def is_valid_type(s: Any) -> bool:
    """检查值是否有效"""
    try:
        if s != "" and s is not None:
            return True
    except (ValueError, TypeError):
        return False
    return False


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


def is_valid_current_data(current_u: Any, current_v: Any) -> bool:
    """验证洋流数据的有效性"""
    try:
        if current_u is None or current_v is None:
            return False
        u = float(current_u)
        v = float(current_v)
        # 检查洋流速度是否在合理范围内 (0-5 m/s)
        current_speed = math.sqrt(u*u + v*v)
        return 0 <= current_speed <= 5.0
    except (ValueError, TypeError):
        return False


def deal_good_perf_list(data: List[Dict[str, Any]], DESIGN_DRAFT: float, DESIGN_SPEED: float) -> Dict[str, float]:
    """
    处理船舶数据列表，计算符合条件的平均船速（优化版）
    新增功能：根据吃水(draft)区分空载(<70%)和满载(>80%)船速
    优化点：
    1. 使用累加器模式减少内存使用
    2. 改进数据验证逻辑
    3. 合并重复计算
    4. 提高代码可读性
    """
    # 设计吃水深度阈值
    EMPTY_LOAD = DESIGN_DRAFT * 0.7  # 70%
    FULL_LOAD = DESIGN_DRAFT * 0.8   # 80%

    # 初始化累加器
    stats = {
        'empty': SpeedStats(),           # 空载统计
        'full': SpeedStats(),            # 满载统计
        'empty_downstream': SpeedStats(),  # 空载顺流
        'empty_upstream': SpeedStats(),   # 空载逆流
        'full_downstream': SpeedStats(),  # 满载顺流
        'full_upstream': SpeedStats(),    # 满载逆流
        'downstream': SpeedStats(),       # 总体顺流
        'upstream': SpeedStats(),         # 总体逆流
    }

    # 数据预处理和验证
    valid_data = []
    for item in data:
        try:
            # 基础数据验证
            if not all(is_valid_type(item.get(field)) for field in ["wind_level", "wave_height", "hdg", "sog", "draught"]):
                continue

            # 数值转换和范围验证
            wind_level = int(item.get("wind_level", 5))
            wave_height = float(item.get("wave_height", 1.26))
            sog = float(item.get("sog", 0.0))
            draught = float(item.get("draught"))
            hdg = float(item.get("hdg"))

            # 条件筛选
            if (wind_level <= 4 and
                wave_height <= 1.25 and
                    sog >= DESIGN_SPEED * 0.5):
                valid_data.append({
                    'draught': draught,
                    'sog': sog,
                    'hdg': hdg,
                    'current_u': item.get("current_u"),
                    'current_v': item.get("current_v")
                })
        except (ValueError, TypeError):
            continue

    # 处理有效数据
    for item in valid_data:
        draught = item['draught']
        sog = item['sog']
        hdg = item['hdg']
        current_u = item['current_u']
        current_v = item['current_v']

        # 判断载重状态
        is_empty = draught < EMPTY_LOAD
        is_full = draught > FULL_LOAD

        # 判断流向（如果有洋流数据）
        is_downstream = False
        if is_valid_current_data(current_u, current_v):
            is_downstream = is_sailing_downstream(
                float(current_u), float(current_v), hdg)

        # 更新统计
        if is_empty:
            stats['empty'].add(sog)
            if is_downstream:
                stats['empty_downstream'].add(sog)
                stats['downstream'].add(sog)
            else:
                stats['empty_upstream'].add(sog)
                stats['upstream'].add(sog)
        elif is_full:
            stats['full'].add(sog)
            if is_downstream:
                stats['full_downstream'].add(sog)
                stats['downstream'].add(sog)
            else:
                stats['full_upstream'].add(sog)
                stats['upstream'].add(sog)

    # 构建结果
    performance = {
        "avg_good_weather_speed": round(
            (stats['empty'].total + stats['full'].total) /
            (stats['empty'].count + stats['full'].count), 2
        ) if (stats['empty'].count + stats['full'].count) > 0 else 0.0,
        "avg_downstream_speed": stats['downstream'].average(),
        "avg_non_downstream_speed": stats['upstream'].average(),
    }

    # 添加载重相关统计
    if stats['empty'].count > 0:
        performance.update({
            "avg_ballast_speed": stats['empty'].average(),
            "avg_ballast_downstream_speed": stats['empty_downstream'].average(),
            "avg_ballast_non_downstream_speed": stats['empty_upstream'].average(),
        })

    if stats['full'].count > 0:
        performance.update({
            "avg_laden_speed": stats['full'].average(),
            "avg_laden_downstream_speed": stats['full_downstream'].average(),
            "avg_laden_non_downstream_speed": stats['full_upstream'].average(),
        })

    # 打印统计信息
    # print(f"数据统计: 空载={stats['empty'].count}, 满载={stats['full'].count}, "
    #       f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}")

    return performance


def is_sailing_downstream(u: float, v: float, ship_angle: float) -> bool:
    """
    判断船舶是否顺流航行
    :param u: 洋流U分量
    :param v: 洋流V分量
    :param ship_angle: 船舶航向角度
    :return: 是否顺流
    """
    try:
        # 计算洋流方向
        current_angle = math.atan2(v, u) * 180 / math.pi
        if current_angle < 0:
            current_angle += 360

        # 计算船舶航向与洋流方向的夹角
        angle_diff = abs(current_angle - ship_angle)
        if angle_diff > 180:
            angle_diff = 360 - angle_diff

        # 夹角小于90度认为是顺流
        return angle_diff < 90
    except (ValueError, TypeError, ZeroDivisionError):
        return False


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


def assess_vessel_performance_from_captain_perspective(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float
) -> Dict[str, Any]:
    """
    基于船长经验的船舶性能评估

    船长经验要点：
    1. 船舶在不同天气下的实际操纵性能
    2. 燃油消耗与航速的关系
    3. 船舶稳定性与安全性
    4. 航线规划和避风策略
    5. 货物运输效率

    :param vessel_data: 船舶基础数据
    :param weather_performance: 天气性能数据
    :param design_speed: 设计速度
    :return: 船长视角的性能评估
    """
    assessment = {
        'captain_assessment': {},
        'operational_recommendations': [],
        'safety_considerations': [],
        'commercial_insights': [],
        'vessel_rating': {}
    }

    # 船舶基础信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
    length = vessel_data.get('length', 0)
    width = vessel_data.get('width', 0)
    dwt = vessel_data.get('dwt', 0)
    build_year = vessel_data.get('buildYear', 0)

    # 性能分析
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_weather_speed', 0)

    # 1. 船舶操纵性能评估
    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100

        # 基于船长经验的性能评级
        if speed_reduction <= 10:
            assessment['vessel_rating']['weather_adaptability'] = 'excellent'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下表现优异，具有良好的适航性'
        elif speed_reduction <= 20:
            assessment['vessel_rating']['weather_adaptability'] = 'good'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下表现良好，适合大多数航线'
        elif speed_reduction <= 30:
            assessment['vessel_rating']['weather_adaptability'] = 'fair'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下性能一般，需要谨慎选择航线'
        else:
            assessment['vessel_rating']['weather_adaptability'] = 'poor'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下性能较差，建议避风航行'

    # 2. 燃油效率评估
    if good_speed > 0:
        # 基于船长经验的燃油消耗估算
        fuel_consumption_good = estimate_fuel_consumption(
            good_speed, dwt, vessel_type)
        fuel_consumption_bad = estimate_fuel_consumption(
            bad_speed, dwt, vessel_type) if bad_speed > 0 else 0

        assessment['captain_assessment']['fuel_efficiency'] = {
            'good_weather_consumption': fuel_consumption_good,
            'bad_weather_consumption': fuel_consumption_bad,
            'consumption_increase': round(((fuel_consumption_bad - fuel_consumption_good) / fuel_consumption_good) * 100, 2) if fuel_consumption_good > 0 else 0
        }

    # 3. 船舶稳定性评估
    stability_assessment = assess_vessel_stability(
        vessel_data, weather_performance)
    assessment['captain_assessment']['stability'] = stability_assessment

    # 4. 航线规划建议
    route_recommendations = generate_route_recommendations(
        vessel_data, weather_performance)
    assessment['operational_recommendations'].extend(route_recommendations)

    # 5. 商业价值评估
    commercial_value = assess_commercial_value(
        vessel_data, weather_performance, design_speed)
    assessment['commercial_insights'] = commercial_value

    return assessment


def estimate_fuel_consumption(speed: float, dwt: float, vessel_type: str) -> float:
    """
    基于船长经验的燃油消耗估算

    船长经验公式：
    - 燃油消耗与航速的立方成正比
    - 不同船型有不同的燃油效率
    - 载重吨位影响燃油消耗
    """
    base_consumption = 0

    # 基于船型的基础消耗率
    if '集装箱' in vessel_type:
        base_consumption = 25  # 吨/天
    elif '干散货' in vessel_type:
        base_consumption = 20  # 吨/天
    elif '油轮' in vessel_type or '液体散货' in vessel_type:
        base_consumption = 22  # 吨/天
    else:
        base_consumption = 18  # 吨/天

    # 基于载重吨位的调整
    dwt_factor = min(dwt / 50000, 2.0)  # 最大2倍

    # 基于航速的调整（立方关系）
    speed_factor = (speed / 14.0) ** 3  # 以14节为基准

    daily_consumption = base_consumption * dwt_factor * speed_factor

    return round(daily_consumption, 2)


def assess_vessel_stability(vessel_data: Dict[str, Any], weather_performance: Dict[str, float]) -> Dict[str, Any]:
    """
    基于船长经验的船舶稳定性评估
    """
    stability = {
        'overall_rating': 'good',
        'factors': [],
        'concerns': []
    }

    length = vessel_data.get('length', 0)
    width = vessel_data.get('width', 0)
    dwt = vessel_data.get('dwt', 0)

    # 船长经验：长宽比影响稳定性
    if length > 0 and width > 0:
        length_width_ratio = length / width
        if length_width_ratio > 7:
            stability['factors'].append('长宽比较大，在恶劣天气下可能影响稳定性')
            stability['overall_rating'] = 'fair'
        elif length_width_ratio < 5:
            stability['factors'].append('长宽比较小，稳定性较好')
        else:
            stability['factors'].append('长宽比适中，稳定性良好')

    # 基于性能数据的稳定性评估
    severe_speed = weather_performance.get('avg_severe_weather_speed', 0)
    moderate_speed = weather_performance.get(
        'avg_moderate_bad_weather_speed', 0)

    if severe_speed > 0 and moderate_speed > 0:
        speed_drop = ((moderate_speed - severe_speed) / moderate_speed) * 100
        if speed_drop > 25:
            stability['concerns'].append('在恶劣天气下速度下降明显，可能存在稳定性问题')
            stability['overall_rating'] = 'fair'
        elif speed_drop < 10:
            stability['factors'].append('在恶劣天气下速度保持稳定，船舶稳定性良好')

    return stability


def generate_route_recommendations(vessel_data: Dict[str, Any], weather_performance: Dict[str, float]) -> List[str]:
    """
    基于船长经验的航线规划建议
    """
    recommendations = []

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    severe_speed = weather_performance.get('avg_severe_weather_speed', 0)
    moderate_speed = weather_performance.get(
        'avg_moderate_bad_weather_speed', 0)

    # 基于船型的航线建议
    if '集装箱' in vessel_type:
        recommendations.append('集装箱船对时间要求高，建议选择避风航线或增加备用时间')
    elif '干散货' in vessel_type:
        recommendations.append('干散货船可适当调整航线避开恶劣天气区域')
    elif '油轮' in vessel_type:
        recommendations.append('油轮安全要求高，建议严格避风航行')

    # 基于性能的航线建议
    if severe_speed < 8:  # 恶劣天气下速度过低
        recommendations.append('船舶在恶劣天气下速度较低，建议选择避风航线')
    elif moderate_speed > 12:  # 中等坏天气下速度尚可
        recommendations.append('船舶在中等坏天气下性能良好，可考虑优化航线')

    return recommendations


def assess_commercial_value(vessel_data: Dict[str, Any], weather_performance: Dict[str, float], design_speed: float) -> List[str]:
    """
    基于船长经验的商业价值评估
    """
    insights = []

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    build_year = vessel_data.get('buildYear', 0)
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)

    # 船舶年龄评估
    current_year = 2024
    try:
        build_year_int = int(build_year) if build_year else 0
        vessel_age = current_year - build_year_int if build_year_int > 0 else 0
    except (ValueError, TypeError):
        vessel_age = 0

    if vessel_age > 20:
        insights.append('船舶年龄较大，可能影响在恶劣天气下的性能表现')
    elif vessel_age < 10:
        insights.append('船舶较新，在恶劣天气下应有良好表现')

    # 性能与设计速度对比
    if good_speed > 0 and design_speed > 0:
        performance_ratio = (good_speed / design_speed) * 100
        if performance_ratio < 80:
            insights.append('船舶实际性能低于设计标准，可能影响商业价值')
        elif performance_ratio > 95:
            insights.append('船舶性能优异，具有较高的商业价值')

    # 天气适应性评估
    if good_speed > 0 and bad_speed > 0:
        weather_adaptability = (bad_speed / good_speed) * 100
        if weather_adaptability > 85:
            insights.append('船舶天气适应性极佳，适合全年运营')
        elif weather_adaptability < 60:
            insights.append('船舶天气适应性较差，可能影响全年运营效率')

    return insights


def analyze_vessel_for_trading_and_chartering(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float,
    market_conditions: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    为买卖船和租船业务提供专业的船舶分析

    船长和航运专家视角：
    1. 船舶在不同天气下的实际商业价值
    2. 燃油成本对盈利能力的影响
    3. 船舶的全年运营能力
    4. 航线适应性和市场竞争力
    5. 投资回报率和风险评估

    :param vessel_data: 船舶基础数据
    :param weather_performance: 天气性能数据
    :param design_speed: 设计速度
    :param market_conditions: 市场条件（可选）
    :return: 买卖船和租船分析结果
    """
    analysis = {
        'trading_analysis': {},
        'chartering_analysis': {},
        'financial_impact': {},
        'risk_assessment': {},
        'market_recommendations': []
    }

    # 船舶基础信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    dwt = vessel_data.get('dwt', 0)
    build_year = vessel_data.get('buildYear', 0)
    length = vessel_data.get('length', 0)
    width = vessel_data.get('width', 0)

    # 性能数据
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_weather_speed', 0)
    moderate_speed = weather_performance.get(
        'avg_moderate_bad_weather_speed', 0)

    # 1. 买卖船分析
    trading_analysis = analyze_vessel_for_trading(
        vessel_data, weather_performance, design_speed, market_conditions or {}
    )
    analysis['trading_analysis'] = trading_analysis

    # 2. 租船分析
    chartering_analysis = analyze_vessel_for_chartering(
        vessel_data, weather_performance, design_speed, market_conditions or {}
    )
    analysis['chartering_analysis'] = chartering_analysis

    # 3. 财务影响分析
    financial_impact = calculate_financial_impact(
        vessel_data, weather_performance, design_speed
    )
    analysis['financial_impact'] = financial_impact

    # 4. 风险评估
    risk_assessment = assess_trading_and_chartering_risks(
        vessel_data, weather_performance, design_speed
    )
    analysis['risk_assessment'] = risk_assessment

    # 5. 市场建议
    market_recommendations = generate_market_recommendations(
        vessel_data, weather_performance, trading_analysis, chartering_analysis
    )
    analysis['market_recommendations'] = market_recommendations

    return analysis


def analyze_vessel_for_trading(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float,
    market_conditions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    买卖船分析
    """
    analysis = {
        'vessel_value': {},
        'investment_potential': {},
        'resale_considerations': [],
        'buying_recommendations': []
    }

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    build_year = vessel_data.get('buildYear', 0)
    dwt = vessel_data.get('dwt', 0)
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)

    # 船舶价值评估
    current_year = 2024
    try:
        build_year_int = int(build_year) if build_year else 0
        vessel_age = current_year - build_year_int if build_year_int > 0 else 0
    except (ValueError, TypeError):
        vessel_age = 0

    # 基于年龄的价值评估
    if vessel_age <= 5:
        age_factor = 1.0
        analysis['vessel_value']['age_rating'] = 'excellent'
    elif vessel_age <= 10:
        age_factor = 0.9
        analysis['vessel_value']['age_rating'] = 'good'
    elif vessel_age <= 15:
        age_factor = 0.8
        analysis['vessel_value']['age_rating'] = 'fair'
    else:
        age_factor = 0.6
        analysis['vessel_value']['age_rating'] = 'poor'

    # 基于性能的价值评估
    if good_speed > 0 and design_speed > 0:
        performance_factor = min(good_speed / design_speed, 1.2)  # 最高1.2倍
    else:
        performance_factor = 0.8

    # 天气适应性价值
    if good_speed > 0 and bad_speed > 0:
        weather_factor = (bad_speed / good_speed) * 1.2  # 天气适应性好的船舶价值更高
    else:
        weather_factor = 1.0

    # 综合价值评估
    total_value_factor = age_factor * performance_factor * weather_factor
    analysis['vessel_value']['total_value_factor'] = round(
        total_value_factor, 3)

    # 投资潜力评估
    if total_value_factor >= 1.0:
        analysis['investment_potential']['rating'] = 'high'
        analysis['investment_potential']['description'] = '船舶具有较高的投资价值'
    elif total_value_factor >= 0.8:
        analysis['investment_potential']['rating'] = 'medium'
        analysis['investment_potential']['description'] = '船舶具有中等投资价值'
    else:
        analysis['investment_potential']['rating'] = 'low'
        analysis['investment_potential']['description'] = '船舶投资价值较低'

    # 转售考虑
    if vessel_age > 20:
        analysis['resale_considerations'].append('船舶年龄较大，转售时可能面临价值大幅下降')
    elif weather_factor < 0.7:
        analysis['resale_considerations'].append('船舶天气适应性较差，可能影响转售价值')
    else:
        analysis['resale_considerations'].append('船舶具有良好的转售潜力')

    # 购买建议
    if total_value_factor >= 1.0 and weather_factor >= 0.8:
        analysis['buying_recommendations'].append('强烈推荐购买，船舶性能优异且天气适应性良好')
    elif total_value_factor >= 0.8:
        analysis['buying_recommendations'].append('建议购买，但需要关注天气适应性')
    else:
        analysis['buying_recommendations'].append('谨慎考虑，建议进一步评估')

    return analysis


def analyze_vessel_for_chartering(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float,
    market_conditions: Dict[str, Any]
) -> Dict[str, Any]:
    """
    租船分析
    """
    analysis = {
        'charter_potential': {},
        'operational_efficiency': {},
        'charter_recommendations': [],
        'rate_considerations': []
    }

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    dwt = vessel_data.get('dwt', 0)
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_weather_speed', 0)

    # 租船潜力评估
    if good_speed > 0 and bad_speed > 0:
        weather_adaptability = (bad_speed / good_speed) * 100

        if weather_adaptability >= 85:
            analysis['charter_potential']['rating'] = 'excellent'
            analysis['charter_potential']['description'] = '船舶天气适应性极佳，适合全年租船'
        elif weather_adaptability >= 70:
            analysis['charter_potential']['rating'] = 'good'
            analysis['charter_potential']['description'] = '船舶天气适应性良好，适合大部分航线'
        elif weather_adaptability >= 50:
            analysis['charter_potential']['rating'] = 'fair'
            analysis['charter_potential']['description'] = '船舶天气适应性一般，需要谨慎选择航线'
        else:
            analysis['charter_potential']['rating'] = 'poor'
            analysis['charter_potential']['description'] = '船舶天气适应性较差，租船风险较高'
    else:
        # 如果没有足够的数据，设置默认值
        analysis['charter_potential']['rating'] = 'unknown'
        analysis['charter_potential']['description'] = '数据不足，无法评估租船潜力'

    # 运营效率评估
    if good_speed > 0:
        # 基于船长经验的运营效率计算
        operational_days_good = 365 * 0.85  # 好天气下85%的运营时间
        operational_days_bad = 365 * 0.15   # 坏天气下15%的运营时间

        total_distance_good = good_speed * 24 * operational_days_good
        total_distance_bad = bad_speed * 24 * operational_days_bad
        total_distance = total_distance_good + total_distance_bad

        analysis['operational_efficiency']['annual_distance'] = round(
            total_distance, 0)
        analysis['operational_efficiency']['average_speed'] = round(
            total_distance / (365 * 24), 2)

    # 租船建议
    charter_rating = analysis['charter_potential'].get('rating', 'unknown')
    if charter_rating in ['excellent', 'good']:
        analysis['charter_recommendations'].append('船舶适合长期租船，具有稳定的收益潜力')
        analysis['charter_recommendations'].append('建议与信誉良好的租船人合作')
    elif charter_rating == 'fair':
        analysis['charter_recommendations'].append('船舶适合短期租船，需要仔细选择航线')
        analysis['charter_recommendations'].append('建议在好天气季节进行租船')
    else:
        analysis['charter_recommendations'].append('船舶租船风险较高，建议谨慎考虑')
        analysis['charter_recommendations'].append('可以考虑作为备用船舶或特定航线使用')

    # 租金考虑
    if charter_rating == 'excellent':
        analysis['rate_considerations'].append('船舶性能优异，可以要求较高的租金')
    elif charter_rating == 'good':
        analysis['rate_considerations'].append('船舶性能良好，租金可以略高于市场平均水平')
    elif charter_rating == 'fair':
        analysis['rate_considerations'].append('船舶性能一般，租金应与市场平均水平相当')
    else:
        analysis['rate_considerations'].append('船舶性能较差，租金应低于市场平均水平以吸引租船人')

    return analysis


def calculate_financial_impact(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float
) -> Dict[str, Any]:
    """
    计算财务影响
    """
    impact = {
        'fuel_cost_analysis': {},
        'operational_cost_analysis': {},
        'revenue_impact': {},
        'profitability_analysis': {}
    }

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    dwt = vessel_data.get('dwt', 0)
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)

    # 燃油成本分析
    if good_speed > 0:
        fuel_good = estimate_fuel_consumption(good_speed, dwt, vessel_type)
        fuel_bad = estimate_fuel_consumption(
            bad_speed, dwt, vessel_type) if bad_speed > 0 else fuel_good

        # 假设燃油价格600美元/吨
        fuel_price = 600
        annual_fuel_cost_good = fuel_good * 365 * fuel_price
        annual_fuel_cost_bad = fuel_bad * 365 * fuel_price

        impact['fuel_cost_analysis'] = {
            'good_weather_annual_cost': round(annual_fuel_cost_good, 0),
            'bad_weather_annual_cost': round(annual_fuel_cost_bad, 0),
            'cost_increase_percentage': round(((annual_fuel_cost_bad - annual_fuel_cost_good) / annual_fuel_cost_good) * 100, 2) if annual_fuel_cost_good > 0 else 0
        }
    else:
        # 如果数据不足，设置默认值
        impact['fuel_cost_analysis'] = {
            'good_weather_annual_cost': 0,
            'bad_weather_annual_cost': 0,
            'cost_increase_percentage': 0
        }

    # 运营成本分析
    # 基于船长经验：运营成本包括船员、维护、保险等
    base_operational_cost = dwt * 2  # 每吨载重2美元的年度运营成本

    impact['operational_cost_analysis'] = {
        'annual_operational_cost': round(base_operational_cost, 0),
        'cost_per_day': round(base_operational_cost / 365, 2)
    }

    # 收入影响分析
    if good_speed > 0 and bad_speed > 0:
        # 假设每海里收入10美元
        revenue_per_nm = 10
        annual_revenue_good = good_speed * 24 * 365 * revenue_per_nm
        annual_revenue_bad = bad_speed * 24 * 365 * revenue_per_nm

        impact['revenue_impact'] = {
            'good_weather_annual_revenue': round(annual_revenue_good, 0),
            'bad_weather_annual_revenue': round(annual_revenue_bad, 0),
            'revenue_decrease_percentage': round(((annual_revenue_good - annual_revenue_bad) / annual_revenue_good) * 100, 2) if annual_revenue_good > 0 else 0
        }
    else:
        # 如果数据不足，设置默认值
        impact['revenue_impact'] = {
            'good_weather_annual_revenue': 0,
            'bad_weather_annual_revenue': 0,
            'revenue_decrease_percentage': 0
        }

    # 盈利能力分析
    if ('fuel_cost_analysis' in impact and 'revenue_impact' in impact and
        'good_weather_annual_cost' in impact['fuel_cost_analysis'] and
            'good_weather_annual_revenue' in impact['revenue_impact']):

        fuel_cost = impact['fuel_cost_analysis']['good_weather_annual_cost']
        operational_cost = impact['operational_cost_analysis']['annual_operational_cost']
        revenue = impact['revenue_impact']['good_weather_annual_revenue']

        profit = revenue - fuel_cost - operational_cost
        profit_margin = (profit / revenue) * 100 if revenue > 0 else 0

        impact['profitability_analysis'] = {
            'annual_profit': round(profit, 0),
            'profit_margin_percentage': round(profit_margin, 2),
            # 假设船舶价值为载重吨位*1000美元
            'roi_estimate': round((profit / (dwt * 1000)) * 100, 2)
        }
    else:
        # 如果数据不足，设置默认值
        impact['profitability_analysis'] = {
            'annual_profit': 0,
            'profit_margin_percentage': 0,
            'roi_estimate': 0
        }

    return impact


def assess_trading_and_chartering_risks(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float
) -> Dict[str, Any]:
    """
    评估买卖船和租船风险
    """
    risks = {
        'operational_risks': [],
        'financial_risks': [],
        'market_risks': [],
        'risk_level': 'medium'
    }

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    build_year = vessel_data.get('buildYear', 0)
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_weather_speed', 0)

    # 运营风险
    if severe_speed < 8:
        risks['operational_risks'].append('船舶在恶劣天气下速度过低，存在运营风险')

    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
        if speed_reduction > 30:
            risks['operational_risks'].append('船舶在坏天气下性能下降严重，运营风险较高')

    # 财务风险
    current_year = 2024
    try:
        build_year_int = int(build_year) if build_year else 0
        vessel_age = current_year - build_year_int if build_year_int > 0 else 0
    except (ValueError, TypeError):
        vessel_age = 0

    if vessel_age > 20:
        risks['financial_risks'].append('船舶年龄较大，维护成本可能增加')

    if good_speed > 0 and design_speed > 0:
        performance_ratio = (good_speed / design_speed) * 100
        if performance_ratio < 80:
            risks['financial_risks'].append('船舶实际性能低于设计标准，可能影响盈利能力')

    # 市场风险
    if '集装箱' in vessel_type:
        risks['market_risks'].append('集装箱船市场竞争激烈，需要关注运价波动')
    elif '干散货' in vessel_type:
        risks['market_risks'].append('干散货船受大宗商品价格影响较大')
    elif '油轮' in vessel_type:
        risks['market_risks'].append('油轮受油价波动影响较大')

    # 综合风险等级
    risk_count = len(risks['operational_risks']) + \
        len(risks['financial_risks']) + len(risks['market_risks'])

    if risk_count <= 2:
        risks['risk_level'] = 'low'
    elif risk_count <= 4:
        risks['risk_level'] = 'medium'
    else:
        risks['risk_level'] = 'high'

    return risks


def generate_market_recommendations(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    trading_analysis: Dict[str, Any],
    chartering_analysis: Dict[str, Any]
) -> List[str]:
    """
    生成市场建议
    """
    recommendations = []

    vessel_type = vessel_data.get('vesselTypeNameCn', '')

    # 基于买卖船分析的建议
    if trading_analysis.get('investment_potential', {}).get('rating') == 'high':
        recommendations.append('船舶具有较高的投资价值，建议考虑购买')
    elif trading_analysis.get('investment_potential', {}).get('rating') == 'low':
        recommendations.append('船舶投资价值较低，建议谨慎考虑或寻找其他机会')

    # 基于租船分析的建议
    if chartering_analysis.get('charter_potential', {}).get('rating') in ['excellent', 'good']:
        recommendations.append('船舶适合租船业务，建议寻找长期租船合同')
    elif chartering_analysis.get('charter_potential', {}).get('rating') == 'poor':
        recommendations.append('船舶租船风险较高，建议考虑其他商业模式')

    # 基于船型的特定建议
    if '集装箱' in vessel_type:
        recommendations.append('集装箱船建议关注主要航线运价趋势')
    elif '干散货' in vessel_type:
        recommendations.append('干散货船建议关注大宗商品需求和运价指数')
    elif '油轮' in vessel_type:
        recommendations.append('油轮建议关注油价走势和地缘政治风险')

    # 基于性能的建议
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)

    if good_speed > 0 and bad_speed > 0:
        weather_adaptability = (bad_speed / good_speed) * 100
        if weather_adaptability > 85:
            recommendations.append('船舶天气适应性极佳，适合全年运营，具有竞争优势')
        elif weather_adaptability < 60:
            recommendations.append('船舶天气适应性较差，建议在好天气季节重点运营')

    return recommendations


class CalcVesselPerformanceDetailsFromWmy(BaseModel):
    def __init__(self):
        # "客船,干散货,杂货船,液体散货,特种船,集装箱"]
        self.vessel_types = os.getenv('VESSEL_TYPES', "")
        self.wmy_url = os.getenv('WMY_URL', "http://192.168.1.128")
        self.wmy_url_port = os.getenv('WMY_URL_PORT', "10020")
        self.time_sleep = os.getenv('TIME_SLEEP', "0.2")
        self.time_days = int(os.getenv('TIME_DAYS', "7"))
        self.calc_days = int(os.getenv('CALC_DAYS', "180"))

        if self.vessel_types:
            self.vessel_types = self.vessel_types.split(",")
        else:
            self.vessel_types = []
        config = {
            'ck_client': True,
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'vessels_performance_details',
            'uniq_idx': [
                ('mmsi', pymongo.ASCENDING),
            ]
        }

        super(CalcVesselPerformanceDetailsFromWmy, self).__init__(config)

        # 配置连接池以提高连接稳定性
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 我们自己在代码中处理重试
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def deal_good_perf_list(self, data: List[Dict[str, Any]], DESIGN_DRAFT: float, DESIGN_SPEED: float) -> Dict[str, float]:
        """
        处理船舶数据列表，计算符合条件的平均船速（优化版）
        新增功能：根据吃水(draft)区分空载(<70%)和满载(>80%)船速
        """
        # 设计吃水深度阈值
        EMPTY_LOAD = DESIGN_DRAFT * 0.7  # 70%
        FULL_LOAD = DESIGN_DRAFT * 0.8   # 80%

        # 初始化累加器
        stats = {
            'empty': SpeedStats(),           # 空载统计
            'full': SpeedStats(),            # 满载统计
            'empty_downstream': SpeedStats(),  # 空载顺流
            'empty_upstream': SpeedStats(),   # 空载逆流
            'full_downstream': SpeedStats(),  # 满载顺流
            'full_upstream': SpeedStats(),    # 满载逆流
            'downstream': SpeedStats(),       # 总体顺流
            'upstream': SpeedStats(),         # 总体逆流
        }

        # 数据预处理和验证
        valid_data = []
        for item in data:
            try:
                # 基础数据验证
                if not all(is_valid_type(item.get(field)) for field in ["wind_level", "wave_height", "hdg", "sog", "draught"]):
                    continue

                # 数值转换和范围验证
                wind_level = int(item.get("wind_level", 5))
                wave_height = float(item.get("wave_height", 1.26))
                sog = float(item.get("sog", 0.0))
                draught = float(item.get("draught"))
                hdg = float(item.get("hdg"))

                # 条件筛选
                if (wind_level <= 4 and
                    wave_height <= 1.25 and
                        sog >= DESIGN_SPEED * 0.5):
                    valid_data.append({
                        'draught': draught,
                        'sog': sog,
                        'hdg': hdg,
                        'current_u': item.get("current_u"),
                        'current_v': item.get("current_v")
                    })
            except (ValueError, TypeError):
                continue

        # 处理有效数据
        for item in valid_data:
            draught = item['draught']
            sog = item['sog']
            hdg = item['hdg']
            current_u = item['current_u']
            current_v = item['current_v']

            # 判断载重状态
            is_empty = draught < EMPTY_LOAD
            is_full = draught > FULL_LOAD

            # 判断流向（如果有洋流数据）
            is_downstream = False
            if is_valid_current_data(current_u, current_v):
                is_downstream = is_sailing_downstream(
                    float(current_u), float(current_v), hdg)

            # 更新统计
            if is_empty:
                stats['empty'].add(sog)
                if is_downstream:
                    stats['empty_downstream'].add(sog)
                    stats['downstream'].add(sog)
                else:
                    stats['empty_upstream'].add(sog)
                    stats['upstream'].add(sog)
            elif is_full:
                stats['full'].add(sog)
                if is_downstream:
                    stats['full_downstream'].add(sog)
                    stats['downstream'].add(sog)
                else:
                    stats['full_upstream'].add(sog)
                    stats['upstream'].add(sog)

        # 构建结果
        performance = {
            "avg_good_weather_speed": round(
                (stats['empty'].total + stats['full'].total) /
                (stats['empty'].count + stats['full'].count), 2
            ) if (stats['empty'].count + stats['full'].count) > 0 else 0.0,
            "avg_downstream_speed": stats['downstream'].average(),
            "avg_non_downstream_speed": stats['upstream'].average(),
        }

        # 添加载重相关统计
        if stats['empty'].count > 0:
            performance.update({
                "avg_ballast_speed": stats['empty'].average(),
                "avg_ballast_downstream_speed": stats['empty_downstream'].average(),
                "avg_ballast_non_downstream_speed": stats['empty_upstream'].average(),
            })

        if stats['full'].count > 0:
            performance.update({
                "avg_laden_speed": stats['full'].average(),
                "avg_laden_downstream_speed": stats['full_downstream'].average(),
                "avg_laden_non_downstream_speed": stats['full_upstream'].average(),
            })

        # 打印统计信息
        # print(f"数据统计: 空载={stats['empty'].count}, 满载={stats['full'].count}, "
        #       f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}")

        return performance

    def deal_bad_perf_list(self, data: List[Dict[str, Any]], DESIGN_DRAFT: float, DESIGN_SPEED: float) -> Dict[str, float]:
        """
        处理船舶数据列表，计算坏天气条件下的平均船速
        坏天气判断标准（具有参考意义）：
        1. 风力等级 >= 6级 (强风及以上)
        2. 浪高 >= 2.0米 (中浪及以上)
        3. 或者风力等级 >= 5级且浪高 >= 1.5米 (组合条件)
        4. 船速 >= 设计速度的30% (确保船舶在航行状态)

        参考标准来源：
        - 国际海事组织(IMO)航行安全指南
        - 中国海事局船舶航行安全规定
        - 航运业实践经验
        """
        # 设计吃水深度阈值
        EMPTY_LOAD = DESIGN_DRAFT * 0.7  # 70%
        FULL_LOAD = DESIGN_DRAFT * 0.8   # 80%

        # 初始化累加器
        stats = {
            'bad_weather': SpeedStats(),           # 坏天气总体统计
            'empty': SpeedStats(),                  # 空载统计
            'full': SpeedStats(),                   # 满载统计
            'empty_downstream': SpeedStats(),       # 空载顺流
            'empty_upstream': SpeedStats(),        # 空载逆流
            'full_downstream': SpeedStats(),       # 满载顺流
            'full_upstream': SpeedStats(),         # 满载逆流
            'downstream': SpeedStats(),            # 总体顺流
            'upstream': SpeedStats(),              # 总体逆流
            'severe_weather': SpeedStats(),        # 恶劣天气统计
            'moderate_bad_weather': SpeedStats(),  # 中等坏天气统计
        }

        # 数据预处理和验证
        valid_data = []
        for item in data:
            try:
                # 基础数据验证
                if not all(is_valid_type(item.get(field)) for field in ["wind_level", "wave_height", "hdg", "sog", "draught"]):
                    continue

                # 数值转换和范围验证
                wind_level = int(item.get("wind_level", 5))
                wave_height = float(item.get("wave_height", 1.26))
                sog = float(item.get("sog", 0.0))
                draught = float(item.get("draught"))
                hdg = float(item.get("hdg"))

                # 使用天气分类函数判断坏天气条件
                weather_info = classify_weather_conditions(
                    wind_level, wave_height)
                is_bad_weather = weather_info['weather_type'] in [
                    'moderate_bad', 'severe_bad']
                weather_severity = weather_info['weather_type']

                # 确保船舶在航行状态
                if is_bad_weather and sog >= DESIGN_SPEED * 0.3:
                    valid_data.append({
                        'draught': draught,
                        'sog': sog,
                        'hdg': hdg,
                        'current_u': item.get("current_u"),
                        'current_v': item.get("current_v"),
                        'wind_level': wind_level,
                        'wave_height': wave_height,
                        'weather_severity': weather_severity
                    })
            except (ValueError, TypeError):
                continue

        # 处理有效数据
        for item in valid_data:
            draught = item['draught']
            sog = item['sog']
            hdg = item['hdg']
            current_u = item['current_u']
            current_v = item['current_v']
            weather_severity = item['weather_severity']

            # 判断载重状态
            is_empty = draught < EMPTY_LOAD
            is_full = draught > FULL_LOAD

            # 判断流向（如果有洋流数据）
            is_downstream = False
            if is_valid_current_data(current_u, current_v):
                is_downstream = is_sailing_downstream(
                    float(current_u), float(current_v), hdg)

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
                if is_downstream:
                    stats['empty_downstream'].add(sog)
                    stats['downstream'].add(sog)
                else:
                    stats['empty_upstream'].add(sog)
                    stats['upstream'].add(sog)
            elif is_full:
                stats['full'].add(sog)
                if is_downstream:
                    stats['full_downstream'].add(sog)
                    stats['downstream'].add(sog)
                else:
                    stats['full_upstream'].add(sog)
                    stats['upstream'].add(sog)

        # 构建结果
        performance = {
            "avg_bad_weather_speed": stats['bad_weather'].average(),
            "avg_downstream_bad_weather_speed": stats['downstream'].average(),
            "avg_non_downstream_bad_weather_speed": stats['upstream'].average(),
            "avg_severe_weather_speed": stats['severe_weather'].average(),
            "avg_moderate_bad_weather_speed": stats['moderate_bad_weather'].average(),
        }

        # 添加载重相关统计
        if stats['empty'].count > 0:
            performance.update({
                "avg_ballast_bad_weather_speed": stats['empty'].average(),
                "avg_ballast_downstream_bad_weather_speed": stats['empty_downstream'].average(),
                "avg_ballast_non_downstream_bad_weather_speed": stats['empty_upstream'].average(),
            })

        if stats['full'].count > 0:
            performance.update({
                "avg_laden_bad_weather_speed": stats['full'].average(),
                "avg_laden_downstream_bad_weather_speed": stats['full_downstream'].average(),
                "avg_laden_non_downstream_bad_weather_speed": stats['full_upstream'].average(),
            })

        # 打印统计信息
        # print(f"坏天气数据统计: 总体={stats['bad_weather'].count}, "
        #       f"空载={stats['empty'].count}, 满载={stats['full'].count}, "
        #       f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}, "
        #       f"恶劣天气={stats['severe_weather'].count}, 中等坏天气={stats['moderate_bad_weather'].count}")

        return performance

    def analyze_performance_comparison(self, good_weather_perf: Dict[str, float],
                                       bad_weather_perf: Dict[str, float],
                                       design_speed: float) -> Dict[str, Any]:
        """
        分析好天气与坏天气性能对比

        :param good_weather_perf: 好天气性能数据
        :param bad_weather_perf: 坏天气性能数据
        :param design_speed: 设计速度
        :return: 性能对比分析结果
        """
        analysis = {
            'performance_comparison': {},
            'speed_reduction_analysis': {},
            'safety_recommendations': [],
            'operational_insights': []
        }

        # 基础性能对比
        if good_weather_perf.get('avg_good_weather_speed', 0) > 0:
            good_speed = good_weather_perf['avg_good_weather_speed']
            bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0)

            if bad_speed > 0:
                # 计算速度降低比例
                speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
                analysis['performance_comparison'].update({
                    'good_weather_speed': good_speed,
                    'bad_weather_speed': bad_speed,
                    'speed_reduction_percentage': round(speed_reduction, 2),
                    'speed_reduction_knots': round(good_speed - bad_speed, 2)
                })

                # 速度降低分析
                if speed_reduction > 30:
                    analysis['speed_reduction_analysis']['level'] = 'high'
                    analysis['speed_reduction_analysis']['description'] = '严重速度降低'
                    analysis['safety_recommendations'].append('建议在恶劣天气下考虑避风锚地')
                elif speed_reduction > 15:
                    analysis['speed_reduction_analysis']['level'] = 'moderate'
                    analysis['speed_reduction_analysis']['description'] = '中等速度降低'
                    analysis['safety_recommendations'].append('建议适当调整航速和航线')
                else:
                    analysis['speed_reduction_analysis']['level'] = 'low'
                    analysis['speed_reduction_analysis']['description'] = '轻微速度降低'
                    analysis['safety_recommendations'].append('注意天气变化，保持正常航行')

        # 载重状态性能对比
        if good_weather_perf.get('avg_ballast_speed', 0) > 0 and bad_weather_perf.get('avg_ballast_bad_weather_speed', 0) > 0:
            ballast_reduction = ((good_weather_perf['avg_ballast_speed'] - bad_weather_perf['avg_ballast_bad_weather_speed']) /
                                 good_weather_perf['avg_ballast_speed']) * 100
            analysis['performance_comparison']['ballast_speed_reduction'] = round(
                ballast_reduction, 2)

        if good_weather_perf.get('avg_laden_speed', 0) > 0 and bad_weather_perf.get('avg_laden_bad_weather_speed', 0) > 0:
            laden_reduction = ((good_weather_perf['avg_laden_speed'] - bad_weather_perf['avg_laden_bad_weather_speed']) /
                               good_weather_perf['avg_laden_speed']) * 100
            analysis['performance_comparison']['laden_speed_reduction'] = round(
                laden_reduction, 2)

        # 流向性能对比
        if good_weather_perf.get('avg_downstream_speed', 0) > 0 and bad_weather_perf.get('avg_downstream_bad_weather_speed', 0) > 0:
            downstream_reduction = ((good_weather_perf['avg_downstream_speed'] - bad_weather_perf['avg_downstream_bad_weather_speed']) /
                                    good_weather_perf['avg_downstream_speed']) * 100
            analysis['performance_comparison']['downstream_speed_reduction'] = round(
                downstream_reduction, 2)

        # 恶劣天气分析
        severe_speed = bad_weather_perf.get('avg_severe_weather_speed', 0)
        moderate_speed = bad_weather_perf.get(
            'avg_moderate_bad_weather_speed', 0)

        if severe_speed > 0 and moderate_speed > 0:
            severe_vs_moderate = (
                (moderate_speed - severe_speed) / moderate_speed) * 100
            analysis['performance_comparison']['severe_vs_moderate_reduction'] = round(
                severe_vs_moderate, 2)

            if severe_vs_moderate > 20:
                analysis['operational_insights'].append(
                    '恶劣天气对船舶性能影响显著，建议加强天气监测')
            else:
                analysis['operational_insights'].append('船舶在恶劣天气下仍保持相对稳定的性能')

        # 设计速度对比
        if design_speed > 0:
            good_vs_design = (good_weather_perf.get(
                'avg_good_weather_speed', 0) / design_speed) * 100
            bad_vs_design = (bad_weather_perf.get(
                'avg_bad_weather_speed', 0) / design_speed) * 100

            analysis['performance_comparison'].update({
                'good_weather_vs_design_percentage': round(good_vs_design, 2),
                'bad_weather_vs_design_percentage': round(bad_vs_design, 2)
            })

            if good_vs_design < 80:
                analysis['operational_insights'].append(
                    '好天气下船舶性能未达到设计标准，建议检查船舶状态')
            if bad_vs_design < 50:
                analysis['operational_insights'].append(
                    '坏天气下船舶性能显著下降，需要优化航行策略')

        return analysis

    def get_vessel_trace(self, mmsi: int, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """
        获取船舶轨迹数据
        :param mmsi: 船舶MMSI号
        :param start_time: 开始时间戳（毫秒）
        :param end_time: 结束时间戳（毫秒）
        :return: 轨迹数据列表
        """
        url = f"{self.wmy_url}:{self.wmy_url_port}/api/vessel/trace"
        # 构造请求体，使用当前vessel的mmsi，时间戳可根据需要调整
        data = {
            "mmsi": mmsi,
            "interval_hour": 3,
            "start_timestamp": start_time,
            "end_timestamp": end_time
        }

        # 重试配置
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                # 增加连接超时和读取超时
                response = self.session.post(
                    url,
                    json=data,
                    verify=False,
                    timeout=(30, 120),  # (连接超时, 读取超时)
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'VesselPerformanceCalculator/1.0'
                    }
                )

                # 检查HTTP状态码
                if response.status_code != 200:
                    logger.error(f"HTTP请求失败，状态码: {response.status_code}")
                    logger.error(f"响应内容: {response.text[:200]}...")
                    if attempt < max_retries - 1:
                        logger.warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

                # 检查响应内容是否为空
                if not response.text.strip():
                    logger.warning(f"API返回空响应")
                    if attempt < max_retries - 1:
                        logger.warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

                # 尝试解析JSON
                try:
                    response_data = response.json()
                except requests.exceptions.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}")
                    logger.error(f"响应内容: {response.text[:200]}...")
                    if attempt < max_retries - 1:
                        logger.warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

                # 检查响应状态
                if response_data.get("state", {}).get("code") == 0:
                    return response_data.get("traces", [])
                else:
                    logger.error(
                        f"API请求失败: {response_data.get('state', {}).get('message', '未知错误')}")
                    if attempt < max_retries - 1:
                        logger.warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

            except requests.exceptions.ConnectionError as e:
                logger.error(f"连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.warning(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                return []

            except requests.exceptions.Timeout as e:
                logger.error(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.warning(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                return []

            except requests.exceptions.RequestException as e:
                logger.error(f"请求异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.warning(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                return []

        logger.error(f"所有重试都失败了，返回空列表")
        return []

    def check_server_health(self) -> bool:
        """
        检查服务器连接健康状态
        :return: 服务器是否可用
        """
        url = f"{self.wmy_url}:{self.wmy_url_port}/api/health"
        try:
            response = self.session.get(url, timeout=10, verify=False)
            return response.status_code == 200
        except:
            return False

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            query_sql: Dict[str, Any] = {"mmsi": {"$exists": True}}
            if self.vessel_types:
                query_sql["vesselTypeNameCn"] = {"$in": self.vessel_types}

            if self.mgo_db is None:
                logger.error("数据库连接失败")
                return

            

            # 计算10天前的时间戳
            if self.time_days:
                ten_days_ago = datetime.now() - timedelta(days=self.time_days)
                logger.info(f"ten_days_ago: {ten_days_ago}")

                # 构建排除最近10天内的updated_at条件
                query_sql_with_time = dict(query_sql)
                query_sql_with_time["$or"] = [
                    {"perf_calculated_updated_at": {"$lt": ten_days_ago}},
                    {"perf_calculated_updated_at": {"$exists": False}}
                ]
            else:
                query_sql_with_time = query_sql

            vessels = self.mgo_db["hifleet_vessels"].find(
                query_sql_with_time,
                {
                    "mmsi": 1,
                    "draught": 1,
                    "speed": 1,
                    "buildYear": 1,
                    "length": 1,
                    "width": 1,
                    "height": 1,
                    "dwt": 1,
                    '_id': 0
                }
            ).sort("perf_calculated_updated_at", 1)

            total_num = vessels.count()
            num = 0
            logger.info(f"total_num: {total_num}")

            # 请求接口，获取轨迹气象数据和船舶轨迹数据
            for vessel in vessels:
                num += 1
                mmsi = vessel["mmsi"]
                draught = vessel.get("draught")
                design_speed = vessel.get("speed")
                buildYear = vessel.get("buildYear")
                length = vessel.get("length")
                width = vessel.get("width")
                height = vessel.get("height")
                load_weight = vessel.get("dwt")
                if not draught or not design_speed:
                    continue

                start_time = int(datetime.now().timestamp()
                                 * 1000) - self.calc_days * 24 * 3600 * 1000
                end_time = int(datetime.now().timestamp() * 1000)
                trace = self.get_vessel_trace(mmsi, start_time, end_time)

                # 初始化性能数据变量
                current_good_weather_performance = None
                current_bad_weather_performance = None
                performance_analysis = None

                if trace:
                    current_good_weather_performance = self.deal_good_perf_list(
                        trace, draught, design_speed)
                    current_bad_weather_performance = self.deal_bad_perf_list(
                        trace, draught, design_speed)

                    # 性能对比分析
                    performance_analysis = self.analyze_performance_comparison(
                        current_good_weather_performance,
                        current_bad_weather_performance,
                        design_speed
                    )

                    # 更新 mongo 的数据
                    self.mgo_db["vessels_performance_details"].update_one(
                        {"mmsi": mmsi},
                        {"$set": {
                            "current_good_weather_performance": current_good_weather_performance,
                            "current_bad_weather_performance": current_bad_weather_performance,
                            "performance_analysis": performance_analysis,
                            "perf_calculated": 1,
                            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }}, upsert=True)

                    # 入计算油耗队列
                    if current_good_weather_performance:
                        current_good_weather_performance["mmsi"] = mmsi
                        current_good_weather_performance["load_weight"] = load_weight
                        current_good_weather_performance["ship_draft"] = draught
                        current_good_weather_performance["ballast_draft"] = round(
                            current_good_weather_performance["ship_draft"]*0.7, 2)
                        current_good_weather_performance["length"] = length
                        current_good_weather_performance["width"] = width
                        current_good_weather_performance["height"] = height
                        current_good_weather_performance["ship_year"] = buildYear
                        if current_good_weather_performance["ship_year"]:
                            current_good_weather_performance["ship_year"] = int(
                                datetime.now().year) - int(current_good_weather_performance["ship_year"])

                    if current_good_weather_performance:
                        task = {
                            'task_type': "handler_calculate_vessel_performance_ck",
                            'process_data': current_good_weather_performance
                        }
                        self.cache_rds.rpush(
                            "handler_calculate_vessel_performance_ck", json.dumps(task))
                        # logger.info(f"已推送mmsi={mmsi}的船舶进入油耗计算队列")

                        # 更新 perf_calculated_updated_at
                        self.mgo_db["hifleet_vessels"].update_one(
                            {"mmsi": mmsi},
                            {"$set": {"perf_calculated_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}})

                    # 船长视角的性能评估
                    # captain_assessment = assess_vessel_performance_from_captain_perspective(
                    #     vessel, current_good_weather_performance, design_speed
                    # )

                    # 买卖船和租船分析
                    # trading_chartering_analysis = analyze_vessel_for_trading_and_chartering(
                    #     vessel, current_good_weather_performance, design_speed, {}
                    # )

                    # print(
                    #     f"MMSI {mmsi} 好天气 性能数据: {current_good_weather_performance}")
                    # print(
                    #     f"MMSI {mmsi} 坏天气 性能数据: {current_bad_weather_performance}")
                    # print(f"MMSI {mmsi} 性能对比分析: {performance_analysis}")
                    # print(f"MMSI {mmsi} 船长评估: {captain_assessment}")
                    # print(f"MMSI {mmsi} 买卖船租船分析: {trading_chartering_analysis}")
                    logger.info(f"性能计算已完成：mmsi={mmsi}, 已计算{num}/{total_num} 进度：{round((num / total_num) * 100, 2)}%")
                else:
                    logger.warning(f"MMSI {mmsi} 未获取到轨迹数据")

                
                time.sleep(float(self.time_sleep))

        except Exception as e:
            traceback.print_exc()
            logger.error(f"error: {e}")
        finally:
            logger.info("运行结束")
