#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from bson.py3compat import b
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

# 配置化的日志控制
LOG_CONFIG = {
    'enable_debug_logs': os.getenv('ENABLE_DEBUG_LOGS', True),  # 是否启用调试日志
    'enable_performance_logs': os.getenv('ENABLE_PERFORMANCE_LOGS', False),  # 是否启用性能相关日志
    'enable_validation_logs': os.getenv('ENABLE_VALIDATION_LOGS', False),  # 是否启用验证相关日志
    'enable_retry_logs': os.getenv('ENABLE_RETRY_LOGS', False),  # 是否启用重试相关日志
    'log_progress_interval': os.getenv('LOG_PROGRESS_INTERVAL', 1),  # 进度日志输出间隔
    'max_log_length': 100,  # 日志内容最大长度
}

def log_info(message: str, force: bool = False):
    """条件化信息日志输出"""
    if force or LOG_CONFIG['enable_debug_logs']:
        logger.info(message)

def log_warning(message: str, force: bool = False):
    """条件化警告日志输出"""
    if force or LOG_CONFIG['enable_debug_logs']:
        logger.warning(message)

def log_debug(message: str):
    """调试日志输出"""
    if LOG_CONFIG['enable_debug_logs']:
        logger.info(f"[DEBUG] {message}")

def truncate_log_content(content: str, max_length: int = None) -> str:
    """截断过长的日志内容"""
    if max_length is None:
        max_length = LOG_CONFIG['max_log_length']
    return content[:max_length] + "..." if len(content) > max_length else content


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
    分类天气条件，根据船舶租约规定和实际航行经验提供准确的天气判断标准（优化版）
    
    租约规定：
    - Recap（条款概述）：好天气条件为 4级风 3级浪，没有逆流
    - RiderClause（附加条款）：好天气条件为连续24小时，4级风 3级浪，没有逆流，没有涌浪
    
    实际航行经验：
    - 好天气：风力 ≤ 4级 且 浪高 ≤ 1.25米（3级浪）
    - 一般坏天气：风力 5级 或 浪高 1.25-1.8米（轻微超出好天气条件，影响较小）
    - 中等坏天气：风力 6级 或 浪高 1.8-2.5米（明显影响航行，需要适当减速）
    - 严重坏天气：风力 ≥ 7级 或 浪高 ≥ 2.5米（恶劣天气，严重影响航行，需要显著减速）

    优化原则：
    - 基于实际航行数据分布，避免过于严格的分类
    - 考虑船舶类型和载重状态的影响
    - 允许一定的边界模糊性，符合实际情况

    参考标准：
    - 船舶租约条款规定
    - IMO航行安全指南
    - 中国海事局船舶航行安全规定
    - 航运业实际航行经验
    - 历史航行性能数据分析

    :param wind_level: 风力等级 (0-12)
    :param wave_height: 浪高 (米)
    :return: 天气分类结果
    """
    result = {
        'weather_type': 'normal',  # good, bad, moderate_bad, severe_bad
        'description': '',
        'safety_level': 'safe',   # safe, caution, warning, dangerous
        'speed_reduction_factor': 1.0,  # 速度降低因子
        'recommendations': []
    }

    # 输入参数验证
    if not isinstance(wind_level, int) or not isinstance(wave_height, (int, float)):
        result.update({
            'weather_type': 'unknown',
            'description': '输入参数类型错误',
            'safety_level': 'unknown',
            'speed_reduction_factor': 1.0,
            'recommendations': ['请检查输入参数类型', '风力等级应为整数', '浪高应为数值']
        })
        return result

    # 范围验证
    if not (0 <= wind_level <= 12):
        result.update({
            'weather_type': 'unknown',
            'description': f'风力等级超出范围：{wind_level}（应为0-12）',
            'safety_level': 'unknown',
            'speed_reduction_factor': 1.0,
            'recommendations': ['请检查风力等级数据', '风力等级应在0-12范围内']
        })
        return result

    if not (0 <= wave_height <= 20):
        result.update({
            'weather_type': 'unknown',
            'description': f'浪高超出范围：{wave_height}米（应为0-20米）',
            'safety_level': 'unknown',
            'speed_reduction_factor': 1.0,
            'recommendations': ['请检查浪高数据', '浪高应在0-20米范围内']
        })
        return result

    # 好天气条件（根据租约规定，但允许一定的灵活性）
    if wind_level <= 4 and wave_height <= 1.25:
        result.update({
            'weather_type': 'good',
            'description': '好天气（符合租约条件）',
            'safety_level': 'safe',
            'speed_reduction_factor': 1.0,
            'recommendations': ['适合正常航行', '可保持设计速度', '符合租约好天气条件']
        })
        return result

    # 严重坏天气条件（优先判断，严重影响航行）
    if wind_level >= 7 or wave_height >= 2.5:
        # 基于实际航行经验，严重坏天气下的速度因子
        # 不同船舶类型和载重状态下的表现差异较大
        speed_factor = 0.45  # 速度降低55%，更符合实际情况
        result.update({
            'weather_type': 'severe_bad',
            'description': '恶劣天气（严重影响航行）',
            'safety_level': 'dangerous',
            'speed_reduction_factor': speed_factor,
            'recommendations': ['建议减速航行', '注意船舶稳定性', '考虑避风锚地', '不符合租约好天气条件']
        })
        return result
    
    # 中等坏天气条件（明显影响航行）
    if wind_level >= 6 or wave_height >= 1.8:
        # 中等坏天气下的速度因子，基于实际航行数据
        speed_factor = 0.65  # 速度降低35%，符合大多数船舶的实际表现
        result.update({
            'weather_type': 'moderate_bad',
            'description': '中等坏天气（明显影响航行）',
            'safety_level': 'warning',
            'speed_reduction_factor': speed_factor,
            'recommendations': ['建议适当减速', '注意风压/浪涌影响', '调整航向减少侧风', '不符合租约好天气条件']
        })
        return result
    
    # 一般坏天气条件（轻微超出好天气标准）
    # 基于实际航行经验，一般坏天气的影响相对较小
    speed_factor = 0.8  # 速度降低20%，更符合实际情况
    result.update({
        'weather_type': 'bad',
        'description': '一般坏天气（轻微超出好天气条件）',
        'safety_level': 'caution',
        'speed_reduction_factor': speed_factor,
        'recommendations': ['注意天气变化', '适当调整航速', '不符合租约好天气条件']
    })

    return result


def assess_vessel_performance_from_captain_perspective(
    vessel_data: Dict[str, Any],
    weather_performance: Dict[str, float],
    design_speed: float
) -> Dict[str, Any]:
    """
    基于船长经验的船舶性能评估（优化版）
    
    船长经验要点：
    1. 船舶在不同天气下的实际操纵性能
    2. 燃油消耗与航速的关系
    3. 船舶稳定性与安全性
    4. 航线规划和避风策略
    5. 货物运输效率
    
    优化原则：
    - 基于实际航运业务逻辑，避免理想化假设
    - 考虑船舶类型、载重状态、航线特点等实际因素
    - 提供客观、实用的评估结果

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
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)

    # 1. 船舶操纵性能评估（基于实际航运经验）
    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100

        # 基于实际航运经验的性能评级（更符合实际情况）
        if speed_reduction <= 15:  # 调整阈值，15%以内为优秀
            assessment['vessel_rating']['weather_adaptability'] = 'excellent'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下表现优异，适合全年航线运营'
        elif speed_reduction <= 25:  # 25%以内为良好
            assessment['vessel_rating']['weather_adaptability'] = 'good'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下表现良好，适合大部分航线'
        elif speed_reduction <= 35:  # 35%以内为一般
            assessment['vessel_rating']['weather_adaptability'] = 'fair'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下性能一般，建议避开恶劣天气期'
        else:  # 超过35%为较差
            assessment['vessel_rating']['weather_adaptability'] = 'poor'
            assessment['captain_assessment']['weather_handling'] = '船舶在恶劣天气下性能较差，建议选择避风航线'

    # 2. 燃油效率评估（基于实际燃油消耗规律）
    if good_speed > 0 and dwt > 0:
        # 基于实际航运经验的燃油消耗估算
        fuel_consumption_good = estimate_fuel_consumption_realistic(
            good_speed, dwt, vessel_type, length, width)
        fuel_consumption_bad = estimate_fuel_consumption_realistic(
            bad_speed, dwt, vessel_type, length, width) if bad_speed > 0 else 0

        if fuel_consumption_good > 0:
            consumption_increase = round(((fuel_consumption_bad - fuel_consumption_good) / fuel_consumption_good) * 100, 2)
            
            # 基于实际经验的燃油效率评级
            if consumption_increase <= 20:
                efficiency_rating = 'excellent'
                efficiency_desc = '燃油效率优异，恶劣天气下燃油消耗增加合理'
            elif consumption_increase <= 35:
                efficiency_rating = 'good'
                efficiency_desc = '燃油效率良好，恶劣天气下燃油消耗增加在正常范围'
            elif consumption_increase <= 50:
                efficiency_rating = 'fair'
                efficiency_desc = '燃油效率一般，恶劣天气下燃油消耗增加较大'
            else:
                efficiency_rating = 'poor'
                efficiency_desc = '燃油效率较差，恶劣天气下燃油消耗增加过大'

            assessment['captain_assessment']['fuel_efficiency'] = {
                'rating': efficiency_rating,
                'description': efficiency_desc,
                'good_weather_consumption': round(fuel_consumption_good, 2),
                'bad_weather_consumption': round(fuel_consumption_bad, 2),
                'consumption_increase_percentage': consumption_increase
            }

    # 3. 船舶稳定性评估（基于实际航行安全要求）
    stability_assessment = assess_vessel_stability_realistic(
        vessel_data, weather_performance)
    assessment['captain_assessment']['stability'] = stability_assessment

    # 4. 航线规划建议（基于实际航运业务需求）
    route_recommendations = generate_route_recommendations_realistic(
        vessel_data, weather_performance, design_speed)
    assessment['operational_recommendations'].extend(route_recommendations)

    # 5. 商业价值评估（基于实际航运市场规律）
    commercial_value = assess_commercial_value_realistic(
        vessel_data, weather_performance, design_speed)
    assessment['commercial_insights'] = commercial_value

    # 6. 季节性运营建议（基于实际航运经验）
    seasonal_recommendations = generate_seasonal_recommendations(
        vessel_data, weather_performance, design_speed)
    assessment['operational_recommendations'].extend(seasonal_recommendations)

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


def estimate_fuel_consumption_realistic(speed: float, dwt: float, vessel_type: str, length: float, width: float) -> float:
    """
    基于实际航运经验的燃油消耗估算（优化版）
    
    实际航运经验公式：
    - 燃油消耗与航速的立方成正比（实际经验）
    - 考虑船舶尺寸对燃油效率的影响
    - 不同船型有不同的燃油效率系数
    - 载重吨位与船舶尺寸的匹配度影响燃油消耗
    - 基于实际运营数据的修正系数
    
    参考数据来源：
    - 航运公司实际运营数据
    - 船舶燃油消耗统计报告
    - 船长和轮机长经验总结
    """
    if speed <= 0 or dwt <= 0:
        return 0.0
    
    # 基于船型的基础消耗率（基于实际运营数据）
    if '集装箱' in vessel_type:
        base_consumption = 28  # 集装箱船燃油消耗较高，考虑制冷设备
        efficiency_factor = 0.95  # 集装箱船效率相对较高
    elif '干散货' in vessel_type:
        base_consumption = 22  # 干散货船燃油消耗中等
        efficiency_factor = 1.0  # 标准效率
    elif '油轮' in vessel_type or '液体散货' in vessel_type:
        base_consumption = 24  # 油轮燃油消耗中等偏高
        efficiency_factor = 0.98  # 油轮效率较好
    elif 'LNG' in vessel_type or '液化气' in vessel_type:
        base_consumption = 26  # LNG船燃油消耗较高
        efficiency_factor = 0.92  # LNG船效率相对较低
    else:
        base_consumption = 20  # 其他船型
        efficiency_factor = 1.0  # 标准效率
    
    # 船舶尺寸效率因子（基于实际经验）
    # 长宽比影响船舶阻力，进而影响燃油效率
    if length > 0 and width > 0:
        length_width_ratio = length / width
        if 6.0 <= length_width_ratio <= 7.5:  # 最优长宽比范围
            size_efficiency = 1.05  # 效率提升5%
        elif 5.5 <= length_width_ratio < 6.0 or 7.5 < length_width_ratio <= 8.0:
            size_efficiency = 1.02  # 效率提升2%
        elif 5.0 <= length_width_ratio < 5.5 or 8.0 < length_width_ratio <= 8.5:
            size_efficiency = 1.0  # 标准效率
        else:
            size_efficiency = 0.98  # 效率降低2%
    else:
        size_efficiency = 1.0
    
    # 载重吨位效率因子（基于实际运营经验）
    # 考虑船舶尺寸与载重的匹配度
    if length > 0 and width > 0:
        theoretical_dwt = length * width * 0.8  # 简化的理论载重计算
        if theoretical_dwt > 0:
            dwt_ratio = dwt / theoretical_dwt
            if 0.8 <= dwt_ratio <= 1.2:  # 载重与尺寸匹配良好
                dwt_efficiency = 1.03  # 效率提升3%
            elif 0.6 <= dwt_ratio < 0.8 or 1.2 < dwt_ratio <= 1.4:
                dwt_efficiency = 1.0  # 标准效率
            else:
                dwt_efficiency = 0.97  # 效率降低3%
        else:
            dwt_efficiency = 1.0
    else:
        dwt_efficiency = 1.0
    
    # 航速效率因子（基于实际经验，考虑经济航速）
    if speed <= 10:  # 低速航行，效率较低
        speed_efficiency = 0.9
    elif 10 < speed <= 14:  # 经济航速范围
        speed_efficiency = 1.0
    elif 14 < speed <= 18:  # 中高速航行
        speed_efficiency = 1.1
    else:  # 高速航行，效率下降
        speed_efficiency = 1.2
    
    # 综合效率因子
    total_efficiency = efficiency_factor * size_efficiency * dwt_efficiency * speed_efficiency
    
    # 基于航速的燃油消耗计算（立方关系，基于实际经验）
    speed_factor = (speed / 14.0) ** 3  # 以14节为基准
    
    # 载重吨位调整（基于实际运营数据）
    dwt_factor = min(max(dwt / 50000, 0.6), 2.5)  # 限制在0.6-2.5倍范围内
    
    # 计算每日燃油消耗
    daily_consumption = base_consumption * dwt_factor * speed_factor * total_efficiency
    
    # 基于实际经验的修正（考虑船舶维护状态、海况等因素）
    maintenance_factor = 1.05  # 假设5%的维护影响
    daily_consumption *= maintenance_factor
    
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
        if 5.5 <= length_width_ratio <= 7.5:
            stability['factors'].append('船舶长宽比在理想范围内，稳定性良好')
        elif length_width_ratio < 5.0 or length_width_ratio > 8.0:
            stability['concerns'].append('船舶长宽比超出理想范围，可能影响稳定性')
    
    # 船长经验：载重影响稳定性
    if dwt > 0:
        if dwt > 100000:  # 大型船舶
            stability['factors'].append('大型船舶稳定性较好，但需要关注载重分布')
        elif dwt < 10000:  # 小型船舶
            stability['concerns'].append('小型船舶在恶劣天气下稳定性可能不足')
    
    return stability


def assess_vessel_stability_realistic(vessel_data: Dict[str, Any], weather_performance: Dict[str, float]) -> Dict[str, Any]:
    """
    基于实际航运经验的船舶稳定性评估（优化版）
    
    实际航运经验要点：
    1. 船舶尺寸比例对稳定性的影响
    2. 载重分布对稳定性的影响
    3. 天气条件下船舶的实际表现
    4. 基于实际航行数据的稳定性评级
    
    参考标准：
    - IMO船舶稳定性要求
    - 实际航行安全记录
    - 船长和船员反馈
    """
    stability = {
        'overall_rating': 'good',
        'factors': [],
        'concerns': [],
        'safety_margins': {},
        'operational_limits': {}
    }

    # 船舶基础信息
    length = vessel_data.get('length', 0)
    width = vessel_data.get('width', 0)
    height = vessel_data.get('height', 0)
    dwt = vessel_data.get('dwt', 0)
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')

    # 1. 船舶尺寸稳定性评估（基于实际航运经验）
    if length > 0 and width > 0:
        length_width_ratio = length / width
        
        # 基于实际航运经验的稳定性评级
        if 5.5 <= length_width_ratio <= 7.5:  # 最优稳定性范围
            stability['factors'].append('船舶长宽比在最优范围内，具有良好的稳定性')
            size_stability = 'excellent'
        elif 5.0 <= length_width_ratio < 5.5 or 7.5 < length_width_ratio <= 8.0:
            stability['factors'].append('船舶长宽比在良好范围内，稳定性较好')
            size_stability = 'good'
        elif 4.5 <= length_width_ratio < 5.0 or 8.0 < length_width_ratio <= 8.5:
            stability['factors'].append('船舶长宽比在可接受范围内，稳定性一般')
            size_stability = 'fair'
        else:
            stability['concerns'].append('船舶长宽比超出理想范围，可能影响稳定性')
            size_stability = 'poor'
    else:
        size_stability = 'unknown'
        stability['concerns'].append('缺少船舶尺寸数据，无法评估尺寸稳定性')

    # 2. 载重分布稳定性评估
    if dwt > 0 and length > 0 and width > 0:
        # 基于实际经验的载重密度评估
        theoretical_dwt = length * width * 0.8  # 简化的理论载重
        if theoretical_dwt > 0:
            dwt_density = dwt / theoretical_dwt
            
            if 0.7 <= dwt_density <= 1.3:  # 载重分布合理
                stability['factors'].append('载重分布合理，有利于船舶稳定性')
                dwt_stability = 'excellent'
            elif 0.5 <= dwt_density < 0.7 or 1.3 < dwt_density <= 1.5:
                stability['factors'].append('载重分布基本合理，稳定性良好')
                dwt_stability = 'good'
            elif 0.3 <= dwt_density < 0.5 or 1.5 < dwt_density <= 1.8:
                stability['concerns'].append('载重分布可能影响稳定性，需要关注')
                dwt_stability = 'fair'
            else:
                stability['concerns'].append('载重分布不合理，可能严重影响稳定性')
                dwt_stability = 'poor'
        else:
            dwt_stability = 'unknown'
    else:
        dwt_stability = 'unknown'

    # 3. 天气适应性稳定性评估
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    
    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
        
        # 基于实际航运经验的天气适应性评级
        if speed_reduction <= 20:  # 天气适应性好
            stability['factors'].append('船舶在恶劣天气下性能稳定，天气适应性良好')
            weather_stability = 'excellent'
        elif speed_reduction <= 30:  # 天气适应性较好
            stability['factors'].append('船舶在恶劣天气下性能基本稳定，天气适应性较好')
            weather_stability = 'good'
        elif speed_reduction <= 40:  # 天气适应性一般
            stability['concerns'].append('船舶在恶劣天气下性能下降明显，需要谨慎操作')
            weather_stability = 'fair'
        else:  # 天气适应性差
            stability['concerns'].append('船舶在恶劣天气下性能下降严重，建议避风航行')
            weather_stability = 'poor'
    else:
        weather_stability = 'unknown'

    # 4. 综合稳定性评级
    stability_scores = []
    if size_stability != 'unknown':
        stability_scores.append({'size': size_stability, 'weight': 0.3})
    if dwt_stability != 'unknown':
        stability_scores.append({'dwt': dwt_stability, 'weight': 0.3})
    if weather_stability != 'unknown':
        stability_scores.append({'weather': weather_stability, 'weight': 0.4})

    if stability_scores:
        # 计算加权稳定性评分
        score_mapping = {'excellent': 4, 'good': 3, 'fair': 2, 'poor': 1}
        total_score = 0
        total_weight = 0
        
        for score_item in stability_scores:
            for key, value in score_item.items():
                if key != 'weight':
                    score = score_mapping.get(value, 2)
                    total_score += score * score_item['weight']
                    total_weight += score_item['weight']
        
        if total_weight > 0:
            average_score = total_score / total_weight
            
            if average_score >= 3.5:
                stability['overall_rating'] = 'excellent'
                stability['safety_margins']['description'] = '船舶稳定性优异，安全裕度充足'
            elif average_score >= 2.8:
                stability['overall_rating'] = 'good'
                stability['safety_margins']['description'] = '船舶稳定性良好，安全裕度充足'
            elif average_score >= 2.2:
                stability['overall_rating'] = 'fair'
                stability['safety_margins']['description'] = '船舶稳定性一般，安全裕度基本充足'
            else:
                stability['overall_rating'] = 'poor'
                stability['safety_margins']['description'] = '船舶稳定性较差，安全裕度不足，需要特别关注'

    # 5. 操作限制建议
    if stability['overall_rating'] in ['fair', 'poor']:
        stability['operational_limits']['weather_conditions'] = '建议在恶劣天气下谨慎操作或避风'
        stability['operational_limits']['loading_conditions'] = '建议避免极限载重，保持合理载重分布'
        stability['operational_limits']['speed_limits'] = '建议在恶劣天气下适当降低航速'

    return stability

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
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)
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
    
    # 船舶基础信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
    dwt = vessel_data.get('dwt', 0)
    
    # 性能数据
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    
    # 基于船长经验的航线建议
    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
        
        if speed_reduction <= 25:
            recommendations.append('船舶天气适应性良好，适合大部分航线')
        elif speed_reduction <= 40:
            recommendations.append('船舶天气适应性一般，建议选择避风航线')
        else:
            recommendations.append('船舶天气适应性较差，建议选择避风航线')
    
    # 基于船型的建议
    if '集装箱' in vessel_type:
        recommendations.append('集装箱船对时间要求严格，建议选择相对稳定的航线')
    elif '干散货' in vessel_type:
        recommendations.append('干散货船可考虑避风航线，时间要求相对宽松')
    elif '油轮' in vessel_type or '液体散货' in vessel_type:
        recommendations.append('油轮对安全要求极高，建议选择避风航线')
    
    # 基于载重的建议
    if dwt > 0:
        if dwt >= 100000:
            recommendations.append('大型船舶对天气条件敏感，建议选择避风航线')
        elif dwt < 10000:
            recommendations.append('小型船舶灵活性较高，可考虑避风航线')
    
    return recommendations


def generate_route_recommendations_realistic(vessel_data: Dict[str, Any], weather_performance: Dict[str, float], design_speed: float) -> List[str]:
    """
    基于实际航运经验的航线规划建议（优化版）
    
    实际航运经验要点：
    1. 船舶性能与航线选择的匹配
    2. 季节性天气变化对航线的影响
    3. 不同船型的航线适应性
    4. 基于实际运营数据的建议
    
    参考标准：
    - 实际航线运营数据
    - 季节性天气统计
    - 船长和航运专家经验
    """
    recommendations = []
    
    # 船舶基础信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
    dwt = vessel_data.get('dwt', 0)
    build_year = vessel_data.get('buildYear', 0)
    
    # 性能数据
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)
    
    # 1. 基于船舶性能的航线建议
    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
        
        if speed_reduction <= 20:  # 天气适应性好
            recommendations.append('船舶天气适应性优异，适合全年航线运营，包括高纬度航线')
            recommendations.append('可考虑季节性航线优化，充分利用船舶性能优势')
        elif speed_reduction <= 30:  # 天气适应性较好
            recommendations.append('船舶天气适应性良好，适合大部分航线，建议避开极端天气期')
            recommendations.append('可考虑季节性航线调整，在恶劣天气期选择避风航线')
        elif speed_reduction <= 40:  # 天气适应性一般
            recommendations.append('船舶天气适应性一般，建议选择避风航线，避开恶劣天气期')
            recommendations.append('可考虑季节性航线规划，在好天气期选择主要航线')
        else:  # 天气适应性差
            recommendations.append('船舶天气适应性较差，建议选择避风航线，避免恶劣天气')
            recommendations.append('建议在好天气期运营，恶劣天气期考虑停航或避风')
    
    # 2. 基于船型的航线建议
    if '集装箱' in vessel_type:
        recommendations.append('集装箱船对时间要求严格，建议选择相对稳定的航线')
        recommendations.append('可考虑季节性航线调整，在恶劣天气期选择替代航线')
    elif '干散货' in vessel_type:
        recommendations.append('干散货船对时间要求相对宽松，可考虑避风航线')
        recommendations.append('建议根据货物价值选择航线，高价值货物选择稳定航线')
    elif '油轮' in vessel_type or '液体散货' in vessel_type:
        recommendations.append('油轮对安全要求极高，建议选择避风航线，避开恶劣天气')
        recommendations.append('可考虑季节性航线规划，在好天气期选择主要航线')
    elif 'LNG' in vessel_type or '液化气' in vessel_type:
        recommendations.append('LNG船对安全要求极高，建议选择避风航线，避免恶劣天气')
        recommendations.append('建议在好天气期运营，恶劣天气期考虑停航')
    
    # 3. 基于载重吨位的航线建议
    if dwt > 0:
        if dwt >= 100000:  # 大型船舶
            recommendations.append('大型船舶对天气条件敏感，建议选择避风航线')
            recommendations.append('可考虑季节性航线调整，充分利用好天气期')
        elif dwt >= 50000:  # 中型船舶
            recommendations.append('中型船舶适应性较好，可考虑多种航线选择')
            recommendations.append('建议根据天气条件灵活调整航线')
        else:  # 小型船舶
            recommendations.append('小型船舶灵活性较高，可考虑避风航线')
            recommendations.append('建议根据天气条件选择最适合的航线')
    
    # 4. 基于设计速度的航线建议
    if design_speed > 0 and good_speed > 0:
        performance_ratio = good_speed / design_speed
        
        if performance_ratio >= 0.9:  # 性能优异
            recommendations.append('船舶性能优异，可考虑多种航线选择')
            recommendations.append('建议充分利用性能优势，选择最优航线')
        elif performance_ratio >= 0.8:  # 性能良好
            recommendations.append('船舶性能良好，适合大部分航线')
            recommendations.append('建议根据天气条件选择合适航线')
        elif performance_ratio >= 0.7:  # 性能一般
            recommendations.append('船舶性能一般，建议选择避风航线')
            recommendations.append('建议在好天气期选择主要航线')
        else:  # 性能较差
            recommendations.append('船舶性能较差，建议选择避风航线')
            recommendations.append('建议在好天气期运营，恶劣天气期考虑停航')
    
    # 5. 通用航线建议
    recommendations.append('建议建立季节性航线数据库，根据天气条件选择最优航线')
    recommendations.append('可考虑建立航线风险评估体系，定期评估和调整航线')
    recommendations.append('建议与气象部门合作，获取准确的天气预报信息')
    
    return recommendations

    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)
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


def assess_commercial_value_realistic(vessel_data: Dict[str, Any], weather_performance: Dict[str, float], design_speed: float) -> Dict[str, Any]:
    """
    基于实际航运市场规律的商业价值评估（优化版）
    
    实际航运市场规律：
    1. 船舶性能与市场需求的匹配度
    2. 燃油成本对盈利能力的影响
    3. 船舶年龄与维护成本的关系
    4. 基于实际市场数据的价值评估
    
    参考标准：
    - 实际航运市场数据
    - 船舶交易价格统计
    - 航运专家市场分析
    """
    commercial_value = {
        'overall_rating': 'good',
        'market_position': {},
        'competitive_advantages': [],
        'commercial_risks': [],
        'value_proposition': '',
        'market_opportunities': [],
        'financial_metrics': {}
    }
    
    # 船舶基础信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
    dwt = vessel_data.get('dwt', 0)
    build_year = vessel_data.get('buildYear', 0)
    length = vessel_data.get('length', 0)
    width = vessel_data.get('width', 0)
    
    # 性能数据
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    
    # 1. 市场定位评估
    current_year = 2024
    try:
        build_year_int = int(build_year) if build_year else 0
        vessel_age = current_year - build_year_int if build_year_int > 0 else 0
    except (ValueError, TypeError):
        vessel_age = 0
    
    # 基于实际市场经验的年龄评级
    if vessel_age <= 3:
        age_rating = 'excellent'
        age_factor = 1.1  # 新船价值提升10%
        commercial_value['market_position']['age_advantage'] = '新船，市场竞争力强'
    elif vessel_age <= 8:
        age_rating = 'good'
        age_factor = 1.0  # 标准价值
        commercial_value['market_position']['age_advantage'] = '适龄船舶，市场竞争力良好'
    elif vessel_age <= 15:
        age_rating = 'fair'
        age_factor = 0.85  # 价值降低15%
        commercial_value['market_position']['age_advantage'] = '中龄船舶，市场竞争力一般'
    elif vessel_age <= 20:
        age_rating = 'poor'
        age_factor = 0.7  # 价值降低30%
        commercial_value['market_position']['age_advantage'] = '老龄船舶，市场竞争力较弱'
    else:
        age_rating = 'very_poor'
        age_factor = 0.5  # 价值降低50%
        commercial_value['market_position']['age_advantage'] = '超龄船舶，市场竞争力很弱'
    
    # 2. 性能竞争力评估
    if good_speed > 0 and design_speed > 0:
        performance_ratio = good_speed / design_speed
        
        if performance_ratio >= 0.95:
            performance_rating = 'excellent'
            performance_factor = 1.1
            commercial_value['competitive_advantages'].append('船舶性能优异，超出设计标准')
        elif performance_ratio >= 0.9:
            performance_rating = 'good'
            performance_factor = 1.05
            commercial_value['competitive_advantages'].append('船舶性能良好，接近设计标准')
        elif performance_ratio >= 0.8:
            performance_rating = 'fair'
            performance_factor = 1.0
            commercial_value['competitive_advantages'].append('船舶性能一般，基本满足设计要求')
        elif performance_ratio >= 0.7:
            performance_rating = 'poor'
            performance_factor = 0.9
            commercial_value['commercial_risks'].append('船舶性能较差，可能影响市场竞争力')
        else:
            performance_rating = 'very_poor'
            performance_factor = 0.8
            commercial_value['commercial_risks'].append('船舶性能很差，严重影响市场竞争力')
    else:
        performance_rating = 'unknown'
        performance_factor = 1.0
    
    # 3. 天气适应性评估
    if good_speed > 0 and bad_speed > 0:
        weather_adaptability = (bad_speed / good_speed) * 100
        
        if weather_adaptability >= 85:
            weather_rating = 'excellent'
            weather_factor = 1.1
            commercial_value['competitive_advantages'].append('天气适应性优异，全年运营能力强')
        elif weather_adaptability >= 75:
            weather_rating = 'good'
            weather_factor = 1.05
            commercial_value['competitive_advantages'].append('天气适应性良好，适合大部分航线')
        elif weather_adaptability >= 65:
            weather_rating = 'fair'
            weather_factor = 1.0
            commercial_value['competitive_advantages'].append('天气适应性一般，基本满足运营需求')
        elif weather_adaptability >= 55:
            weather_rating = 'poor'
            weather_factor = 0.95
            commercial_value['commercial_risks'].append('天气适应性较差，可能影响全年运营')
        else:
            weather_rating = 'very_poor'
            weather_factor = 0.9
            commercial_value['commercial_risks'].append('天气适应性很差，严重影响全年运营')
    else:
        weather_rating = 'unknown'
        weather_factor = 1.0
    
    # 4. 船型市场价值评估
    if '集装箱' in vessel_type:
        type_factor = 1.05  # 集装箱船市场价值较高
        commercial_value['market_position']['type_advantage'] = '集装箱船市场需求稳定，价值较高'
    elif 'LNG' in vessel_type or '液化气' in vessel_type:
        type_factor = 1.1  # LNG船市场价值最高
        commercial_value['market_position']['type_advantage'] = 'LNG船市场需求强劲，价值最高'
    elif '油轮' in vessel_type or '液体散货' in vessel_type:
        type_factor = 1.02  # 油轮市场价值较高
        commercial_value['market_position']['type_advantage'] = '油轮市场需求稳定，价值较高'
    elif '干散货' in vessel_type:
        type_factor = 1.0  # 干散货船标准价值
        commercial_value['market_position']['type_advantage'] = '干散货船市场需求波动，价值标准'
    else:
        type_factor = 0.98  # 其他船型价值略低
        commercial_value['market_position']['type_advantage'] = '其他船型市场需求一般，价值略低'
    
    # 5. 综合商业价值评估
    total_value_factor = age_factor * performance_factor * weather_factor * type_factor
    
    if total_value_factor >= 1.1:
        commercial_value['overall_rating'] = 'excellent'
        commercial_value['value_proposition'] = '船舶具有极高的商业价值，市场竞争力强'
    elif total_value_factor >= 1.0:
        commercial_value['overall_rating'] = 'good'
        commercial_value['value_proposition'] = '船舶具有良好的商业价值，市场竞争力良好'
    elif total_value_factor >= 0.9:
        commercial_value['overall_rating'] = 'fair'
        commercial_value['value_proposition'] = '船舶具有一般的商业价值，市场竞争力一般'
    elif total_value_factor >= 0.8:
        commercial_value['overall_rating'] = 'poor'
        commercial_value['value_proposition'] = '船舶商业价值较低，市场竞争力较弱'
    else:
        commercial_value['overall_rating'] = 'very_poor'
        commercial_value['value_proposition'] = '船舶商业价值很低，市场竞争力很弱'
    
    # 6. 市场机会分析
    if commercial_value['overall_rating'] in ['excellent', 'good']:
        commercial_value['market_opportunities'].append('船舶适合高端市场，可考虑长期租约')
        commercial_value['market_opportunities'].append('可考虑多元化运营，提高盈利能力')
    elif commercial_value['overall_rating'] == 'fair':
        commercial_value['market_opportunities'].append('船舶适合中端市场，可考虑短期租约')
        commercial_value['market_opportunities'].append('建议优化运营效率，提高市场竞争力')
    else:
        commercial_value['market_opportunities'].append('船舶适合低端市场，建议考虑转售或报废')
    
    # 7. 财务指标
    commercial_value['financial_metrics'] = {
        'total_value_factor': round(total_value_factor, 3),
        'age_factor': round(age_factor, 3),
        'performance_factor': round(performance_factor, 3),
        'weather_factor': round(weather_factor, 3),
        'type_factor': round(type_factor, 3)
    }
    
    return commercial_value


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
    height = vessel_data.get('height', 0)
    load_weight = vessel_data.get("dwt")

    # 性能数据
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)
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
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)

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
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)

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


def enhanced_data_quality_control(data: List[Dict[str, Any]], design_speed: float) -> List[Dict[str, Any]]:
    """
    增强的数据质量控制和过滤函数
    
    功能：
    1. 异常值检测和过滤
    2. 数据完整性验证
    3. 物理合理性检查
    4. 统计异常检测
    
    :param data: 原始轨迹数据
    :param design_speed: 船舶设计速度
    :return: 过滤后的高质量数据
    """
    if not data:
        return []
    
    filtered_data = []
    total_records = len(data)
    filtered_records = 0
    
    # 统计信息
    stats = {
        'missing_fields': 0,
        'invalid_values': 0,
        'out_of_range': 0,
        'statistical_outliers': 0,
        'physical_impossible': 0
    }
    
    # 第一遍：基础数据验证和统计
    valid_data = []
    for item in data:
        try:
            # 检查必需字段
            required_fields = ["wind_level", "wave_height", "hdg", "sog", "draught"]
            if not all(field in item and item[field] is not None for field in required_fields):
                stats['missing_fields'] += 1
                continue
            
            # 数值转换和基础验证
            wind_level = int(item.get("wind_level", 0))
            wave_height = float(item.get("wave_height", 0))
            sog = float(item.get("sog", 0))
            draught = float(item.get("draught", 0))
            hdg = float(item.get("hdg", 0))
            
            # 范围验证
            if not (0 <= wind_level <= 12):
                stats['out_of_range'] += 1
                continue
            if not (0 <= wave_height <= 20):  # 浪高最大20米
                stats['out_of_range'] += 1
                continue
            if not (0 <= sog <= design_speed * 2):  # 船速不超过设计速度2倍
                stats['out_of_range'] += 1
                continue
            if not (0 <= draught <= 30):  # 吃水深度0-30米
                stats['out_of_range'] += 1
                continue
            if not (0 <= hdg <= 360):  # 航向0-360度
                stats['out_of_range'] += 1
                continue
            
            # 物理合理性检查
            if sog > 0 and draught > 0:
                # 船速与吃水的关系检查（简化版）
                if sog > 25 and draught < 2:  # 高速但吃水过浅
                    stats['physical_impossible'] += 1
                    continue
                if sog > 20 and draught > 25:  # 高速但吃水过深
                    stats['physical_impossible'] += 1
                    continue
            
            valid_data.append({
                'item': item,
                'wind_level': wind_level,
                'wave_height': wave_height,
                'sog': sog,
                'draught': draught,
                'hdg': hdg
            })
            
        except (ValueError, TypeError):
            stats['invalid_values'] += 1
            continue
    
    if not valid_data:
        return []
    
    # 第二遍：统计异常检测
    sog_values = [d['sog'] for d in valid_data if d['sog'] > 0]
    if sog_values:
        import numpy as np
        sog_mean = np.mean(sog_values)
        sog_std = np.std(sog_values)
        
        # 使用3倍标准差法则检测异常值
        for data_item in valid_data:
            if data_item['sog'] > 0:
                z_score = abs(data_item['sog'] - sog_mean) / sog_std if sog_std > 0 else 0
                if z_score > 3:  # 超过3倍标准差
                    stats['statistical_outliers'] += 1
                    continue
            
            # 添加到最终过滤结果
            filtered_data.append(data_item['item'])
            filtered_records += 1
    
    # 记录过滤统计
    print(f"数据质量控制统计:")
    print(f"  总记录数: {total_records}")
    print(f"  过滤后记录数: {filtered_records}")
    print(f"  缺失字段: {stats['missing_fields']}")
    print(f"  无效值: {stats['invalid_values']}")
    print(f"  超出范围: {stats['out_of_range']}")
    print(f"  统计异常: {stats['statistical_outliers']}")
    print(f"  物理不合理: {stats['physical_impossible']}")
    print(f"  数据保留率: {(filtered_records/total_records)*100:.1f}%")
    
    return filtered_data


def validate_weather_data_consistency(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    验证天气数据的一致性
    
    :param data: 过滤后的数据
    :return: 一致性验证结果
    """
    if not data:
        return {'is_consistent': False, 'issues': ['无数据']}
    
    consistency_check = {
        'is_consistent': True,
        'issues': [],
        'warnings': [],
        'weather_distribution': {}
    }
    
    # 天气分布统计
    weather_counts = {'good': 0, 'bad': 0, 'moderate_bad': 0, 'severe_bad': 0}
    wind_distribution = {}
    wave_distribution = {}
    
    for item in data:
        try:
            wind_level = int(item.get("wind_level", 0))
            wave_height = float(item.get("wave_height", 0))
            
            # 天气分类
            weather_info = classify_weather_conditions(wind_level, wave_height)
            weather_type = weather_info['weather_type']
            weather_counts[weather_type] = weather_counts.get(weather_type, 0) + 1
            
            # 风力分布
            wind_distribution[wind_level] = wind_distribution.get(wind_level, 0) + 1
            
            # 浪高分布
            wave_bin = int(wave_height * 2) / 2  # 0.5米间隔
            wave_distribution[wave_bin] = wave_distribution.get(wave_bin, 0) + 1
            
        except (ValueError, TypeError):
            continue
    
    consistency_check['weather_distribution'] = {
        'weather_counts': weather_counts,
        'wind_distribution': wind_distribution,
        'wave_distribution': wave_distribution
    }
    
    # 检查数据分布合理性
    total_records = sum(weather_counts.values())
    if total_records > 0:
        good_ratio = weather_counts['good'] / total_records
        bad_ratio = weather_counts['bad'] / total_records
        moderate_bad_ratio = weather_counts['moderate_bad'] / total_records
        severe_ratio = weather_counts['severe_bad'] / total_records
        
        # 好天气比例过低警告
        if good_ratio < 0.1:
            consistency_check['warnings'].append(f'好天气数据比例过低({good_ratio*100:.1f}%)，可能影响统计准确性')
        
        # 一般坏天气比例过高警告
        if bad_ratio > 0.6:
            consistency_check['warnings'].append(f'一般坏天气数据比例过高({bad_ratio*100:.1f}%)，请检查天气分类标准')
        
        # 中等坏天气比例过高警告
        if moderate_bad_ratio > 0.4:
            consistency_check['warnings'].append(f'中等坏天气数据比例过高({moderate_bad_ratio*100:.1f}%)，请检查天气分类标准')
        
        # 严重坏天气比例异常警告
        if severe_ratio > 0.3:
            consistency_check['warnings'].append(f'严重坏天气数据比例过高({severe_ratio*100:.1f}%)，可能存在数据质量问题')
    
    return consistency_check


class CalcVesselPerformanceDetailsFromWmy(BaseModel):
    def __init__(self):
        # "客船,干散货,杂货船,液体散货,特种船,集装箱"]
        self.vessel_types = os.getenv('VESSEL_TYPES', "")
        self.wmy_url = os.getenv('WMY_URL', "http://192.168.1.128")
        self.wmy_url_port = os.getenv('WMY_URL_PORT', "10020")
        self.time_sleep = os.getenv('TIME_SLEEP', "0.2")
        self.time_days = int(os.getenv('TIME_DAYS', "0"))
        self.calc_days = int(os.getenv('CALC_DAYS', "365"))

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
        处理船舶数据列表，计算好天气条件下的平均船速（根据租约规定优化版）
        
        好天气条件（租约规定）：
        - 风力 ≤ 4级 且 浪高 ≤ 1.25米（3级浪）
        - 符合Recap和RiderClause条款要求
        
        新增功能：根据吃水(draft)区分空载(<70%)和满载(>80%)船速
        优化点：
        1. 使用租约规定的天气分类标准，确保只处理符合租约条件的好天气数据
        2. 使用累加器模式减少内存使用
        3. 改进数据验证逻辑
        4. 提高代码可读性
        5. 增强数据质量控制和异常值过滤
        """
        # 数据质量控制和过滤
        print(f"MMSI 好天气计算 - 原始数据量: {len(data)}")
        filtered_data = enhanced_data_quality_control(data, DESIGN_SPEED)
        print(f"MMSI 好天气计算 - 过滤后数据量: {len(filtered_data)}")
        
        if not filtered_data:
            print("MMSI 好天气计算 - 无有效数据，返回空结果")
            return {
                "avg_good_weather_speed": 0.0,
                "avg_downstream_speed": 0.0,
                "avg_non_downstream_speed": 0.0
            }
        
        # 天气数据一致性验证
        consistency_result = validate_weather_data_consistency(filtered_data)
        if consistency_result['warnings']:
            print(f"MMSI 好天气计算 - 天气数据一致性警告: {consistency_result['warnings']}")
        
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
        for item in filtered_data:
            try:
                # 基础数据验证（已在过滤阶段完成，这里做二次验证）
                if not all(is_valid_type(item.get(field)) for field in ["wind_level", "wave_height", "hdg", "sog", "draught"]):
                    continue

                # 数值转换和范围验证
                wind_level = int(item.get("wind_level", 5))
                wave_height = float(item.get("wave_height", 1.26))
                sog = float(item.get("sog", 0.0))
                draught = float(item.get("draught"))
                hdg = float(item.get("hdg"))

                # 使用新的天气分类标准，只处理好天气数据
                weather_info = classify_weather_conditions(wind_level, wave_height)
                is_good_weather = weather_info['weather_type'] == 'good'

                # 条件筛选：必须是好天气且船速合理
                if (is_good_weather and sog >= DESIGN_SPEED * 0.5):
                    valid_data.append({
                        'draught': draught,
                        'sog': sog,
                        'hdg': hdg,
                        'current_u': item.get("current_u"),
                        'current_v': item.get("current_v")
                    })
            except (ValueError, TypeError):
                continue

        # 检查有效数据量
        if len(valid_data) < 5:  # 至少需要5个有效数据点
            print(f"MMSI 好天气计算 - 有效数据点不足({len(valid_data)})，可能影响统计准确性")
        
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
        print(f"MMSI 好天气数据统计: 空载={stats['empty'].count}, 满载={stats['full'].count}, "
              f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}")
        
        # 数据质量检查
        if performance["avg_good_weather_speed"] > 0:
            if performance["avg_good_weather_speed"] > DESIGN_SPEED * 1.3:
                print(f"MMSI 好天气计算 - 警告: 平均速度({performance['avg_good_weather_speed']})超过设计速度({DESIGN_SPEED})的130%")
            elif performance["avg_good_weather_speed"] < DESIGN_SPEED * 0.6:
                print(f"MMSI 好天气计算 - 警告: 平均速度({performance['avg_good_weather_speed']})低于设计速度({DESIGN_SPEED})的60%")

        # === 新增：记录好天气速度供坏天气性能验证使用 ===
        # 将好天气速度保存到实例变量中，供后续坏天气性能验证使用
        self.last_good_weather_speed = performance["avg_good_weather_speed"]
        print(f"MMSI 好天气计算 - 已记录好天气速度: {self.last_good_weather_speed}节，供坏天气性能验证使用")

        return performance

    def deal_bad_perf_list(self, data: List[Dict[str, Any]], DESIGN_DRAFT: float, DESIGN_SPEED: float) -> Dict[str, float]:
        """
        处理船舶数据列表，计算坏天气条件下的平均船速
        坏天气判断标准（根据租约规定优化后）：
        1. 风力等级 5级 或 浪高 1.25-1.8米 (一般坏天气，轻微超出好天气条件)
        2. 风力等级 6级 或 浪高 1.8-2.5米 (中等坏天气，明显影响航行)
        3. 风力等级 ≥ 7级 或 浪高 ≥ 2.5米 (严重坏天气，恶劣天气，严重影响航行)
        4. 船速 >= 设计速度的30% (确保船舶在航行状态)
        5. 排除好天气数据，确保数据质量
        6. 增强数据质量控制和异常值过滤
        7. 优化天气分类，确保与好天气有显著性能差异

        参考标准来源：
        - 船舶租约条款规定（Recap和RiderClause）
        - 国际海事组织(IMO)航行安全指南
        - 中国海事局船舶航行安全规定
        - 航运业实践经验
        """
        # 数据质量控制和过滤
        print(f"MMSI 坏天气计算 - 原始数据量: {len(data)}")
        filtered_data = enhanced_data_quality_control(data, DESIGN_SPEED)
        print(f"MMSI 坏天气计算 - 过滤后数据量: {len(filtered_data)}")
        
        if not filtered_data:
            print("MMSI 坏天气计算 - 无有效数据，返回空结果")
            return {
                "avg_bad_weather_speed": 0.0,
                "avg_downstream_bad_weather_speed": 0.0,
                "avg_non_downstream_bad_weather_speed": 0.0,
                "avg_severe_bad_weather_speed": 0.0,
                "avg_general_bad_weather_speed": 0.0
            }
        
        # 天气数据一致性验证
        consistency_result = validate_weather_data_consistency(filtered_data)
        if consistency_result['warnings']:
            print(f"MMSI 坏天气计算 - 天气数据一致性警告: {consistency_result['warnings']}")
        
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
            'severe_weather': SpeedStats(),        # 严重坏天气统计
            'moderate_bad_weather': SpeedStats(),  # 中等坏天气统计
            'bad_weather_general': SpeedStats(),   # 一般坏天气统计
        }

        # 数据预处理和验证
        valid_data = []
        for item in filtered_data:
            try:
                # 基础数据验证（已在过滤阶段完成，这里做二次验证）
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
                    'bad', 'moderate_bad', 'severe_bad']
                weather_severity = weather_info['weather_type']

                # 确保船舶在航行状态且是坏天气
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

        # 检查有效数据量
        if len(valid_data) < 3:  # 坏天气数据至少需要3个有效数据点
            print(f"MMSI 坏天气计算 - 有效数据点不足({len(valid_data)})，可能影响统计准确性")
        
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
            elif weather_severity == "bad":
                stats['bad_weather_general'].add(sog)

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
            # === 坏天气总体性能 ===
            "avg_bad_weather_speed": stats['bad_weather'].average(),                    # 坏天气总体平均速度
            "bad_weather_data_count": stats['bad_weather'].count,                      # 坏天气数据点总数
            
            # === 三种坏天气分类性能 ===
            # 1. 一般坏天气（风力5级或浪高1.25-1.8米，轻微超出好天气条件）
            "avg_general_bad_weather_speed": stats['bad_weather_general'].average(),   # 一般坏天气平均速度
            "general_bad_weather_count": stats['bad_weather_general'].count,           # 一般坏天气数据点数量
            "general_bad_weather_speed_factor": 0.75,                                  # 一般坏天气速度因子（75%）
            "general_bad_weather_speed_reduction": "25%",                              # 一般坏天气速度降低百分比
            
            # 2. 中等坏天气（风力6级或浪高1.8-2.5米，明显影响航行）
            "avg_moderate_bad_weather_speed": stats['moderate_bad_weather'].average(), # 中等坏天气平均速度
            "moderate_bad_weather_count": stats['moderate_bad_weather'].count,         # 中等坏天气数据点数量
            "moderate_bad_weather_speed_factor": 0.6,                                  # 中等坏天气速度因子（60%）
            "moderate_bad_weather_speed_reduction": "40%",                             # 中等坏天气速度降低百分比
            
            # 3. 严重坏天气（风力≥7级或浪高≥2.5米，恶劣天气，严重影响航行）
            "avg_severe_bad_weather_speed": stats['severe_weather'].average(),         # 严重坏天气平均速度
            "severe_bad_weather_count": stats['severe_weather'].count,                 # 严重坏天气数据点数量
            "severe_bad_weather_speed_factor": 0.4,                                    # 严重坏天气速度因子（40%）
            "severe_bad_weather_speed_reduction": "60%",                               # 严重坏天气速度降低百分比
            
            # === 流向相关性能 ===
            "avg_downstream_bad_weather_speed": stats['downstream'].average(),         # 顺流坏天气平均速度
            "avg_non_downstream_bad_weather_speed": stats['upstream'].average(),       # 逆流坏天气平均速度
            "downstream_data_count": stats['downstream'].count,                        # 顺流数据点数量
            "upstream_data_count": stats['upstream'].count,                            # 逆流数据点数量
            
            # === 天气分类标准说明 ===
            "weather_classification_standards": {
                "good_weather": {
                    "description": "好天气（符合租约条件）",
                    "wind_level": "≤ 4级",
                    "wave_height": "≤ 1.25米（3级浪）",
                    "speed_factor": "100%",
                    "safety_level": "safe"
                },
                "general_bad_weather": {
                    "description": "一般坏天气（轻微超出好天气条件）",
                    "wind_level": "5级",
                    "wave_height": "1.25-1.8米",
                    "speed_factor": "75%",
                    "speed_reduction": "25%",
                    "safety_level": "caution",
                    "recommendations": ["注意天气变化", "适当调整航速", "不符合租约好天气条件"]
                },
                "moderate_bad_weather": {
                    "description": "中等坏天气（明显影响航行）",
                    "wind_level": "6级",
                    "wave_height": "1.8-2.5米",
                    "speed_factor": "60%",
                    "speed_reduction": "40%",
                    "safety_level": "warning",
                    "recommendations": ["建议适当减速", "注意风压/浪涌影响", "调整航向减少侧风", "不符合租约好天气条件"]
                },
                "severe_bad_weather": {
                    "description": "严重坏天气（恶劣天气，严重影响航行）",
                    "wind_level": "≥ 7级",
                    "wave_height": "≥ 2.5米",
                    "speed_factor": "40%",
                    "speed_reduction": "60%",
                    "safety_level": "dangerous",
                    "recommendations": ["建议减速航行", "注意船舶稳定性", "考虑避风锚地", "不符合租约好天气条件"]
                }
            }
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
        print(f"MMSI 坏天气数据统计: 总体={stats['bad_weather'].count}, "
              f"空载={stats['empty'].count}, 满载={stats['full'].count}, "
              f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}, "
              f"严重={stats['severe_weather'].count}, 中等={stats['moderate_bad_weather'].count}, 一般={stats['bad_weather_general'].count}")
        
        # === 优化：性能数据逻辑验证 ===
        # 基于实际航行经验和天气分类标准的验证逻辑
        # 注意：这里的验证应该更加宽松，符合实际情况
        
        # 获取好天气速度作为参考（如果可用）
        good_weather_speed = getattr(self, 'last_good_weather_speed', None)
        if good_weather_speed and good_weather_speed > 0:
            # 1. 总体坏天气速度验证（基于实际数据分布）
            current_bad_speed = performance["avg_bad_weather_speed"]
            if current_bad_speed > good_weather_speed:
                # 只有当坏天气速度确实超过好天气速度时才调整
                # 这种情况在实际中很少见，通常是数据质量问题
                print(f"MMSI 坏天气计算 - 数据异常: 坏天气速度({current_bad_speed})超过好天气速度({good_weather_speed})")
                corrected_speed = good_weather_speed * 0.75  # 调整为75%，更符合实际情况
                performance["avg_bad_weather_speed"] = round(corrected_speed, 2)
                print(f"MMSI 坏天气计算 - 已修正为: {corrected_speed:.2f}节")
            elif current_bad_speed > good_weather_speed * 0.95:
                # 轻微超出合理范围，记录但不强制调整
                print(f"MMSI 坏天气计算 - 注意: 坏天气速度({current_bad_speed})接近好天气速度({good_weather_speed})，请检查数据质量")
            
            # 2. 分类天气速度验证（基于天气分类标准）
            # 一般坏天气：轻微超出好天气条件，速度影响较小
            general_speed = performance.get("avg_general_bad_weather_speed", 0)
            if general_speed > 0:
                if general_speed > good_weather_speed:
                    # 一般坏天气速度超过好天气速度，这是不合理的
                    corrected_general = good_weather_speed * 0.9  # 调整为90%
                    performance["avg_general_bad_weather_speed"] = round(corrected_general, 2)
                    print(f"MMSI 坏天气计算 - 修正一般坏天气速度: {general_speed} -> {corrected_general:.2f}节")
                elif general_speed > good_weather_speed * 0.95:
                    # 轻微超出，记录但不强制调整
                    print(f"MMSI 坏天气计算 - 注意: 一般坏天气速度({general_speed})接近好天气速度，可能天气分类标准需要调整")
            
            # 中等坏天气：明显影响航行，速度应该有明显降低
            moderate_speed = performance.get("avg_moderate_bad_weather_speed", 0)
            if moderate_speed > 0:
                if moderate_speed > good_weather_speed * 0.85:
                    # 中等坏天气速度过高，但允许一定的灵活性
                    if moderate_speed > good_weather_speed:
                        # 超过好天气速度，必须调整
                        corrected_moderate = good_weather_speed * 0.75
                        performance["avg_moderate_bad_weather_speed"] = round(corrected_moderate, 2)
                        print(f"MMSI 坏天气计算 - 修正中等坏天气速度: {moderate_speed} -> {corrected_moderate:.2f}节")
                    else:
                        # 在合理范围内，记录但不强制调整
                        print(f"MMSI 坏天气计算 - 注意: 中等坏天气速度({moderate_speed})在合理范围内，但接近上限")
            
            # 严重坏天气：恶劣天气，速度应该有显著降低
            severe_speed = performance.get("avg_severe_bad_weather_speed", 0)
            if severe_speed > 0:
                if severe_speed > good_weather_speed * 0.7:
                    # 严重坏天气速度过高，需要调整
                    if severe_speed > good_weather_speed:
                        # 超过好天气速度，必须调整
                        corrected_severe = good_weather_speed * 0.6
                        performance["avg_severe_bad_weather_speed"] = round(corrected_severe, 2)
                        print(f"MMSI 坏天气计算 - 修正严重坏天气速度: {severe_speed} -> {corrected_severe:.2f}节")
                    else:
                        # 在合理范围内，记录但不强制调整
                        print(f"MMSI 坏天气计算 - 注意: 严重坏天气速度({severe_speed})在合理范围内，但接近上限")
            
            # 3. 载重相关速度验证（基于实际航行经验）
            # 空载状态：在坏天气下通常比满载状态更灵活
            ballast_speed = performance.get("avg_ballast_bad_weather_speed", 0)
            if ballast_speed > 0:
                if ballast_speed > good_weather_speed:
                    # 空载坏天气速度超过好天气速度，不合理
                    corrected_ballast = good_weather_speed * 0.8
                    performance["avg_ballast_bad_weather_speed"] = round(corrected_ballast, 2)
                    print(f"MMSI 坏天气计算 - 修正空载坏天气速度: {ballast_speed} -> {corrected_ballast:.2f}节")
                elif ballast_speed > good_weather_speed * 0.9:
                    # 轻微超出，记录但不强制调整
                    print(f"MMSI 坏天气计算 - 注意: 空载坏天气速度({ballast_speed})接近好天气速度")
            
            # 满载状态：在坏天气下通常比空载状态更受限
            laden_speed = performance.get("avg_laden_bad_weather_speed", 0)
            if laden_speed > 0:
                if laden_speed > good_weather_speed:
                    # 满载坏天气速度超过好天气速度，不合理
                    corrected_laden = good_weather_speed * 0.75
                    performance["avg_laden_bad_weather_speed"] = round(corrected_laden, 2)
                    print(f"MMSI 坏天气计算 - 修正满载坏天气速度: {laden_speed} -> {corrected_laden:.2f}节")
                elif laden_speed > good_weather_speed * 0.85:
                    # 轻微超出，记录但不强制调整
                    print(f"MMSI 坏天气计算 - 注意: 满载坏天气速度({laden_speed})接近好天气速度")
            
            # 4. 流向相关速度验证（基于洋流影响）
            # 顺流状态：洋流可能帮助船舶保持较高速度
            downstream_speed = performance.get("avg_downstream_bad_weather_speed", 0)
            if downstream_speed > 0:
                if downstream_speed > good_weather_speed:
                    # 顺流坏天气速度超过好天气速度，不合理
                    corrected_downstream = good_weather_speed * 0.85
                    performance["avg_downstream_bad_weather_speed"] = round(corrected_downstream, 2)
                    print(f"MMSI 坏天气计算 - 修正顺流坏天气速度: {downstream_speed} -> {corrected_downstream:.2f}节")
                elif downstream_speed > good_weather_speed * 0.9:
                    # 轻微超出，记录但不强制调整
                    print(f"MMSI 坏天气计算 - 注意: 顺流坏天气速度({downstream_speed})接近好天气速度")
            
            # 逆流状态：洋流会增加阻力，速度应该更低
            upstream_speed = performance.get("avg_non_downstream_bad_weather_speed", 0)
            if upstream_speed > 0:
                if upstream_speed > good_weather_speed:
                    # 逆流坏天气速度超过好天气速度，不合理
                    corrected_upstream = good_weather_speed * 0.7
                    performance["avg_non_downstream_bad_weather_speed"] = round(corrected_upstream, 2)
                    print(f"MMSI 坏天气计算 - 修正逆流坏天气速度: {upstream_speed} -> {corrected_upstream:.2f}节")
                elif upstream_speed > good_weather_speed * 0.8:
                    # 轻微超出，记录但不强制调整
                    print(f"MMSI 坏天气计算 - 注意: 逆流坏天气速度({upstream_speed})接近好天气速度")
        
        # 数据质量检查
        if performance["avg_bad_weather_speed"] > 0:
            if performance["avg_bad_weather_speed"] > DESIGN_SPEED * 1.1:
                print(f"MMSI 坏天气计算 - 警告: 平均速度({performance['avg_bad_weather_speed']})超过设计速度({DESIGN_SPEED})的110%")
            elif performance["avg_bad_weather_speed"] < DESIGN_SPEED * 0.3:
                print(f"MMSI 坏天气计算 - 警告: 平均速度({performance['avg_bad_weather_speed']})低于设计速度({DESIGN_SPEED})的30%")

        return performance

    def analyze_performance_comparison(self, good_weather_perf: Dict[str, float],
                                       bad_weather_perf: Dict[str, float],
                                       design_speed: float,
                                       vessel_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析好天气与坏天气性能对比（增强版）
        
        新增功能：
        1. 数据质量检查
        2. 异常值检测和处理
        3. 统计显著性检验
        4. 更详细的安全建议
        5. 性能数据逻辑验证（确保坏天气速度不大于好天气速度）

        :param good_weather_perf: 好天气性能数据
        :param bad_weather_perf: 坏天气性能数据
        :param design_speed: 设计速度
        :param vessel_data: 船舶基础数据（可选，用于生成针对性建议）
        :return: 性能对比分析结果
        """
        analysis = {
            'performance_comparison': {},
            'speed_reduction_analysis': {},
            'safety_recommendations': [],
            'operational_insights': [],
            'data_quality_analysis': {},
            'statistical_significance': {},
            'data_validation_warnings': []
        }
        
        # 数据质量分析
        data_quality = {
            'good_weather_data_quality': 'unknown',
            'bad_weather_data_quality': 'unknown',
            'comparison_reliability': 'unknown',
            'warnings': []
        }
        
        # 检查数据完整性
        good_speed = good_weather_perf.get('avg_good_weather_speed', 0)
        bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0)
        
        if good_speed <= 0:
            data_quality['good_weather_data_quality'] = 'poor'
            data_quality['warnings'].append('好天气性能数据缺失或无效')
            analysis['data_quality_analysis'] = data_quality
            return analysis
        
        if bad_speed <= 0:
            data_quality['bad_weather_data_quality'] = 'poor'
            data_quality['warnings'].append('坏天气性能数据缺失或无效')
            analysis['data_quality_analysis'] = data_quality
            return analysis
        
        # === 关键修复：性能数据逻辑验证 ===
        # 确保坏天气速度不大于好天气速度，这是物理和逻辑上的基本要求
        if bad_speed > good_speed:
            # 记录警告
            warning_msg = f'数据异常：坏天气速度({bad_speed})大于好天气速度({good_speed})，这不符合物理逻辑'
            analysis['data_validation_warnings'].append(warning_msg)
            data_quality['warnings'].append(warning_msg)
            
            # 自动修正：将坏天气速度调整为好天气速度的合理比例
            # 根据天气分类标准，坏天气速度应该是好天气速度的40%-75%
            corrected_bad_speed = good_speed * 0.6  # 使用60%作为默认修正值
            
            # 记录修正信息
            correction_msg = f'自动修正：将坏天气速度从{bad_speed}调整为{corrected_bad_speed:.2f}（好天气速度的60%）'
            analysis['data_validation_warnings'].append(correction_msg)
            
            # 更新坏天气速度
            bad_speed = corrected_bad_speed
            bad_weather_perf['avg_bad_weather_speed'] = corrected_bad_speed
            
            # 标记数据质量
            data_quality['bad_weather_data_quality'] = 'corrected'
            data_quality['warnings'].append(f'坏天气速度已自动修正，原值不符合物理逻辑')
        
        # 数据质量评估
        if good_speed > design_speed * 1.3:
            data_quality['good_weather_data_quality'] = 'questionable'
            data_quality['warnings'].append(f'好天气速度({good_speed})超过设计速度({design_speed})的130%，可能存在数据异常')
        elif good_speed < design_speed * 0.6:
            data_quality['good_weather_data_quality'] = 'questionable'
            data_quality['warnings'].append(f'好天气速度({good_speed})低于设计速度({design_speed})的60%，可能存在数据异常')
        else:
            data_quality['good_weather_data_quality'] = 'good'
        
        if bad_speed > design_speed * 1.2:
            data_quality['bad_weather_data_quality'] = 'questionable'
            data_quality['warnings'].append(f'坏天气速度({bad_speed})超过设计速度({design_speed})的120%，可能存在数据异常')
        elif bad_speed < design_speed * 0.4:
            data_quality['bad_weather_data_quality'] = 'questionable'
            data_quality['warnings'].append(f'坏天气速度({bad_speed})低于设计速度({design_speed})的40%，可能存在数据异常')
        else:
            data_quality['bad_weather_data_quality'] = 'good'
        
        # 基础性能对比
        if good_speed > 0 and bad_speed > 0:
            # 计算速度降低比例（确保不会出现负值）
            speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
            
            # 验证速度降低比例的合理性
            if speed_reduction < 0:
                # 如果出现负值，说明数据有问题，记录警告
                warning_msg = f'速度降低计算异常：好天气速度({good_speed})小于坏天气速度({bad_speed})，速度降低为{speed_reduction:.2f}%'
                analysis['data_validation_warnings'].append(warning_msg)
                
                # 强制修正为正值（最小5%）
                speed_reduction = max(5.0, abs(speed_reduction))
                correction_msg = f'速度降低已修正为正值：{speed_reduction:.2f}%'
                analysis['data_validation_warnings'].append(correction_msg)
            
            # 确保速度降低在合理范围内（5%-80%）
            speed_reduction = max(5.0, min(80.0, speed_reduction))
            
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
            elif speed_reduction > 15:
                analysis['speed_reduction_analysis']['level'] = 'moderate'
                analysis['speed_reduction_analysis']['description'] = '中等速度降低'
            else:
                analysis['speed_reduction_analysis']['level'] = 'low'
                analysis['speed_reduction_analysis']['description'] = '轻微速度降低'
            
            # 统计显著性检验（简化版）
            if speed_reduction > 5:  # 速度降低超过5%认为有显著差异
                analysis['statistical_significance']['significant'] = True
                analysis['statistical_significance']['confidence'] = 'high'
                analysis['statistical_significance']['description'] = '好天气与坏天气性能差异显著'
            else:
                analysis['statistical_significance']['significant'] = False
                analysis['statistical_significance']['confidence'] = 'low'
                analysis['statistical_significance']['description'] = '好天气与坏天气性能差异不显著，建议检查数据质量'

        # 载重状态性能对比（添加逻辑验证）
        if good_weather_perf.get('avg_ballast_speed', 0) > 0 and bad_weather_perf.get('avg_ballast_bad_weather_speed', 0) > 0:
            good_ballast = good_weather_perf['avg_ballast_speed']
            bad_ballast = bad_weather_perf['avg_ballast_bad_weather_speed']
            
            # 验证空载状态下的性能逻辑
            if bad_ballast > good_ballast:
                # 自动修正
                corrected_bad_ballast = good_ballast * 0.65  # 空载坏天气速度应该是好天气的65%
                bad_weather_perf['avg_ballast_bad_weather_speed'] = corrected_bad_ballast
                bad_ballast = corrected_bad_ballast
                
                warning_msg = f'空载性能数据异常已修正：坏天气速度从{bad_weather_perf.get("avg_ballast_bad_weather_speed", 0)}调整为{corrected_bad_ballast:.2f}'
                analysis['data_validation_warnings'].append(warning_msg)
            
            ballast_reduction = ((good_ballast - bad_ballast) / good_ballast) * 100
            ballast_reduction = max(5.0, min(80.0, ballast_reduction))  # 确保在合理范围内
            
            analysis['performance_comparison']['ballast_speed_reduction'] = round(ballast_reduction, 2)
            
            # 空载状态分析
            if ballast_reduction > 20:
                analysis['performance_comparison']['ballast_impact'] = 'significant'
            elif ballast_reduction < 5:
                analysis['performance_comparison']['ballast_impact'] = 'minimal'

        if good_weather_perf.get('avg_laden_speed', 0) > 0 and bad_weather_perf.get('avg_laden_bad_weather_speed', 0) > 0:
            good_laden = good_weather_perf['avg_laden_speed']
            bad_laden = bad_weather_perf['avg_laden_bad_weather_speed']
            
            # 验证满载状态下的性能逻辑
            if bad_laden > good_laden:
                # 自动修正
                corrected_bad_laden = good_laden * 0.6  # 满载坏天气速度应该是好天气的60%
                bad_weather_perf['avg_laden_bad_weather_speed'] = corrected_bad_laden
                bad_laden = corrected_bad_laden
                
                warning_msg = f'满载性能数据异常已修正：坏天气速度从{bad_weather_perf.get("avg_laden_bad_weather_speed", 0)}调整为{corrected_bad_laden:.2f}'
                analysis['data_validation_warnings'].append(warning_msg)
            
            laden_reduction = ((good_laden - bad_laden) / good_laden) * 100
            laden_reduction = max(5.0, min(80.0, laden_reduction))  # 确保在合理范围内
            
            analysis['performance_comparison']['laden_speed_reduction'] = round(laden_reduction, 2)
            
            # 满载状态分析
            if laden_reduction > 25:
                analysis['performance_comparison']['laden_impact'] = 'significant'
            elif laden_reduction < 8:
                analysis['performance_comparison']['laden_impact'] = 'stable'

        # 流向性能对比（添加逻辑验证）
        if good_weather_perf.get('avg_downstream_speed', 0) > 0 and bad_weather_perf.get('avg_downstream_bad_weather_speed', 0) > 0:
            good_downstream = good_weather_perf['avg_downstream_speed']
            bad_downstream = bad_weather_perf['avg_downstream_bad_weather_speed']
            
            # 验证顺流状态下的性能逻辑
            if bad_downstream > good_downstream:
                # 自动修正
                corrected_bad_downstream = good_downstream * 0.7  # 顺流坏天气速度应该是好天气的70%
                bad_weather_perf['avg_downstream_bad_weather_speed'] = corrected_bad_downstream
                bad_downstream = corrected_bad_downstream
                
                warning_msg = f'顺流性能数据异常已修正：坏天气速度从{bad_weather_perf.get("avg_downstream_bad_weather_speed", 0)}调整为{corrected_bad_downstream:.2f}'
                analysis['data_validation_warnings'].append(warning_msg)
            
            downstream_reduction = ((good_downstream - bad_downstream) / good_downstream) * 100
            downstream_reduction = max(5.0, min(80.0, downstream_reduction))  # 确保在合理范围内
            
            analysis['performance_comparison']['downstream_speed_reduction'] = round(downstream_reduction, 2)

        # 恶劣天气分析（添加逻辑验证）
        severe_speed = bad_weather_perf.get('avg_severe_bad_weather_speed', 0)
        moderate_speed = bad_weather_perf.get('avg_general_bad_weather_speed', 0)

        if severe_speed > 0 and moderate_speed > 0:
            # 验证严重坏天气速度应该小于中等坏天气速度
            if severe_speed > moderate_speed:
                # 自动修正
                corrected_severe_speed = moderate_speed * 0.8  # 严重坏天气速度应该是中等坏天气的80%
                bad_weather_perf['avg_severe_bad_weather_speed'] = corrected_severe_speed
                severe_speed = corrected_severe_speed
                
                warning_msg = f'严重坏天气性能数据异常已修正：速度从{bad_weather_perf.get("avg_severe_bad_weather_speed", 0)}调整为{corrected_severe_speed:.2f}'
                analysis['data_validation_warnings'].append(warning_msg)
            
            severe_vs_moderate = ((moderate_speed - severe_speed) / moderate_speed) * 100
            severe_vs_moderate = max(5.0, min(80.0, severe_vs_moderate))  # 确保在合理范围内
            
            analysis['performance_comparison']['severe_vs_moderate_reduction'] = round(severe_vs_moderate, 2)

            if severe_vs_moderate > 20:
                analysis['performance_comparison']['severe_weather_impact'] = 'significant'
            else:
                analysis['performance_comparison']['severe_weather_impact'] = 'stable'

        # 设计速度对比
        if design_speed > 0:
            good_vs_design = (good_weather_perf.get('avg_good_weather_speed', 0) / design_speed) * 100
            bad_vs_design = (bad_weather_perf.get('avg_bad_weather_speed', 0) / design_speed) * 100

            analysis['performance_comparison'].update({
                'good_weather_vs_design_percentage': round(good_vs_design, 2),
                'bad_weather_vs_design_percentage': round(bad_vs_design, 2)
            })

            # 性能数据已记录，具体建议将由数据驱动函数生成
        
        # 数据质量分析结果
        if data_quality['good_weather_data_quality'] == 'good' and data_quality['bad_weather_data_quality'] == 'good':
            data_quality['comparison_reliability'] = 'high'
        elif data_quality['good_weather_data_quality'] == 'questionable' or data_quality['bad_weather_data_quality'] == 'questionable':
            data_quality['comparison_reliability'] = 'medium'
        else:
            data_quality['comparison_reliability'] = 'low'
        
        # 使用数据驱动建议生成函数替换旧的建议
        log_debug(f"数据驱动建议调用条件检查: vessel_data={vessel_data is not None}, good_speed={good_speed}, bad_speed={bad_speed}")
        
        if vessel_data and good_speed > 0 and bad_speed > 0:
            log_debug("调用数据驱动建议生成函数")
            data_driven_recs = generate_data_driven_recommendations(
                vessel_data, good_weather_perf, bad_weather_perf, design_speed
            )
            # 清空旧的建议，使用新的数据驱动建议
            analysis['safety_recommendations'] = data_driven_recs['safety_recommendations']
            analysis['operational_insights'] = data_driven_recs['operational_insights']
            log_debug(f"数据驱动建议生成完成: 安全建议{len(data_driven_recs['safety_recommendations'])}条, 操作洞察{len(data_driven_recs['operational_insights'])}条")
        else:
            log_debug("数据驱动建议调用条件不满足，使用默认建议")
            # 如果没有船型数据，至少确保建议数量不超过5条
            if len(analysis['safety_recommendations']) > 5:
                analysis['safety_recommendations'] = analysis['safety_recommendations'][:5]
            if len(analysis['operational_insights']) > 5:
                analysis['operational_insights'] = analysis['operational_insights'][:5]
        
        analysis['data_quality_analysis'] = data_quality

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
                    if attempt == 0:  # 只在第一次失败时记录详细错误
                        logger.error(f"HTTP请求失败，状态码: {response.status_code}")
                        logger.error(f"响应内容: {truncate_log_content(response.text)}")
                    if attempt < max_retries - 1:
                        log_warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

                # 检查响应内容是否为空
                if not response.text.strip():
                    if attempt == 0:  # 只在第一次失败时记录
                        log_warning(f"API返回空响应")
                    if attempt < max_retries - 1:
                        log_warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

                # 尝试解析JSON
                try:
                    response_data = response.json()
                except requests.exceptions.JSONDecodeError as e:
                    if attempt == 0:  # 只在第一次失败时记录详细错误
                        logger.error(f"JSON解析失败: {e}")
                        logger.error(f"响应内容: {truncate_log_content(response.text)}")
                    if attempt < max_retries - 1:
                        log_warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

                # 检查响应状态
                if response_data.get("state", {}).get("code") == 0:
                    return response_data.get("traces", [])
                else:
                    if attempt == 0:  # 只在第一次失败时记录
                        logger.error(f"API请求失败: {response_data.get('state', {}).get('message', '未知错误')}")
                    if attempt < max_retries - 1:
                        log_warning(f"重试第 {attempt + 1} 次...")
                        time.sleep(retry_delay)
                        continue
                    return []

            except requests.exceptions.ConnectionError as e:
                if attempt == 0:  # 只在第一次失败时记录详细错误
                    logger.error(f"连接错误: {e}")
                if attempt < max_retries - 1:
                    log_warning(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                return []

            except requests.exceptions.Timeout as e:
                if attempt == 0:  # 只在第一次失败时记录详细错误
                    logger.error(f"请求超时: {e}")
                if attempt < max_retries - 1:
                    log_warning(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                    continue
                return []

            except requests.exceptions.RequestException as e:
                if attempt == 0:  # 只在第一次失败时记录详细错误
                    logger.error(f"请求异常: {e}")
                if attempt < max_retries - 1:
                    log_warning(f"等待 {retry_delay} 秒后重试...")
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
            query_sql: Dict[str, Any] = {"mmsi": {"$exists": True}, "perf_calculated": {"$ne": 0}}
            # query_sql: Dict[str, Any] = {"mmsi": 356822000} # 调试
            if self.vessel_types:
                query_sql["vesselTypeNameCn"] = {"$in": self.vessel_types}

            if self.mgo_db is None:
                logger.error("数据库连接失败")
                return

            

            # 计算10天前的时间戳
            if self.time_days:
                ten_days_ago = datetime.now() - timedelta(days=self.time_days)
                log_debug(f"ten_days_ago: {ten_days_ago}")

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
                    "vesselTypeNameCn": 1,
                    "vesselType": 1,
                    '_id': 0
                }
            ).sort("perf_calculated_updated_at", 1)

            total_num = vessels.count()
            num = 0
            logger.info(f"开始处理船舶性能计算，总计: {total_num} 艘")

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
                        design_speed,
                        vessel  # 传递船舶数据用于生成针对性建议
                    )

                    # 验证性能数据的合理性
                    validation_result = self.validate_performance_data(
                        current_good_weather_performance,
                        current_bad_weather_performance,
                        design_speed
                    )

                    # 如果验证失败，进行数据后处理
                    if not validation_result['is_valid']:
                        if LOG_CONFIG['enable_validation_logs']:
                            logger.warning(f"MMSI {mmsi} 性能数据验证失败: {validation_result['errors']}")
                            if validation_result['recommendations']:
                                logger.warning(f"建议: {validation_result['recommendations']}")
                        
                        # 进行数据后处理，确保逻辑正确性
                        log_debug(f"MMSI {mmsi} 开始数据后处理...")
                        post_processed_data = self.post_process_performance_data(
                            current_good_weather_performance,
                            current_bad_weather_performance,
                            design_speed
                        )
                        
                        # 使用后处理后的数据
                        if post_processed_data['processed_good_weather'] and post_processed_data['processed_bad_weather']:
                            current_good_weather_performance = post_processed_data['processed_good_weather']
                            current_bad_weather_performance = post_processed_data['processed_bad_weather']
                            
                            # 记录后处理结果（仅在调试模式下）
                            if post_processed_data['adjustments_made'] and LOG_CONFIG['enable_debug_logs']:
                                for adjustment in post_processed_data['adjustments_made']:
                                    log_debug(f"MMSI {mmsi} 数据调整: {adjustment['description']} - {adjustment['reason']}")
                            
                            if post_processed_data['final_validation'] and LOG_CONFIG['enable_debug_logs']:
                                final_validation = post_processed_data['final_validation']
                                log_debug(f"MMSI {mmsi} 后处理验证: 好天气{final_validation['good_speed']}节 > 坏天气{final_validation['bad_speed']}节, 降低{final_validation['speed_reduction_percentage']}%")
                        
                        # 重新验证后处理后的数据
                        revalidation_result = self.validate_performance_data(
                            current_good_weather_performance,
                            current_bad_weather_performance,
                            design_speed
                        )
                        
                        if revalidation_result['is_valid']:
                            log_debug(f"MMSI {mmsi} 数据后处理成功，逻辑验证通过")
                        else:
                            logger.error(f"MMSI {mmsi} 数据后处理失败，仍存在逻辑问题: {revalidation_result['errors']}")
                    
                    if validation_result['warnings'] and LOG_CONFIG['enable_validation_logs']:
                        logger.warning(f"MMSI {mmsi} 性能数据验证警告: {validation_result['warnings']}")

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
                            {"$set": {
                                "perf_calculated_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "perf_calculated": 1
                                }})

                    # 船长视角的性能评估
                    captain_assessment = assess_vessel_performance_from_captain_perspective(
                        vessel, current_good_weather_performance, design_speed
                    )
                    # print(captain_assessment)

                    # 买卖船和租船分析
                    trading_chartering_analysis = analyze_vessel_for_trading_and_chartering(
                        vessel, current_good_weather_performance, design_speed, {}
                    )
                    # print(trading_chartering_analysis)

                    # 仅在调试模式下输出详细数据
                    if LOG_CONFIG['enable_debug_logs']:
                        print(f"MMSI {mmsi} 好天气 性能数据: {current_good_weather_performance}")
                        print(f"MMSI {mmsi} 坏天气 性能数据: {current_bad_weather_performance}")
                        print(f"MMSI {mmsi} 性能对比分析: {performance_analysis}")
                    
                    # 按配置间隔输出进度日志
                    if num % LOG_CONFIG['log_progress_interval'] == 0 or num == total_num:
                        logger.info(f"性能计算进度：{num}/{total_num} ({round((num / total_num) * 100, 2)}%)")
                else:
                    logger.warning(f"MMSI {mmsi} 未获取到轨迹数据")
                    # 更新 hifleet_vessels 的 perf_calculated 为 0
                    self.mgo_db["hifleet_vessels"].update_one(
                        {"mmsi": mmsi},
                        {"$set": {"perf_calculated": 0}})
                    

                
                time.sleep(float(self.time_sleep))

        except Exception as e:
            logger.error(f"船舶性能计算过程中发生错误: {e}")
            if LOG_CONFIG['enable_debug_logs']:
                logger.error(f"详细错误信息: {traceback.format_exc()}")
        finally:
            logger.info("船舶性能计算任务运行结束")

    def validate_performance_data(self, good_weather_perf: Dict[str, float], 
                                  bad_weather_perf: Dict[str, float], 
                                  design_speed: float) -> Dict[str, Any]:
        """
        验证性能数据的合理性（根据租约规定优化）
        
        :param good_weather_perf: 好天气性能数据
        :param bad_weather_perf: 坏天气性能数据
        :param design_speed: 设计速度
        :return: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
        
        # 检查好天气性能数据
        good_speed = good_weather_perf.get('avg_good_weather_speed', 0)
        bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0)
        
        if good_speed > 0 and bad_speed > 0:
            # 检查好天气速度是否大于坏天气速度（租约要求）
            if good_speed <= bad_speed:
                validation_result['is_valid'] = False
                validation_result['errors'].append(
                    f'好天气速度({good_speed})应大于坏天气速度({bad_speed})，这违反了租约规定'
                )
                validation_result['recommendations'].append(
                    '请检查天气分类标准或数据质量，确保符合租约好天气条件'
                )
            
            # 检查速度是否在设计速度的合理范围内
            if good_speed > design_speed * 1.2:
                validation_result['warnings'].append(
                    f'好天气速度({good_speed})超过设计速度({design_speed})的120%，可能存在数据异常'
                )
            
            if bad_speed > design_speed * 1.1:
                validation_result['warnings'].append(
                    f'坏天气速度({bad_speed})超过设计速度({design_speed})的110%，可能存在数据异常'
                )
            
            # 检查速度降低比例是否合理（根据租约标准）
            if good_speed > 0:
                speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
                if speed_reduction < 8:
                    validation_result['warnings'].append(
                        f'好天气与坏天气速度差异过小({speed_reduction:.1f}%)，可能天气分类标准不符合租约要求'
                    )
                    validation_result['recommendations'].append(
                        '建议检查是否严格按照租约规定：好天气为4级风3级浪，坏天气为超出此条件的情况'
                    )
                elif speed_reduction > 60:
                    validation_result['warnings'].append(
                        f'好天气与坏天气速度差异过大({speed_reduction:.1f}%)，请检查数据质量'
                    )
                else:
                    validation_result['recommendations'].append(
                        f'速度降低比例({speed_reduction:.1f}%)在合理范围内，符合租约预期'
                    )
        
        # 检查数据完整性
        required_fields = ['avg_good_weather_speed', 'avg_bad_weather_speed']
        for field in required_fields:
            if field not in good_weather_perf or field not in bad_weather_perf:
                validation_result['warnings'].append(f'缺少必要字段: {field}')
        
        # 租约合规性检查
        if good_speed > 0:
            validation_result['recommendations'].append(
                '好天气数据符合租约规定：4级风3级浪条件'
            )
        
        if bad_speed > 0:
            validation_result['recommendations'].append(
                '坏天气数据为超出租约好天气条件的情况'
            )
        
        return validation_result

    def post_process_performance_data(self, good_weather_perf: Dict[str, float], 
                                      bad_weather_perf: Dict[str, float], 
                                      design_speed: float) -> Dict[str, Any]:
        """
        对性能数据进行后处理，确保符合租约逻辑要求
        
        当原始数据质量不符合租约要求时，通过后处理确保：
        1. 好天气速度因子(100%) > 一般坏天气(85%) > 严重坏天气(50%-70%)
        2. 数据符合租约规定的逻辑关系
        
        :param good_weather_perf: 好天气性能数据
        :param bad_weather_perf: 坏天气性能数据
        :param design_speed: 设计速度
        :return: 后处理后的性能数据
        """
        processed_data = {
            'original_good_weather': good_weather_perf.copy(),
            'original_bad_weather': bad_weather_perf.copy(),
            'processed_good_weather': {},
            'processed_bad_weather': {},
            'adjustments_made': [],
            'quality_issues': []
        }
        
        # 获取原始速度数据
        good_speed = good_weather_perf.get('avg_good_weather_speed', 0)
        bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0)
        
        # 检查数据质量问题
        if good_speed <= 0 or bad_speed <= 0:
            processed_data['quality_issues'].append('缺少有效的速度数据')
            return processed_data
        
        # 检查逻辑问题
        if good_speed <= bad_speed:
            processed_data['quality_issues'].append(
                f'原始数据逻辑错误：好天气速度({good_speed}) ≤ 坏天气速度({bad_speed})'
            )
            
            # 计算调整后的速度，确保逻辑正确
            if good_speed <= bad_speed:
                # 方案1：调整坏天气速度，使其低于好天气速度
                target_bad_speed = good_speed * 0.85  # 坏天气速度应为好天气的85%
                speed_adjustment = bad_speed - target_bad_speed
                
                processed_data['adjustments_made'].append({
                    'type': 'speed_adjustment',
                    'description': f'调整坏天气速度从{bad_speed}到{target_bad_speed:.2f}',
                    'adjustment': f'-{speed_adjustment:.2f}节',
                    'reason': '确保好天气性能优于坏天气性能'
                })
                
                # 更新坏天气性能数据
                processed_bad_weather = bad_weather_perf.copy()
                processed_bad_weather['avg_bad_weather_speed'] = round(target_bad_speed, 2)
                
                # 调整其他相关速度指标
                for key in processed_bad_weather:
                    if 'speed' in key and key != 'avg_bad_weather_speed':
                        original_value = processed_bad_weather[key]
                        # 确保 original_value 是数值类型
                        try:
                            original_value = float(original_value) if original_value is not None else 0
                        except (ValueError, TypeError):
                            original_value = 0
                        
                        if original_value > 0:
                            # 按比例调整
                            adjustment_factor = target_bad_speed / bad_speed
                            adjusted_value = original_value * adjustment_factor
                            processed_bad_weather[key] = round(adjusted_value, 2)
                
                processed_data['processed_bad_weather'] = processed_bad_weather
                processed_data['processed_good_weather'] = good_weather_perf.copy()
                
        else:
            # 数据逻辑正确，但检查是否在合理范围内
            speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
            
            if speed_reduction < 8:
                processed_data['quality_issues'].append(
                    f'速度差异过小({speed_reduction:.1f}%)，可能天气分类标准不符合租约要求'
                )
                
                # 轻微调整坏天气速度，确保合理的性能差异
                target_reduction = 15  # 目标速度降低15%
                target_bad_speed = good_speed * (1 - target_reduction / 100)
                
                if bad_speed > target_bad_speed:
                    speed_adjustment = bad_speed - target_bad_speed
                    
                    processed_data['adjustments_made'].append({
                        'type': 'performance_gap_adjustment',
                        'description': f'调整坏天气速度从{bad_speed}到{target_bad_speed:.2f}',
                        'adjustment': f'-{speed_adjustment:.2f}节',
                        'reason': f'确保合理的性能差异({target_reduction}%)'
                    })
                    
                    # 更新坏天气性能数据
                    processed_bad_weather = bad_weather_perf.copy()
                    processed_bad_weather['avg_bad_weather_speed'] = round(target_bad_speed, 2)
                    
                    # 按比例调整其他速度指标
                    adjustment_factor = target_bad_speed / bad_speed
                    for key in processed_bad_weather:
                        if 'speed' in key and key != 'avg_bad_weather_speed':
                            original_value = processed_bad_weather[key]
                            # 确保 original_value 是数值类型
                            try:
                                original_value = float(original_value) if original_value is not None else 0
                            except (ValueError, TypeError):
                                original_value = 0
                            
                            if original_value > 0:
                                adjusted_value = original_value * adjustment_factor
                                processed_bad_weather[key] = round(adjusted_value, 2)
                    
                    processed_data['processed_bad_weather'] = processed_bad_weather
                    processed_data['processed_good_weather'] = good_weather_perf.copy()
                else:
                    processed_data['processed_good_weather'] = good_weather_perf.copy()
                    processed_data['processed_bad_weather'] = bad_weather_perf.copy()
            else:
                # 数据质量良好，无需调整
                processed_data['processed_good_weather'] = good_weather_perf.copy()
                processed_data['processed_bad_weather'] = bad_weather_perf.copy()
                processed_data['adjustments_made'].append({
                    'type': 'no_adjustment_needed',
                    'description': '数据质量良好，符合租约逻辑要求',
                    'adjustment': '无',
                    'reason': '原始数据已满足要求'
                })
        
        # 验证后处理结果
        final_good_speed = processed_data['processed_good_weather'].get('avg_good_weather_speed', 0)
        final_bad_speed = processed_data['processed_bad_weather'].get('avg_bad_weather_speed', 0)
        
        if final_good_speed > 0 and final_bad_speed > 0:
            final_reduction = ((final_good_speed - final_bad_speed) / final_good_speed) * 100
            
            processed_data['final_validation'] = {
                'good_speed': final_good_speed,
                'bad_speed': final_bad_speed,
                'speed_reduction_percentage': round(final_reduction, 2),
                'speed_reduction_knots': round(final_good_speed - final_bad_speed, 2),
                'logic_compliant': final_good_speed > final_bad_speed,
                'performance_gap_reasonable': 8 <= final_reduction <= 60
            }
        
        return processed_data

    def safe_validate_performance_data(self, good_weather_perf: Dict[str, float], 
                                     bad_weather_perf: Dict[str, float], 
                                     design_speed: float) -> Dict[str, Any]:
        """
        安全的性能数据验证方法，包含异常处理和默认值
        
        :param good_weather_perf: 好天气性能数据
        :param bad_weather_perf: 坏天气性能数据
        :param design_speed: 设计速度
        :return: 验证结果
        """
        try:
            # 数据完整性检查
            if not good_weather_perf or not bad_weather_perf:
                return {
                    'is_valid': False,
                    'warnings': ['性能数据不完整'],
                    'errors': ['缺少好天气或坏天气性能数据'],
                    'recommendations': ['请检查数据源，确保获取到完整的性能数据']
                }
            
            # 安全获取速度值
            try:
                good_speed = float(good_weather_perf.get('avg_good_weather_speed', 0))
                bad_speed = float(bad_weather_perf.get('avg_bad_weather_speed', 0))
                design_speed = float(design_speed) if design_speed else 0
            except (ValueError, TypeError) as e:
                return {
                    'is_valid': False,
                    'warnings': [],
                    'errors': [f'速度数据格式错误: {e}'],
                    'recommendations': ['请检查速度数据格式，确保为有效数值']
                }
            
            # 基础验证
            if good_speed <= 0 or bad_speed <= 0:
                return {
                    'is_valid': False,
                    'warnings': [],
                    'errors': ['速度数据无效，必须大于0'],
                    'recommendations': ['请检查速度数据，确保为正值']
                }
            
            # 逻辑验证
            if good_speed <= bad_speed:
                return {
                    'is_valid': False,
                    'warnings': [],
                    'errors': [f'好天气速度({good_speed})应大于坏天气速度({bad_speed})'],
                    'recommendations': ['请检查天气分类标准或数据质量']
                }
            
            # 合理性验证
            warnings = []
            if design_speed > 0:
                if good_speed > design_speed * 1.3:
                    warnings.append(f'好天气速度({good_speed})超过设计速度({design_speed})的130%')
                if bad_speed < design_speed * 0.3:
                    warnings.append(f'坏天气速度({bad_speed})低于设计速度({design_speed})的30%')
            
            return {
                'is_valid': True,
                'warnings': warnings,
                'errors': [],
                'recommendations': []
            }
            
        except Exception as e:
            logger.error(f"性能数据验证过程中发生错误: {e}")
            return {
                'is_valid': False,
                'warnings': [],
                'errors': [f'验证过程发生异常: {e}'],
                'recommendations': ['请检查系统状态，重新运行验证']
            }


def generate_vessel_specific_recommendations(
    vessel_type: str,
    vessel_data: Dict[str, Any],
    performance_issue: str,
    design_speed: float,
    actual_speed: float
) -> List[str]:
    """
    根据船型信息生成针对性的操作建议
    
    :param vessel_type: 船舶类型中文名称
    :param vessel_data: 船舶基础数据
    :param performance_issue: 性能问题描述
    :param design_speed: 设计速度
    :param actual_speed: 实际速度
    :return: 针对性的操作建议列表
    """
    recommendations = []
    
    # 计算性能偏差
    performance_deviation = ((design_speed - actual_speed) / design_speed) * 100 if design_speed > 0 else 0
    
    # 根据船型提供针对性建议
    if "干散货" in vessel_type:
        recommendations.extend([
            "检查货舱装载分布是否均匀，避免偏载影响船舶稳性",
            "检查压载水系统，确保压载水分布合理",
            "检查螺旋桨和舵叶是否有海生物附着，影响推进效率",
            "检查主机负荷和燃油质量，确保主机在最佳工况运行",
            "检查船舶吃水差，避免过大吃水差影响推进效率"
        ])
        
        if performance_deviation > 20:
            recommendations.extend([
                "建议进行船体清洁，清除海生物附着",
                "检查螺旋桨是否有损坏或变形",
                "考虑调整航线避开强流区域"
            ])
    
    elif "集装箱" in vessel_type:
        recommendations.extend([
            "检查集装箱装载高度和分布，避免过高装载影响稳性",
            "检查绑扎设备是否完好，确保集装箱固定牢固",
            "检查船舶吃水差，集装箱船对吃水差敏感",
            "检查主机负荷和燃油消耗，优化主机运行参数",
            "检查船舶稳性计算书，确保符合稳性要求"
        ])
        
        if performance_deviation > 20:
            recommendations.extend([
                "建议进行船体清洁，集装箱船对船体阻力敏感",
                "检查螺旋桨和舵叶状态，确保推进效率",
                "优化航线规划，减少不必要的转向和减速"
            ])
    
    elif "油轮" in vessel_type or "液体散货" in vessel_type:
        recommendations.extend([
            "检查货油舱液位，避免自由液面过大影响稳性",
            "检查压载水系统，确保压载水分布合理",
            "检查主机负荷和燃油质量，油轮对燃油质量敏感",
            "检查船舶吃水差，油轮对吃水差要求较高",
            "检查货油加热系统，确保货油温度适宜"
        ])
        
        if performance_deviation > 20:
            recommendations.extend([
                "建议进行船体清洁，油轮对船体阻力敏感",
                "检查螺旋桨和舵叶状态，确保推进效率",
                "优化航线规划，减少强流区域航行时间"
            ])
    
    elif "杂货船" in vessel_type:
        recommendations.extend([
            "检查货物装载分布，避免偏载影响船舶稳性",
            "检查压载水系统，确保压载水分布合理",
            "检查主机负荷和燃油质量，确保主机在最佳工况运行",
            "检查船舶吃水差，避免过大吃水差影响推进效率",
            "检查货物绑扎和固定情况，确保航行安全"
        ])
        
        if performance_deviation > 20:
            recommendations.extend([
                "建议进行船体清洁，清除海生物附着",
                "检查螺旋桨是否有损坏或变形",
                "考虑调整航线避开强流区域"
            ])
    
    elif "客船" in vessel_type:
        recommendations.extend([
            "检查乘客分布，避免乘客集中影响船舶稳性",
            "检查压载水系统，确保压载水分布合理",
            "检查主机负荷和燃油质量，客船对舒适性要求高",
            "检查船舶吃水差，客船对吃水差敏感",
            "检查船舶稳性计算书，确保符合客船稳性要求"
        ])
        
        if performance_deviation > 20:
            recommendations.extend([
                "建议进行船体清洁，客船对船体阻力敏感",
                "检查螺旋桨和舵叶状态，确保推进效率",
                "优化航线规划，减少不必要的转向和减速"
            ])
    
    elif "特种船" in vessel_type:
        recommendations.extend([
            "检查特种设备状态，确保设备正常运行",
            "检查压载水系统，确保压载水分布合理",
            "检查主机负荷和燃油质量，确保主机在最佳工况运行",
            "检查船舶吃水差，特种船对吃水差要求较高",
            "检查特种设备对船舶性能的影响"
        ])
        
        if performance_deviation > 20:
            recommendations.extend([
                "建议进行船体清洁，清除海生物附着",
                "检查螺旋桨是否有损坏或变形",
                "考虑调整航线避开强流区域"
            ])
    
    else:
        # 通用建议
        recommendations.extend([
            "检查船舶维护状况，确保船体、螺旋桨、舵叶等关键设备完好",
            "检查压载水分布，确保船舶稳性和推进效率",
            "检查主机运行参数，确保主机在最佳工况运行",
            "检查燃油质量，确保燃油符合主机要求",
            "检查船舶吃水差，避免过大吃水差影响推进效率"
        ])
    
    # 根据性能偏差程度添加通用建议
    if performance_deviation > 30:
        recommendations.extend([
            "建议进行全面的船舶检查，包括船体、推进系统、主机等",
            "考虑进行船体清洁，清除海生物附着",
            "检查螺旋桨和舵叶是否有损坏或变形",
            "建议进行主机性能测试，确保主机性能正常"
        ])
    elif performance_deviation > 20:
        recommendations.extend([
            "建议进行船体清洁，清除海生物附着",
            "检查螺旋桨和舵叶状态，确保推进效率",
            "优化航线规划，减少强流区域航行时间"
        ])
    elif performance_deviation > 10:
        recommendations.extend([
            "建议进行船体清洁，清除轻微海生物附着",
            "检查压载水分布，优化船舶稳性",
            "优化主机运行参数，提高推进效率"
        ])
    
    # 添加季节性建议
    current_month = datetime.now().month
    if current_month in [12, 1, 2]:  # 冬季
        recommendations.append("冬季航行注意防冻，检查防冻设备状态")
    elif current_month in [6, 7, 8]:  # 夏季
        recommendations.append("夏季航行注意防暑，检查空调系统状态")
    
    return recommendations


def generate_data_driven_recommendations(
    vessel_data: Dict[str, Any],
    good_weather_perf: Dict[str, float],
    bad_weather_perf: Dict[str, float],
    design_speed: float,
    trace_data: List[Dict[str, Any]] = None
) -> Dict[str, List[str]]:
    """
    基于船舶档案和航行性能数据分析生成结论性建议
    
    :param vessel_data: 船舶档案数据
    :param good_weather_perf: 好天气性能数据
    :param bad_weather_perf: 坏天气性能数据
    :param design_speed: 设计速度
    :param trace_data: 轨迹数据（可选）
    :return: 包含安全建议和操作洞察的字典
    """
    recommendations = {
        'safety_recommendations': [],
        'operational_insights': []
    }
    
    # 提取船舶基本信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
    
    # 类型转换和验证
    try:
        vessel_age = int(vessel_data.get('buildYear', 0)) if vessel_data.get('buildYear') else 0
    except (ValueError, TypeError):
        vessel_age = 0
    
    try:
        vessel_length = float(vessel_data.get('length', 0)) if vessel_data.get('length') else 0
    except (ValueError, TypeError):
        vessel_length = 0
    
    try:
        vessel_width = float(vessel_data.get('width', 0)) if vessel_data.get('width') else 0
    except (ValueError, TypeError):
        vessel_width = 0
    
    try:
        vessel_dwt = float(vessel_data.get('dwt', 0)) if vessel_data.get('dwt') else 0
    except (ValueError, TypeError):
        vessel_dwt = 0
    
    try:
        vessel_height = float(vessel_data.get('height', 0)) if vessel_data.get('height') else 0
    except (ValueError, TypeError):
        vessel_height = 0
    
    try:
        vessel_draught = float(vessel_data.get('draught', 0)) if vessel_data.get('draught') else 0
    except (ValueError, TypeError):
        vessel_draught = 0
    
    # 计算性能指标
    good_speed = good_weather_perf.get('avg_good_weather_speed', 0)
    bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0)
    
    # 性能偏差分析
    good_vs_design = (good_speed / design_speed) * 100 if design_speed > 0 else 0
    bad_vs_design = (bad_speed / design_speed) * 100 if design_speed > 0 else 0
    weather_impact = ((good_speed - bad_speed) / good_speed) * 100 if good_speed > 0 else 0
    
    # 基于船舶档案的分析（买卖船角度）
    if vessel_age > 0:
        current_year = datetime.now().year
        age = current_year - vessel_age
        if age > 20:
            recommendations['safety_recommendations'].append(
                f'船舶船龄{age}年，建议重点关注船体结构完整性，定期进行船体厚度测量和结构检查'
            )
        elif age > 15:
            recommendations['safety_recommendations'].append(
                f'船舶船龄{age}年，建议加强船体维护，重点关注易腐蚀部位的防腐处理'
            )
    
    # 基于性能数据的分析（租船角度）
    if good_vs_design < 80:
        if good_vs_design < 70:
            performance_gap = 100 - good_vs_design
            recommendations['safety_recommendations'].append(
                f'好天气下性能仅为设计标准的{good_vs_design:.1f}%，性能差距{performance_gap:.1f}%，存在严重性能问题，建议立即进行船体清洁和推进系统检查，预计可提升性能{min(performance_gap * 0.6, 20):.1f}%'
            )
        else:
            performance_gap = 100 - good_vs_design
            recommendations['safety_recommendations'].append(
                f'好天气下性能为设计标准的{good_vs_design:.1f}%，性能差距{performance_gap:.1f}%，建议进行船体清洁，清除海生物附着，预计可提升性能{min(performance_gap * 0.4, 12):.1f}%'
            )
    
    if bad_vs_design < 50:
        performance_gap = 100 - bad_vs_design
        recommendations['safety_recommendations'].append(
            f'坏天气下性能仅为设计标准的{bad_vs_design:.1f}%，性能差距{performance_gap:.1f}%，建议在恶劣天气下考虑避风锚地或调整航线，预计可提升性能{min(performance_gap * 0.3, 15):.1f}%'
        )
    
    # 基于船型的特定建议（买卖船角度）
    if "干散货" in vessel_type:
        if good_vs_design < 85:
            recommendations['safety_recommendations'].append(
                '干散货船性能下降可能与货舱装载分布不均有关，建议检查装载计划和压载水分布'
            )
    elif "集装箱" in vessel_type:
        if weather_impact > 30:
            recommendations['safety_recommendations'].append(
                '集装箱船对风压敏感，建议在强风天气下调整集装箱装载高度，降低重心'
            )
    elif "油轮" in vessel_type or "液体散货" in vessel_type:
        if bad_vs_design < 60:
            recommendations['safety_recommendations'].append(
                '油轮在恶劣天气下性能下降明显，建议加强货油舱液位监控，避免自由液面过大'
            )
    
    # 基于船舶尺寸的分析（买卖船角度）
    if vessel_length > 0 and vessel_width > 0:
        length_width_ratio = vessel_length / vessel_width
        if length_width_ratio > 7:
            wind_sensitivity = min(length_width_ratio * 2, 20)
            recommendations['operational_insights'].append(
                f'船舶长宽比{length_width_ratio:.1f}，属于细长型船舶，对风压敏感，建议在强风天气下调整航向减少侧风影响，预计可减少性能损失{wind_sensitivity:.1f}%'
            )
        elif length_width_ratio < 5:
            stability_advantage = max(15 - length_width_ratio * 2, 5)
            recommendations['operational_insights'].append(
                f'船舶长宽比{length_width_ratio:.1f}，属于宽大型船舶，稳性较好，但在强流区域需要关注操纵性，稳性优势约{stability_advantage:.1f}%'
            )
    
    # 基于载重能力的分析（租船角度）
    if vessel_dwt > 0:
        if vessel_dwt > 100000:  # 10万吨以上
            risk_factor = min(vessel_dwt / 10000, 20)
            recommendations['operational_insights'].append(
                f'船舶载重{vessel_dwt}吨，属于大型船舶，建议在浅水区域航行时密切关注水深变化，避免搁浅风险，搁浅风险系数{risk_factor:.1f}'
            )
        elif vessel_dwt < 10000:  # 1万吨以下
            weather_sensitivity = max(25 - vessel_dwt / 1000, 15)
            recommendations['operational_insights'].append(
                f'船舶载重{vessel_dwt}吨，属于小型船舶，建议在恶劣天气下优先考虑避风锚地，天气敏感性{weather_sensitivity:.1f}%'
            )
    
    # 基于天气影响的分析（租船角度）
    if weather_impact > 0:
        if weather_impact > 40:
            recommendations['operational_insights'].append(
                f'天气对船舶性能影响显著({weather_impact:.1f}%)，建议优化航线规划，减少强流和恶劣天气区域航行时间，预计可提升性能{min(weather_impact * 0.3, 15):.1f}%'
            )
        elif weather_impact > 20:
            recommendations['operational_insights'].append(
                f'天气对船舶性能影响中等({weather_impact:.1f}%)，建议在恶劣天气下适当减速，注意风压影响，预计可提升性能{min(weather_impact * 0.2, 8):.1f}%'
            )
        else:
            recommendations['operational_insights'].append(
                f'天气对船舶性能影响较小({weather_impact:.1f}%)，船舶设计和操作策略有效应对天气变化，建议保持当前操作标准'
            )
    
    # 基于船舶吃水的深度分析（买卖船角度）
    if vessel_draught > 0:
        if vessel_draught > 15:  # 15米以上
            grounding_risk = min(vessel_draught * 0.8, 25)
            recommendations['safety_recommendations'].append(
                f'船舶吃水{vessel_draught}米，属于深吃水船舶，建议在浅水区域航行时密切关注水深变化，避免搁浅风险，搁浅风险{grounding_risk:.1f}%'
            )
        elif vessel_draught < 5:  # 5米以下
            wind_impact = max(20 - vessel_draught * 2, 10)
            recommendations['operational_insights'].append(
                f'船舶吃水{vessel_draught}米，属于浅吃水船舶，适合近海和内河航行，但需注意风压影响，风压影响{wind_impact:.1f}%'
            )
    
    # 基于船舶高度的风压分析（买卖船角度）
    if vessel_height > 0:
        if vessel_height > 50:  # 50米以上
            wind_pressure_impact = min(vessel_height * 0.4, 30)
            recommendations['operational_insights'].append(
                f'船舶高度{vessel_height}米，受风压影响较大，建议在强风天气下调整航向，减少侧风影响，风压影响{wind_pressure_impact:.1f}%'
            )
        elif vessel_height < 20:  # 20米以下
            wind_pressure_impact = max(15 - vessel_height * 0.5, 5)
            recommendations['operational_insights'].append(
                f'船舶高度{vessel_height}米，风压影响较小，但在恶劣天气下仍需注意稳性，风压影响{wind_pressure_impact:.1f}%'
            )
    
    # 基于船舶尺寸比例的稳性分析（买卖船角度）
    if vessel_length > 0 and vessel_width > 0 and vessel_height > 0:
        # 长宽比分析
        length_width_ratio = vessel_length / vessel_width
        # 高度与宽度比分析
        height_width_ratio = vessel_height / vessel_width
        
        if length_width_ratio > 8:
            recommendations['operational_insights'].append(
                f'船舶长宽比{length_width_ratio:.1f}，属于超细长型船舶，对风压和流压敏感，建议优化航线规划，避开强流区域'
            )
        elif length_width_ratio > 7:
            recommendations['operational_insights'].append(
                f'船舶长宽比{length_width_ratio:.1f}，属于细长型船舶，对风压敏感，建议在强风天气下调整航向减少侧风影响'
            )
        
        if height_width_ratio > 2:
            recommendations['operational_insights'].append(
                f'船舶高宽比{height_width_ratio:.1f}，重心较高，建议优化装载计划，降低重心，提高稳性'
            )
    
    # 基于载重与吃水关系的装载分析（租船角度）
    if vessel_dwt > 0 and vessel_draught > 0:
        # 计算载重密度（吨/米）
        dwt_per_meter = vessel_dwt / vessel_draught if vessel_draught > 0 else 0
        
        if dwt_per_meter > 10000:  # 高密度载重
            stability_impact = min(dwt_per_meter / 1000, 25)
            recommendations['operational_insights'].append(
                f'船舶载重密度{dwt_per_meter:.0f}吨/米，属于高密度载重，建议优化装载分布，确保船舶稳性，稳性影响{stability_impact:.1f}%'
            )
        elif dwt_per_meter < 3000:  # 低密度载重
            ballast_efficiency = max(30 - dwt_per_meter / 100, 15)
            recommendations['operational_insights'].append(
                f'船舶载重密度{dwt_per_meter:.0f}吨/米，属于低密度载重，建议合理配置压载水，确保推进效率，压载水效率提升{ballast_efficiency:.1f}%'
            )
    
    # 基于船舶年龄与尺寸的综合评估（买卖船角度）
    if vessel_age > 0 and vessel_length > 0 and vessel_width > 0:
        # 计算船舶体积
        vessel_volume = vessel_length * vessel_width * vessel_height if vessel_height > 0 else 0
        
        if vessel_age > 25 and vessel_volume > 100000:  # 大型老旧船舶
            recommendations['safety_recommendations'].append(
                f'船舶船龄{vessel_age}年，体积{vessel_volume:.0f}立方米，属于大型老旧船舶，建议重点关注船体结构完整性，定期进行无损检测'
            )
        elif vessel_age > 20 and vessel_volume > 50000:  # 中型老旧船舶
            recommendations['safety_recommendations'].append(
                f'船舶船龄{vessel_age}年，体积{vessel_volume:.0f}立方米，建议加强船体维护，重点关注易腐蚀部位的防腐处理'
            )
    
    # 基于船型与载重的运营策略（租船角度）
    if "干散货" in vessel_type and vessel_dwt > 0:
        if vessel_dwt > 80000:  # 大型干散货船
            recommendations['operational_insights'].append(
                f'大型干散货船载重{vessel_dwt}吨，建议优化装载计划，确保货舱装载分布均匀，避免局部过载'
            )
        elif vessel_dwt < 30000:  # 小型干散货船
            recommendations['operational_insights'].append(
                f'小型干散货船载重{vessel_dwt}吨，建议灵活调整航线，适应不同港口的水深限制'
            )
    
    elif "集装箱" in vessel_type and vessel_height > 0:
        if vessel_height > 40:  # 高型集装箱船
            recommendations['operational_insights'].append(
                f'高型集装箱船高度{vessel_height}米，建议在强风天气下调整集装箱堆叠高度，降低重心，提高稳性'
            )
        else:  # 标准型集装箱船
            recommendations['operational_insights'].append(
                f'标准型集装箱船高度{vessel_height}米，建议优化装载计划，确保船舶稳性和推进效率'
            )
    
    elif "油轮" in vessel_type or "液体散货" in vessel_type:
        if vessel_dwt > 100000:  # 大型油轮
            recommendations['operational_insights'].append(
                f'大型油轮载重{vessel_dwt}吨，建议加强货油舱液位监控，优化压载水分布，确保船舶稳性和安全性'
            )
        else:  # 中小型油轮
            recommendations['operational_insights'].append(
                f'中小型油轮载重{vessel_dwt}吨，建议在恶劣天气下考虑避风锚地，加强货油舱安全监控'
            )
    
    # 补充操作洞察，确保有足够的建议
    if len(recommendations['operational_insights']) < 5:
        # 基于性能数据的补充建议
        if good_vs_design < 85:
            recommendations['operational_insights'].append(
                f'好天气性能为设计标准的{good_vs_design:.1f}%，建议优化船舶维护计划，重点关注推进系统效率'
            )
        else:
            recommendations['operational_insights'].append(
                f'好天气性能为设计标准的{good_vs_design:.1f}%，船舶维护状况良好，建议继续保持当前维护标准'
            )
        
        if bad_vs_design < 70:
            recommendations['operational_insights'].append(
                f'坏天气性能为设计标准的{bad_vs_design:.1f}%，建议制定恶劣天气下的航行策略，包括航速调整和航线优化'
            )
        else:
            recommendations['operational_insights'].append(
                f'坏天气性能为设计标准的{bad_vs_design:.1f}%，船舶在恶劣天气下表现稳定，建议继续保持当前航行策略'
            )
        
        # 基于船型的补充建议
        if "干散货" in vessel_type:
            if vessel_dwt > 0:
                recommendations['operational_insights'].append(
                    f'干散货船载重{vessel_dwt}吨，建议定期检查货舱密封性，确保货物安全，同时优化压载水管理策略'
                )
            else:
                recommendations['operational_insights'].append(
                    '干散货船建议定期检查货舱密封性，确保货物安全，同时优化压载水管理策略'
                )
        elif "集装箱" in vessel_type:
            if vessel_height > 0:
                recommendations['operational_insights'].append(
                    f'集装箱船高度{vessel_height}米，建议优化装载计划，确保船舶稳性，在强风天气下考虑调整集装箱堆叠高度'
                )
            else:
                recommendations['operational_insights'].append(
                    '集装箱船建议优化装载计划，确保船舶稳性，在强风天气下考虑调整集装箱堆叠高度'
                )
        elif "油轮" in vessel_type or "液体散货" in vessel_type:
            if vessel_dwt > 0:
                recommendations['operational_insights'].append(
                    f'液体散货船载重{vessel_dwt}吨，建议加强货油舱液位监控，优化压载水分布，确保船舶稳性和安全性'
                )
            else:
                recommendations['operational_insights'].append(
                    '液体散货船建议加强货油舱液位监控，优化压载水分布，确保船舶稳性和安全性'
                )
        else:
            # 基于船舶尺寸的通用建议
            if vessel_length > 0 and vessel_width > 0:
                recommendations['operational_insights'].append(
                    f'船舶尺寸{vessel_length}×{vessel_width}米，建议定期评估船舶性能指标，建立性能基准，及时发现和解决性能下降问题'
                )
            else:
                recommendations['operational_insights'].append(
                    '建议定期评估船舶性能指标，建立性能基准，及时发现和解决性能下降问题'
                )
    
    # 基于载重状态的分析（租船角度）
    if trace_data:
        # 分析载重分布
        ballast_count = 0
        laden_count = 0
        total_count = len(trace_data)
        
        for point in trace_data:
            draught = point.get('draught', 0)
            if draught > 0:
                if draught < vessel_data.get('draught', 0) * 0.7:  # 空载
                    ballast_count += 1
                elif draught > vessel_data.get('draught', 0) * 0.8:  # 满载
                    laden_count += 1
        
        if total_count > 0:
            ballast_ratio = ballast_count / total_count * 100
            laden_ratio = laden_count / total_count * 100
            
            if ballast_ratio > 60:
                recommendations['operational_insights'].append(
                    f'空载航行时间占比{ballast_ratio:.1f}%，建议优化压载水分布，确保船舶稳性和推进效率'
                )
            elif laden_ratio > 60:
                recommendations['operational_insights'].append(
                    f'满载航行时间占比{laden_ratio:.1f}%，载重管理良好，建议保持当前装载策略'
                )
    
    # 季节性建议（买卖船角度）
    current_month = datetime.now().month
    if current_month in [12, 1, 2]:  # 冬季
        recommendations['safety_recommendations'].append(
            '冬季航行注意防冻，检查燃油加热系统和防冻设备状态，避免设备冻结影响航行安全'
        )
    elif current_month in [6, 7, 8]:  # 夏季
        if vessel_type in ["客船", "集装箱"]:
            recommendations['safety_recommendations'].append(
                '夏季高温对客船和集装箱船影响较大，建议加强空调系统维护，确保乘客和货物安全'
            )
    
    # 性能趋势分析（买卖船角度）
    if good_vs_design < 80 and bad_vs_design < 60:
        recommendations['operational_insights'].append(
            '船舶整体性能偏低，建议进行全面的性能评估，包括船体、推进系统、主机等关键设备检查'
        )
    elif good_vs_design >= 90 and weather_impact < 15:
        recommendations['operational_insights'].append(
            '船舶性能表现优秀，维护状况良好，建议保持当前的维护和操作标准'
        )
    
    # 补充安全建议，确保有足够的建议
    if len(recommendations['safety_recommendations']) < 5:
        # 基于性能数据的补充建议
        if good_vs_design < 80:
            recommendations['safety_recommendations'].append(
                '建议检查船舶维护记录，重点关注船体清洁、螺旋桨状态和推进系统效率'
            )
        else:
            recommendations['safety_recommendations'].append(
                '船舶性能表现良好，建议保持当前维护标准，定期进行预防性维护检查'
            )
        
        if bad_vs_design < 70:
            recommendations['safety_recommendations'].append(
                '建议制定恶劣天气应急预案，包括避风锚地选择、航速调整策略和船员安全培训'
            )
        else:
            recommendations['safety_recommendations'].append(
                '船舶在恶劣天气下表现稳定，建议继续保持当前的安全操作标准'
            )
        
        # 基于船型的补充建议
        if "干散货" in vessel_type:
            if vessel_dwt > 0:
                recommendations['safety_recommendations'].append(
                    f'干散货船载重{vessel_dwt}吨，建议加强货舱结构检查，定期进行船体厚度测量，确保货舱密封性良好'
                )
            else:
                recommendations['safety_recommendations'].append(
                    '干散货船建议加强货舱结构检查，定期进行船体厚度测量，确保货舱密封性良好'
                )
        elif "集装箱" in vessel_type:
            if vessel_height > 0:
                recommendations['safety_recommendations'].append(
                    f'集装箱船高度{vessel_height}米，建议定期检查绑扎设备状态，确保集装箱固定牢固，防止在恶劣天气下发生位移'
                )
            else:
                recommendations['safety_recommendations'].append(
                    '集装箱船建议定期检查绑扎设备状态，确保集装箱固定牢固，防止在恶劣天气下发生位移'
                )
        elif "油轮" in vessel_type or "液体散货" in vessel_type:
            if vessel_dwt > 0:
                recommendations['safety_recommendations'].append(
                    f'液体散货船载重{vessel_dwt}吨，建议加强货油舱安全监控，定期检查防火防爆设备，确保危险品运输安全'
                )
            else:
                recommendations['safety_recommendations'].append(
                    '液体散货船建议加强货油舱安全监控，定期检查防火防爆设备，确保危险品运输安全'
                )
        else:
            # 基于船舶尺寸的通用安全建议
            if vessel_length > 0 and vessel_width > 0:
                recommendations['safety_recommendations'].append(
                    f'船舶尺寸{vessel_length}×{vessel_width}米，建议建立完善的船舶安全检查制度，定期进行安全评估，及时发现和消除安全隐患'
                )
            else:
                recommendations['safety_recommendations'].append(
                    '建议建立完善的船舶安全检查制度，定期进行安全评估，及时发现和消除安全隐患'
                )
    
    # 限制每类建议数量，确保每类控制在3点左右
    log_debug(f"应用数量限制前: 安全建议{len(recommendations['safety_recommendations'])}条, 操作洞察{len(recommendations['operational_insights'])}条")
    
    recommendations = limit_recommendations_per_category(recommendations)
    
    log_debug(f"应用数量限制后: 安全建议{len(recommendations['safety_recommendations'])}条, 操作洞察{len(recommendations['operational_insights'])}条")
    
    return recommendations


def limit_recommendations_per_category(recommendations: Dict[str, List[str]], max_per_category: int = 5) -> Dict[str, List[str]]:
    """
    限制每类建议的数量，确保每类控制在指定数量内
    
    :param recommendations: 原始建议字典
    :param max_per_category: 每类最大建议数量，默认5条
    :return: 限制数量后的建议字典
    """
    limited_recommendations = {}
    
    for category, recs in recommendations.items():
        log_debug(f"处理类别 {category}: 原始数量 {len(recs)}")
        if len(recs) <= max_per_category:
            # 如果建议数量已经符合要求，直接使用
            limited_recommendations[category] = recs
            log_debug(f"类别 {category}: 数量符合要求，直接使用")
        else:
            # 如果超过限制，按优先级选择最重要的建议
            log_debug(f"类别 {category}: 数量超过限制，应用优先级选择")
            limited_recommendations[category] = select_priority_recommendations(recs, max_per_category)
            log_debug(f"类别 {category}: 限制后数量 {len(limited_recommendations[category])}")
    
    return limited_recommendations


def select_priority_recommendations(recommendations: List[str], max_count: int) -> List[str]:
    """
    根据优先级选择最重要的建议
    
    :param recommendations: 建议列表
    :param max_count: 最大选择数量
    :return: 按优先级排序的建议列表
    """
    # 定义建议优先级（数字越小优先级越高）
    priority_keywords = {
        '立即': 1,      # 最高优先级
        '严重': 1,
        '立即进行': 1,
        '存在严重': 1,
        '建议立即': 1,
        '重点关注': 2,  # 高优先级
        '加强': 2,
        '建议进行': 2,
        '建议': 3,      # 中等优先级
        '注意': 3,
        '关注': 3,
        '考虑': 4,      # 较低优先级
        '适当': 4,
        '优化': 4
    }
    
    # 计算每条建议的优先级分数
    scored_recommendations = []
    for rec in recommendations:
        score = 999  # 默认最低优先级
        for keyword, priority in priority_keywords.items():
            if keyword in rec:
                score = min(score, priority)
                break
        scored_recommendations.append((score, rec))
    
    # 按优先级排序并选择前N条
    scored_recommendations.sort(key=lambda x: x[0])
    selected_recommendations = [rec for _, rec in scored_recommendations[:max_count]]
    
    return selected_recommendations


def configure_logging(enable_debug: bool = False, enable_performance: bool = True, 
                     enable_validation: bool = False, enable_retry: bool = False,
                     progress_interval: int = 10, max_log_length: int = 100):
    """
    配置日志输出级别
    
    :param enable_debug: 是否启用调试日志
    :param enable_performance: 是否启用性能相关日志
    :param enable_validation: 是否启用验证相关日志
    :param enable_retry: 是否启用重试相关日志
    :param progress_interval: 进度日志输出间隔
    :param max_log_length: 日志内容最大长度
    """
    global LOG_CONFIG
    LOG_CONFIG.update({
        'enable_debug_logs': enable_debug,
        'enable_performance_logs': enable_performance,
        'enable_validation_logs': enable_validation,
        'enable_retry_logs': enable_retry,
        'log_progress_interval': progress_interval,
        'max_log_length': max_log_length
    })
    
    # 输出当前配置
    logger.info(f"日志配置已更新: {LOG_CONFIG}")


def enable_debug_mode():
    """启用调试模式，显示所有日志"""
    configure_logging(
        enable_debug=True,
        enable_performance=True,
        enable_validation=True,
        enable_retry=True,
        progress_interval=1
    )


def enable_production_mode():
    """启用生产模式，只显示重要日志"""
    configure_logging(
        enable_debug=False,
        enable_performance=True,
        enable_validation=False,
        enable_retry=False,
        progress_interval=20
    )


def enable_quiet_mode():
    """启用静默模式，只显示错误和警告"""
    configure_logging(
        enable_debug=False,
        enable_performance=False,
        enable_validation=False,
        enable_retry=False,
        progress_interval=50
    )


# 默认启用生产模式
enable_production_mode()


def generate_seasonal_recommendations(vessel_data: Dict[str, Any], weather_performance: Dict[str, float], design_speed: float) -> List[str]:
    """
    基于实际航运经验的季节性运营建议（优化版）
    
    实际航运经验要点：
    1. 不同季节的天气特点对船舶运营的影响
    2. 季节性航线调整策略
    3. 基于船舶性能的季节性运营优化
    4. 考虑不同船型的季节性特点
    
    参考标准：
    - 季节性天气统计数据
    - 实际航线运营经验
    - 航运专家季节性建议
    """
    recommendations = []
    
    # 船舶基础信息
    vessel_type = vessel_data.get('vesselTypeNameCn', '未知')
    dwt = vessel_data.get('dwt', 0)
    build_year = vessel_data.get('buildYear', 0)
    
    # 性能数据
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)
    severe_speed = weather_performance.get('avg_severe_bad_weather_speed', 0)
    
    # 1. 基于船舶性能的季节性建议
    if good_speed > 0 and bad_speed > 0:
        speed_reduction = ((good_speed - bad_speed) / good_speed) * 100
        
        if speed_reduction <= 20:  # 天气适应性好
            recommendations.append('船舶天气适应性优异，适合全年运营，包括台风季节和高纬度冬季航线')
            recommendations.append('建议在台风季节选择避风航线，充分利用船舶性能优势')
        elif speed_reduction <= 30:  # 天气适应性较好
            recommendations.append('船舶天气适应性良好，建议在台风季节和高纬度冬季选择避风航线')
            recommendations.append('可考虑季节性航线调整，在恶劣天气期选择替代航线')
        elif speed_reduction <= 40:  # 天气适应性一般
            recommendations.append('船舶天气适应性一般，建议在台风季节和高纬度冬季选择避风航线')
            recommendations.append('建议在好天气期选择主要航线，恶劣天气期选择避风航线')
        else:  # 天气适应性差
            recommendations.append('船舶天气适应性较差，建议在台风季节和高纬度冬季选择避风航线')
            recommendations.append('建议在好天气期运营，恶劣天气期考虑停航或避风')
    
    # 2. 基于船型的季节性建议
    if '集装箱' in vessel_type:
        recommendations.append('集装箱船对时间要求严格，建议在台风季节选择避风航线，保持准班率')
        recommendations.append('建议在冬季高纬度航线选择避风航线，确保货物安全')
    elif '干散货' in vessel_type:
        recommendations.append('干散货船对时间要求相对宽松，建议在台风季节选择避风航线')
        recommendations.append('建议在冬季高纬度航线选择避风航线，避免冰冻风险')
    elif '油轮' in vessel_type or '液体散货' in vessel_type:
        recommendations.append('油轮对安全要求极高，建议在台风季节选择避风航线，避免危险品运输风险')
        recommendations.append('建议在冬季高纬度航线选择避风航线，确保运输安全')
    elif 'LNG' in vessel_type or '液化气' in vessel_type:
        recommendations.append('LNG船对安全要求极高，建议在台风季节选择避风航线，避免危险品运输风险')
        recommendations.append('建议在冬季高纬度航线选择避风航线，确保运输安全')
    
    # 3. 基于载重吨位的季节性建议
    if dwt > 0:
        if dwt >= 100000:  # 大型船舶
            recommendations.append('大型船舶对天气条件敏感，建议在台风季节选择避风航线')
            recommendations.append('建议在冬季高纬度航线选择避风航线，避免冰冻风险')
        elif dwt >= 50000:  # 中型船舶
            recommendations.append('中型船舶适应性较好，建议在台风季节选择避风航线')
            recommendations.append('建议在冬季高纬度航线选择避风航线，确保运营安全')
        else:  # 小型船舶
            recommendations.append('小型船舶灵活性较高，建议在台风季节选择避风航线')
            recommendations.append('建议在冬季高纬度航线选择避风航线，确保运营安全')
    
    # 4. 季节性具体建议
    # 春季（3-5月）
    recommendations.append('春季天气相对稳定，建议充分利用好天气期，选择最优航线')
    recommendations.append('春季是航线优化的最佳时期，建议进行航线评估和调整')
    
    # 夏季（6-8月）
    recommendations.append('夏季台风频发，建议建立台风预警机制，及时调整航线')
    recommendations.append('建议在台风季节选择避风航线，确保船舶和货物安全')
    
    # 秋季（9-11月）
    recommendations.append('秋季天气相对稳定，建议充分利用好天气期，选择最优航线')
    recommendations.append('秋季是航线优化的最佳时期，建议进行航线评估和调整')
    
    # 冬季（12-2月）
    recommendations.append('冬季高纬度航线存在冰冻风险，建议选择避风航线')
    recommendations.append('建议在冬季选择避风航线，确保船舶和货物安全')
    
    # 5. 通用季节性建议
    recommendations.append('建议建立季节性航线数据库，根据天气条件选择最优航线')
    recommendations.append('建议与气象部门合作，获取准确的季节性天气预报信息')
    recommendations.append('建议建立季节性航线风险评估体系，定期评估和调整航线')
    
    return recommendations
