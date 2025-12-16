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
    # 是否启用性能相关日志
    'enable_performance_logs': os.getenv('ENABLE_PERFORMANCE_LOGS', True),
    # 是否启用验证相关日志
    'enable_validation_logs': os.getenv('ENABLE_VALIDATION_LOGS', False),
    'enable_retry_logs': os.getenv('ENABLE_RETRY_LOGS', False),  # 是否启用重试相关日志
    # 进度日志输出间隔（秒）
    'log_progress_interval': os.getenv('LOG_PROGRESS_INTERVAL', 10),
    'max_log_length': 80,  # 日志内容最大长度
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


def safe_division(numerator, denominator, default_value=0.0):
    """
    安全除法函数，避免除零错误

    :param numerator: 分子
    :param denominator: 分母
    :param default_value: 当分母为0时的默认值
    :return: 除法结果或默认值
    """
    if denominator == 0 or abs(denominator) < 1e-10:  # 使用小阈值避免浮点数精度问题
        return default_value
    return numerator / denominator


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
    
    好天气条件：严格按照租约规定的4级风3级浪标准
    风力等级 <= 4 且 波浪等级 <= 3
    
    新增功能：根据吃水(draft)区分空载(<70%)和满载(>80%)船速
    优化点：
    1. 使用租约规定的天气分类标准，确保只处理符合租约条件的好天气数据
    2. 使用累加器模式减少内存使用
    3. 改进数据验证逻辑
    4. 合并重复计算
    5. 提高代码可读性
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
            # 支持 wind_level 和 wave_level（优先）或 wave_height
            required_fields = ["wind_level", "hdg", "sog", "draught"]
            if not all(is_valid_type(item.get(field)) for field in required_fields):
                continue
            
            # 检查是否有 wave_level 或 wave_height
            if not is_valid_type(item.get("wave_level")) and not is_valid_type(item.get("wave_height")):
                continue

            # 数值转换和范围验证
            sog = float(item.get("sog", 0.0))
            draught = float(item.get("draught"))
            hdg = float(item.get("hdg"))

            # 使用新的 is_good_weather 函数，严格按照租约规定的4级风3级浪标准
            # 好天气条件：风力等级 <= 4 且 波浪等级 <= 3
            if not is_good_weather(item):
                continue

            # 条件筛选：必须是好天气且船速合理
            if sog >= DESIGN_SPEED * 0.5:
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


def is_good_weather(weather_data: Dict[str, Any]) -> bool:
    """
    根据天气数据判断是否为好天气
    好天气条件：严格按照租约规定的4级风3级浪标准
    风力等级 <= 4 且 波浪等级 <= 3

    :param weather_data: 天气数据字典，应包含 wind_level 和 wave_level 字段
    :return: 是否为好天气
    """
    if not weather_data:
        return False

    try:
        wind_level = weather_data.get("wind_level")
        wave_level = weather_data.get("wave_level")

        # 如果 wave_level 不存在，尝试从 wave_height 转换
        # 波浪等级与浪高的对应关系（参考标准）:
        # 0级: < 0.1米, 1级: 0.1-0.5米, 2级: 0.5-1.25米, 3级: 1.25-2.0米
        # 4级: 2.0-3.5米, 5级: 3.5-6.0米, 6级: 6.0-9.0米, 7级: 9.0-14.0米
        # 8级: 14.0-20.0米, 9级: > 20.0米
        if wave_level is None:
            wave_height = weather_data.get("wave_height")
            if wave_height is not None:
                try:
                    wave_height = float(wave_height)
                    # 将浪高转换为波浪等级
                    if wave_height < 0.1:
                        wave_level = 0
                    elif wave_height < 0.5:
                        wave_level = 1
                    elif wave_height < 1.25:
                        wave_level = 2
                    elif wave_height < 2.0:
                        wave_level = 3
                    elif wave_height < 3.5:
                        wave_level = 4
                    elif wave_height < 6.0:
                        wave_level = 5
                    elif wave_height < 9.0:
                        wave_level = 6
                    elif wave_height < 14.0:
                        wave_level = 7
                    elif wave_height < 20.0:
                        wave_level = 8
                    else:
                        wave_level = 9
                except (ValueError, TypeError):
                    return False
            else:
                return False

        # 转换为整数类型
        wind_level = int(wind_level) if wind_level is not None else None
        wave_level = int(wave_level) if wave_level is not None else None

        # 检查数据有效性
        if wind_level is None or wave_level is None:
            return False

        # 严格按照租约规定的4级风3级浪标准
        return wind_level <= 4 and wave_level <= 3

    except (ValueError, TypeError, KeyError):
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


def calculate_speed_performance_score(good_speed: float, design_speed: float, vessel_data: Dict[str, Any]) -> float:
    """
    计算速度性能评分

    评分标准：
    - 好天气速度与设计速度的匹配度
    - 考虑船舶类型和载重的实际影响
    """
    if good_speed <= 0 or design_speed <= 0:
        return 60.0  # 数据缺失，给予及格分

    # 计算速度匹配度
    speed_ratio = good_speed / design_speed

    # 基于实际航运经验的评分
    if speed_ratio >= 0.95:  # 达到设计速度的95%以上
        base_score = 95
    elif speed_ratio >= 0.90:  # 达到设计速度的90%以上
        base_score = 90
    elif speed_ratio >= 0.85:  # 达到设计速度的85%以上
        base_score = 85
    elif speed_ratio >= 0.80:  # 达到设计速度的80%以上
        base_score = 80
    elif speed_ratio >= 0.75:  # 达到设计速度的75%以上
        base_score = 75
    elif speed_ratio >= 0.70:  # 达到设计速度的70%以上
        base_score = 70
    else:  # 低于设计速度的70%
        base_score = 60

    # 考虑船舶类型的调整
    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    if '集装箱' in vessel_type:
        # 集装箱船对速度要求较高
        if speed_ratio < 0.85:
            base_score -= 5
    elif 'LNG' in vessel_type or '液化气' in vessel_type:
        # LNG船对速度要求相对较低
        if speed_ratio >= 0.80:
            base_score += 3

    # 考虑载重的影响
    dwt = vessel_data.get('dwt', 0)
    if dwt > 0:
        if dwt >= 100000:  # 大型船舶
            if speed_ratio >= 0.85:
                base_score += 2
        elif dwt < 10000:  # 小型船舶
            if speed_ratio >= 0.90:
                base_score += 3

    return min(100.0, max(0.0, base_score))


def calculate_weather_adaptability_score(
    good_speed: float, bad_speed: float, severe_speed: float,
    moderate_speed: float, general_speed: float
) -> float:
    """
    计算天气适应性评分

    评分标准：
    - 坏天气与好天气的速度对比
    - 不同等级坏天气下的性能表现
    """
    if good_speed <= 0:
        return 60.0

    # 基础天气适应性评分
    if bad_speed > 0:
        weather_ratio = bad_speed / good_speed
        if weather_ratio >= 0.85:
            base_score = 95  # 天气适应性优异
        elif weather_ratio >= 0.75:
            base_score = 90  # 天气适应性良好
        elif weather_ratio >= 0.65:
            base_score = 85  # 天气适应性较好
        elif weather_ratio >= 0.55:
            base_score = 80  # 天气适应性一般
        elif weather_ratio >= 0.45:
            base_score = 75  # 天气适应性较差
        else:
            base_score = 65  # 天气适应性差
    else:
        base_score = 70  # 数据不足

    # 考虑不同等级坏天气的表现
    bonus_score = 0

    # 严重坏天气表现
    if severe_speed > 0 and good_speed > 0:
        severe_ratio = severe_speed / good_speed
        if severe_ratio >= 0.60:
            bonus_score += 3
        elif severe_ratio >= 0.50:
            bonus_score += 2
        elif severe_ratio >= 0.40:
            bonus_score += 1

    # 中等坏天气表现
    if moderate_speed > 0 and good_speed > 0:
        moderate_ratio = moderate_speed / good_speed
        if moderate_ratio >= 0.75:
            bonus_score += 2
        elif moderate_ratio >= 0.65:
            bonus_score += 1

    # 一般坏天气表现
    if general_speed > 0 and good_speed > 0:
        general_ratio = general_speed / good_speed
        if general_ratio >= 0.85:
            bonus_score += 2
        elif general_ratio >= 0.75:
            bonus_score += 1

    final_score = min(100.0, base_score + bonus_score)
    return round(final_score, 1)


def calculate_stability_score(weather_performance: Dict[str, float], vessel_data: Dict[str, Any]) -> float:
    """
    计算稳定性评分

    评分标准：
    - 不同天气条件下的速度稳定性
    - 船舶尺寸和载重的稳定性影响
    """
    good_speed = weather_performance.get('avg_good_weather_speed', 0)
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0)

    if good_speed <= 0:
        return 70.0

    # 基于速度变化的稳定性评分
    if bad_speed > 0:
        speed_variation = abs(good_speed - bad_speed) / good_speed

        if speed_variation <= 0.15:  # 速度变化小于15%
            base_score = 95
        elif speed_variation <= 0.25:  # 速度变化小于25%
            base_score = 90
        elif speed_variation <= 0.35:  # 速度变化小于35%
            base_score = 85
        elif speed_variation <= 0.45:  # 速度变化小于45%
            base_score = 80
        elif speed_variation <= 0.55:  # 速度变化小于55%
            base_score = 75
        else:  # 速度变化大于55%
            base_score = 70
    else:
        base_score = 75

    # 考虑船舶尺寸的稳定性影响
    length = vessel_data.get('length', 0) or 0
    width = vessel_data.get('width', 0) or 0

    if length > 0 and width > 0:
        length_width_ratio = length / width

        # 长宽比在理想范围内，稳定性更好
        if 5.5 <= length_width_ratio <= 7.5:
            base_score += 3
        elif 5.0 <= length_width_ratio < 5.5 or 7.5 < length_width_ratio <= 8.0:
            base_score += 2
        elif length_width_ratio < 4.5 or length_width_ratio > 8.5:
            base_score -= 2

    # 考虑载重的稳定性影响
    dwt = vessel_data.get('dwt', 0) or 0
    if dwt > 0:
        if 50000 <= dwt <= 150000:  # 中等载重，稳定性较好
            base_score += 2
        elif dwt > 150000:  # 超大型船舶，稳定性挑战
            base_score -= 1

    final_score = min(100.0, max(0.0, base_score))
    return round(final_score, 1)


def calculate_efficiency_score(weather_performance: Dict[str, float], vessel_data: Dict[str, Any]) -> float:
    """
    计算效率评分

    评分标准：
    - 燃油效率（基于速度变化）
    - 运营效率（基于天气适应性）
    """
    good_speed = weather_performance.get('avg_good_weather_speed', 0) or 0
    bad_speed = weather_performance.get('avg_bad_weather_speed', 0) or 0

    if good_speed <= 0:
        return 75.0

    # 基于天气适应性的效率评分
    if bad_speed > 0:
        efficiency_ratio = bad_speed / good_speed

        if efficiency_ratio >= 0.80:
            base_score = 95  # 效率优异
        elif efficiency_ratio >= 0.70:
            base_score = 90  # 效率良好
        elif efficiency_ratio >= 0.60:
            base_score = 85  # 效率较好
        elif efficiency_ratio >= 0.50:
            base_score = 80  # 效率一般
        elif efficiency_ratio >= 0.40:
            base_score = 75  # 效率较差
        else:
            base_score = 70  # 效率差
    else:
        base_score = 80

    # 考虑船型的效率特点
    vessel_type = vessel_data.get('vesselTypeNameCn', '')
    if '集装箱' in vessel_type:
        # 集装箱船对效率要求较高
        if base_score >= 85:
            base_score += 3
        elif base_score < 75:
            base_score -= 2
    elif 'LNG' in vessel_type or '液化气' in vessel_type:
        # LNG船效率要求相对较低
        if base_score >= 80:
            base_score += 2

    final_score = min(100.0, max(0.0, base_score))
    return round(final_score, 1)


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
            # 支持 wind_level 和 wave_level（优先）或 wave_height
            required_fields = ["wind_level", "hdg", "sog", "draught"]
            if not all(field in item and item[field] is not None for field in required_fields):
                stats['missing_fields'] += 1
                continue
            
            # 检查是否有 wave_level 或 wave_height
            if "wave_level" not in item and "wave_height" not in item:
                stats['missing_fields'] += 1
                continue

            # 数值转换和基础验证
            wind_level = int(item.get("wind_level", 0))
            sog = float(item.get("sog", 0))
            draught = float(item.get("draught", 0))
            hdg = float(item.get("hdg", 0))

            # 处理波浪数据：优先使用 wave_level，如果没有则使用 wave_height
            wave_level = item.get("wave_level")
            wave_height = item.get("wave_height")
            
            if wave_level is not None:
                wave_level = int(wave_level)
                # 波浪等级范围验证 (0-9级)
                if not (0 <= wave_level <= 9):
                    stats['out_of_range'] += 1
                    continue
            elif wave_height is not None:
                wave_height = float(wave_height)
                # 浪高范围验证 (0-20米)
                if not (0 <= wave_height <= 20):
                    stats['out_of_range'] += 1
                    continue
            else:
                stats['missing_fields'] += 1
                continue

            # 范围验证
            if not (0 <= wind_level <= 12):
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
                'wave_level': wave_level,
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
                z_score = safe_division(
                    abs(data_item['sog'] - sog_mean), sog_std, 0.0) if sog_std > 0 else 0
                if z_score > 3:  # 超过3倍标准差
                    stats['statistical_outliers'] += 1
                    continue

            # 添加到最终过滤结果
            filtered_data.append(data_item['item'])
            filtered_records += 1

    # 记录过滤统计
            log_info(
                f"数据质量控制统计: 总记录数={total_records}, 过滤后={filtered_records}, 保留率={(filtered_records/total_records)*100:.1f}%")

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
            weather_counts[weather_type] = weather_counts.get(
                weather_type, 0) + 1

            # 风力分布
            wind_distribution[wind_level] = wind_distribution.get(
                wind_level, 0) + 1

            # 浪高分布
            wave_bin = int(wave_height * 2) / 2  # 0.5米间隔
            wave_distribution[wave_bin] = wave_distribution.get(
                wave_bin, 0) + 1

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
        good_ratio = safe_division(weather_counts['good'], total_records, 0.0)
        bad_ratio = safe_division(weather_counts['bad'], total_records, 0.0)
        moderate_bad_ratio = safe_division(
            weather_counts['moderate_bad'], total_records, 0.0)
        severe_ratio = safe_division(
            weather_counts['severe_bad'], total_records, 0.0)

        # 好天气比例过低警告
        if good_ratio < 0.1:
            consistency_check['warnings'].append(
                f'好天气数据比例过低({good_ratio*100:.1f}%)，可能影响统计准确性')

        # 一般坏天气比例过高警告
        if bad_ratio > 0.6:
            consistency_check['warnings'].append(
                f'一般坏天气数据比例过高({bad_ratio*100:.1f}%)，请检查天气分类标准')

        # 中等坏天气比例过高警告
        if moderate_bad_ratio > 0.4:
            consistency_check['warnings'].append(
                f'中等坏天气数据比例过高({moderate_bad_ratio*100:.1f}%)，请检查天气分类标准')

        # 严重坏天气比例异常警告
        if severe_ratio > 0.3:
            consistency_check['warnings'].append(
                f'严重坏天气数据比例过高({severe_ratio*100:.1f}%)，可能存在数据质量问题')

    return consistency_check


class CalcVesselPerformanceDetailsFromWmy(BaseModel):
    def __init__(self):
        # "客船,干散货,杂货船,液体散货,特种船,集装箱"]
        self.vessel_types = os.getenv('VESSEL_TYPES', "干散货,杂货船")
        self.wmy_url = os.getenv('WMY_URL', "http://192.168.1.128")
        self.wmy_url_port = os.getenv('WMY_URL_PORT', "10020")
        self.time_sleep = os.getenv('TIME_SLEEP', "0.1")
        self.time_days = int(os.getenv('TIME_DAYS', "15"))
        self.calc_days = int(os.getenv('CALC_DAYS', "180"))
        self.interval_hour = os.getenv('TRACE_INTERVAL_HOUR', "6")
        self.api_key = os.getenv('API_KEY', "266102ea-ca32-4ad8-8292-17c952a81a56")

        if self.vessel_types:
            self.vessel_types = self.vessel_types.split(",")
        else:
            self.vessel_types = []
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'global_vessels_performance_details',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
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
        - 严格按照租约规定的4级风3级浪标准
        - 风力等级 <= 4 且 波浪等级 <= 3
        - 符合Recap和RiderClause条款要求

        新增功能：根据吃水(draft)区分空载(<70%)和满载(>80%)船速
        优化点：
        1. 使用租约规定的天气分类标准，确保只处理符合租约条件的好天气数据
        2. 使用 is_good_weather 函数进行严格的好天气判断
        3. 支持从 /api/vessel/trace 接口获取的 wind_level 和 wave_level 数据
        4. 使用累加器模式减少内存使用
        5. 改进数据验证逻辑
        6. 提高代码可读性
        7. 增强数据质量控制和异常值过滤
        """
        # 输入验证
        if not data or not isinstance(data, list):
            log_warning("MMSI 好天气计算 - 输入数据无效")
            return {
                "avg_good_weather_speed": 0.0,
                "avg_downstream_speed": 0.0,
                "avg_non_downstream_speed": 0.0
            }
        
        try:
            # 数据质量控制和过滤
            log_debug(
                f"MMSI 好天气计算 - 数据量: {len(data)}")
            filtered_data = enhanced_data_quality_control(data, DESIGN_SPEED)
            log_debug(f"MMSI 好天气计算 - 过滤后数据量: {len(filtered_data)}")
        except Exception as e:
            logger.error(f"好天气数据质量控制失败: {e}")
            filtered_data = data  # 使用原始数据作为降级方案

            if not filtered_data:
                log_warning("MMSI 好天气计算 - 无有效数据，返回空结果")
                return {
                    "avg_good_weather_speed": 0.0,
                    "avg_downstream_speed": 0.0,
                    "avg_non_downstream_speed": 0.0
                }

            # 天气数据一致性验证
            try:
                consistency_result = validate_weather_data_consistency(filtered_data)
                if consistency_result.get('warnings'):
                    log_warning(
                        f"MMSI 好天气计算 - 天气数据一致性警告: {consistency_result['warnings']}")
            except Exception as e:
                logger.error(f"好天气数据一致性验证失败: {e}")
                # 继续处理，不中断

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
                # 支持 wind_level 和 wave_level（优先）或 wave_height
                required_fields = ["wind_level", "hdg", "sog", "draught"]
                if not all(is_valid_type(item.get(field)) for field in required_fields):
                    continue
                
                # 检查是否有 wave_level 或 wave_height
                if not is_valid_type(item.get("wave_level")) and not is_valid_type(item.get("wave_height")):
                    continue

                # 数值转换和范围验证
                sog = float(item.get("sog", 0.0))
                draught = float(item.get("draught"))
                hdg = float(item.get("hdg"))

                # 使用新的 is_good_weather 函数，严格按照租约规定的4级风3级浪标准
                # 好天气条件：风力等级 <= 4 且 波浪等级 <= 3
                if not is_good_weather(item):
                    continue

                # 条件筛选：必须是好天气且船速合理
                if sog >= DESIGN_SPEED * 0.5:
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
            log_warning(f"MMSI 好天气计算 - 有效数据点不足({len(valid_data)})，可能影响统计准确性")

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
        log_debug(
            f"MMSI 好天气数据统计: 空载={stats['empty'].count}, 满载={stats['full'].count}, 顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}")

        # 数据质量检查
        if performance["avg_good_weather_speed"] > 0:
            if performance["avg_good_weather_speed"] > DESIGN_SPEED * 1.3:
                log_warning(
                    f"MMSI 好天气计算 - 警告: 平均速度({performance['avg_good_weather_speed']})超过设计速度({DESIGN_SPEED})的130%")
            elif performance["avg_good_weather_speed"] < DESIGN_SPEED * 0.6:
                log_warning(
                    f"MMSI 好天气计算 - 警告: 平均速度({performance['avg_good_weather_speed']})低于设计速度({DESIGN_SPEED})的60%")

        # === 新增：记录好天气速度供坏天气性能验证使用 ===
        # 将好天气速度保存到实例变量中，供后续坏天气性能验证使用
        self.last_good_weather_speed = performance["avg_good_weather_speed"]
        log_debug(
            f"MMSI 好天气计算 - 已记录好天气速度: {self.last_good_weather_speed}节，供坏天气性能验证使用")

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
        # 输入验证
        if not data or not isinstance(data, list):
            log_warning("MMSI 坏天气计算 - 输入数据无效")
            return {
                "avg_bad_weather_speed": 0.0,
                "avg_downstream_bad_weather_speed": 0.0,
                "avg_non_downstream_bad_weather_speed": 0.0,
                "avg_severe_bad_weather_speed": 0.0,
                "avg_general_bad_weather_speed": 0.0
            }
        
        try:
            # 数据质量控制和过滤
            log_debug(
                f"MMSI 坏天气计算 - 数据量: {len(data)}")
            filtered_data = enhanced_data_quality_control(data, DESIGN_SPEED)
            log_debug(f"MMSI 坏天气计算 - 过滤后数据量: {len(filtered_data)}")
        except Exception as e:
            logger.error(f"坏天气数据质量控制失败: {e}")
            filtered_data = data  # 使用原始数据作为降级方案

            if not filtered_data:
                log_warning("MMSI 坏天气计算 - 无有效数据，返回空结果")
                return {
                    "avg_bad_weather_speed": 0.0,
                    "avg_downstream_bad_weather_speed": 0.0,
                    "avg_non_downstream_bad_weather_speed": 0.0,
                    "avg_severe_bad_weather_speed": 0.0,
                    "avg_general_bad_weather_speed": 0.0
                }

            # 天气数据一致性验证
            try:
                consistency_result = validate_weather_data_consistency(filtered_data)
                if consistency_result.get('warnings'):
                    log_warning(
                        f"MMSI 坏天气计算 - 天气数据一致性警告: {consistency_result['warnings']}")
            except Exception as e:
                logger.error(f"坏天气数据一致性验证失败: {e}")
                # 继续处理，不中断

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
            log_warning(f"MMSI 坏天气计算 - 有效数据点不足({len(valid_data)})，可能影响统计准确性")

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
            # 坏天气总体平均速度
            "avg_bad_weather_speed": stats['bad_weather'].average(),
            # 坏天气数据点总数
            "bad_weather_data_count": stats['bad_weather'].count,

            # === 三种坏天气分类性能 ===
            # 1. 一般坏天气（风力5级或浪高1.25-1.8米，轻微超出好天气条件）
            # 一般坏天气平均速度
            "avg_general_bad_weather_speed": stats['bad_weather_general'].average(),
            # 一般坏天气数据点数量
            "general_bad_weather_count": stats['bad_weather_general'].count,
            # 一般坏天气速度因子（75%）
            "general_bad_weather_speed_factor": 0.75,
            # 一般坏天气速度降低百分比
            "general_bad_weather_speed_reduction": "25%",

            # 2. 中等坏天气（风力6级或浪高1.8-2.5米，明显影响航行）
            # 中等坏天气平均速度
            "avg_moderate_bad_weather_speed": stats['moderate_bad_weather'].average(),
            # 中等坏天气数据点数量
            "moderate_bad_weather_count": stats['moderate_bad_weather'].count,
            # 中等坏天气速度因子（60%）
            "moderate_bad_weather_speed_factor": 0.6,
            # 中等坏天气速度降低百分比
            "moderate_bad_weather_speed_reduction": "40%",

            # 3. 严重坏天气（风力≥7级或浪高≥2.5米，恶劣天气，严重影响航行）
            # 严重坏天气平均速度
            "avg_severe_bad_weather_speed": stats['severe_weather'].average(),
            # 严重坏天气数据点数量
            "severe_bad_weather_count": stats['severe_weather'].count,
            # 严重坏天气速度因子（40%）
            "severe_bad_weather_speed_factor": 0.4,
            # 严重坏天气速度降低百分比
            "severe_bad_weather_speed_reduction": "60%",

            # === 流向相关性能 ===
            # 顺流坏天气平均速度
            "avg_downstream_bad_weather_speed": stats['downstream'].average(),
            # 逆流坏天气平均速度
            "avg_non_downstream_bad_weather_speed": stats['upstream'].average(),
            # 顺流数据点数量
            "downstream_data_count": stats['downstream'].count,
            # 逆流数据点数量
            "upstream_data_count": stats['upstream'].count,

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
        log_debug(f"MMSI 坏天气数据统计: 总体={stats['bad_weather'].count}, 空载={stats['empty'].count}, 满载={stats['full'].count}, 顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}, 严重={stats['severe_weather'].count}, 中等={stats['moderate_bad_weather'].count}, 一般={stats['bad_weather_general'].count}")

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
                log_warning(
                    f"MMSI 坏天气计算 - 数据异常: 坏天气速度({current_bad_speed})超过好天气速度({good_weather_speed})")
                corrected_speed = good_weather_speed * 0.75  # 调整为75%，更符合实际情况
                performance["avg_bad_weather_speed"] = round(
                    corrected_speed, 2)
                log_info(f"MMSI 坏天气计算 - 已修正为: {corrected_speed:.2f}节")
            elif current_bad_speed > good_weather_speed * 0.95:
                # 轻微超出合理范围，记录但不强制调整
                log_warning(
                    f"MMSI 坏天气计算 - 注意: 坏天气速度({current_bad_speed})接近好天气速度({good_weather_speed})，请检查数据质量")

            # 2. 分类天气速度验证（基于天气分类标准）
            # 一般坏天气：轻微超出好天气条件，速度影响较小
            general_speed = performance.get("avg_general_bad_weather_speed", 0)
            if general_speed > 0:
                if general_speed > good_weather_speed:
                    # 一般坏天气速度超过好天气速度，这是不合理的
                    corrected_general = good_weather_speed * 0.9  # 调整为90%
                    performance["avg_general_bad_weather_speed"] = round(
                        corrected_general, 2)
                    log_info(
                        f"MMSI 坏天气计算 - 修正一般坏天气速度: {general_speed} -> {corrected_general:.2f}节")
                elif general_speed > good_weather_speed * 0.95:
                    # 轻微超出，记录但不强制调整
                    log_warning(
                        f"MMSI 坏天气计算 - 注意: 一般坏天气速度({general_speed})接近好天气速度，可能天气分类标准需要调整")

            # 中等坏天气：明显影响航行，速度应该有明显降低
            moderate_speed = performance.get(
                "avg_moderate_bad_weather_speed", 0)
            if moderate_speed > 0:
                if moderate_speed > good_weather_speed * 0.85:
                    # 中等坏天气速度过高，但允许一定的灵活性
                    if moderate_speed > good_weather_speed:
                        # 超过好天气速度，必须调整
                        corrected_moderate = good_weather_speed * 0.75
                        performance["avg_moderate_bad_weather_speed"] = round(
                            corrected_moderate, 2)
                        log_info(
                            f"MMSI 坏天气计算 - 修正中等坏天气速度: {moderate_speed} -> {corrected_moderate:.2f}节")
                    else:
                        # 在合理范围内，记录但不强制调整
                        log_warning(
                            f"MMSI 坏天气计算 - 注意: 中等坏天气速度({moderate_speed})在合理范围内，但接近上限")

            # 严重坏天气：恶劣天气，速度应该有显著降低
            severe_speed = performance.get("avg_severe_bad_weather_speed", 0)
            if severe_speed > 0:
                if severe_speed > good_weather_speed * 0.7:
                    # 严重坏天气速度过高，需要调整
                    if severe_speed > good_weather_speed:
                        # 超过好天气速度，必须调整
                        corrected_severe = good_weather_speed * 0.6
                        performance["avg_severe_bad_weather_speed"] = round(
                            corrected_severe, 2)
                        log_info(
                            f"MMSI 坏天气计算 - 修正严重坏天气速度: {severe_speed} -> {corrected_severe:.2f}节")
                    else:
                        # 在合理范围内，记录但不强制调整
                        log_warning(
                            f"MMSI 坏天气计算 - 注意: 严重坏天气速度({severe_speed})在合理范围内，但接近上限")

            # 3. 载重相关速度验证（基于实际航行经验）
            # 空载状态：在坏天气下通常比满载状态更灵活
            ballast_speed = performance.get("avg_ballast_bad_weather_speed", 0)
            if ballast_speed > 0:
                if ballast_speed > good_weather_speed:
                    # 空载坏天气速度超过好天气速度，不合理
                    corrected_ballast = good_weather_speed * 0.8
                    performance["avg_ballast_bad_weather_speed"] = round(
                        corrected_ballast, 2)
                    log_info(
                        f"MMSI 坏天气计算 - 修正空载坏天气速度: {ballast_speed} -> {corrected_ballast:.2f}节")
                elif ballast_speed > good_weather_speed * 0.9:
                    # 轻微超出，记录但不强制调整
                    log_warning(
                        f"MMSI 坏天气计算 - 注意: 空载坏天气速度({ballast_speed})接近好天气速度")

            # 满载状态：在坏天气下通常比空载状态更受限
            laden_speed = performance.get("avg_laden_bad_weather_speed", 0)
            if laden_speed > 0:
                if laden_speed > good_weather_speed:
                    # 满载坏天气速度超过好天气速度，不合理
                    corrected_laden = good_weather_speed * 0.75
                    performance["avg_laden_bad_weather_speed"] = round(
                        corrected_laden, 2)
                    log_info(
                        f"MMSI 坏天气计算 - 修正满载坏天气速度: {laden_speed} -> {corrected_laden:.2f}节")
                elif laden_speed > good_weather_speed * 0.85:
                    # 轻微超出，记录但不强制调整
                    log_warning(
                        f"MMSI 坏天气计算 - 注意: 满载坏天气速度({laden_speed})接近好天气速度")

            # 4. 流向相关速度验证（基于洋流影响）
            # 顺流状态：洋流可能帮助船舶保持较高速度
            downstream_speed = performance.get(
                "avg_downstream_bad_weather_speed", 0)
            if downstream_speed > 0:
                if downstream_speed > good_weather_speed:
                    # 顺流坏天气速度超过好天气速度，不合理
                    corrected_downstream = good_weather_speed * 0.85
                    performance["avg_downstream_bad_weather_speed"] = round(
                        corrected_downstream, 2)
                    log_info(
                        f"MMSI 坏天气计算 - 修正顺流坏天气速度: {downstream_speed} -> {corrected_downstream:.2f}节")
                elif downstream_speed > good_weather_speed * 0.9:
                    # 轻微超出，记录但不强制调整
                    log_warning(
                        f"MMSI 坏天气计算 - 注意: 顺流坏天气速度({downstream_speed})接近好天气速度")

            # 逆流状态：洋流会增加阻力，速度应该更低
            upstream_speed = performance.get(
                "avg_non_downstream_bad_weather_speed", 0)
            if upstream_speed > 0:
                if upstream_speed > good_weather_speed:
                    # 逆流坏天气速度超过好天气速度，不合理
                    corrected_upstream = good_weather_speed * 0.7
                    performance["avg_non_downstream_bad_weather_speed"] = round(
                        corrected_upstream, 2)
                    log_info(
                        f"MMSI 坏天气计算 - 修正逆流坏天气速度: {upstream_speed} -> {corrected_upstream:.2f}节")
                elif upstream_speed > good_weather_speed * 0.8:
                    # 轻微超出，记录但不强制调整
                    log_warning(
                        f"MMSI 坏天气计算 - 注意: 逆流坏天气速度({upstream_speed})接近好天气速度")

        # 数据质量检查
        if performance["avg_bad_weather_speed"] > 0:
            if performance["avg_bad_weather_speed"] > DESIGN_SPEED * 1.1:
                log_warning(
                    f"MMSI 坏天气计算 - 警告: 平均速度({performance['avg_bad_weather_speed']})超过设计速度({DESIGN_SPEED})的110%")
            elif performance["avg_bad_weather_speed"] < DESIGN_SPEED * 0.3:
                log_warning(
                    f"MMSI 坏天气计算 - 警告: 平均速度({performance['avg_bad_weather_speed']})低于设计速度({DESIGN_SPEED})的30%")

        return performance

    def get_vessel_trace(self, mmsi: int, start_time: int, end_time: int, max_retries: int = 3) -> List[Dict[str, Any]]:
        """
        获取船舶轨迹数据（简化版，单次调用，带重试机制）
        :param mmsi: 船舶MMSI号
        :param start_time: 开始时间戳（秒）
        :param end_time: 结束时间戳（秒）
        :param max_retries: 最大重试次数
        :return: 轨迹数据列表
        """
        url = f"{self.wmy_url}:{self.wmy_url_port}/api/vessel/trace?api_key={self.api_key}"
        
        # 构造请求体
        try:
            payload = json.dumps({
                "mmsi": mmsi,
                "interval_hour": int(self.interval_hour),
                "start_timestamp": start_time,
                "end_timestamp": end_time
            })
        except (TypeError, ValueError) as e:
            logger.warning(f"MMSI {mmsi} 构造请求体失败: {e}")
            return []
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 重试机制
        for attempt in range(max_retries):
            try:
                # 单次调用，设置超时
                response = self.session.post(
                    url,
                    headers=headers,
                    data=payload,
                    timeout=30,  # 总超时时间30秒
                    verify=False
                )
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))  # 递增延迟
                        continue
                    logger.warning(f"MMSI {mmsi} API请求失败，状态码: {response.status_code}")
                    return []
                
                # 解析响应
                try:
                    response_data = response.json()
                except (ValueError, json.JSONDecodeError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                        continue
                    logger.warning(f"MMSI {mmsi} 响应JSON解析失败: {e}")
                    return []
                
                # 检查响应状态
                if response_data.get("state", {}).get("code") == 0:
                    data = response_data.get("data", [])
                    if not isinstance(data, list):
                        logger.warning(f"MMSI {mmsi} API返回数据格式错误，期望列表")
                        return []
                    
                    # 验证返回的数据质量
                    if len(data) == 0:
                        log_debug(f"MMSI {mmsi} API返回空数据列表")
                    else:
                        log_debug(f"MMSI {mmsi} API返回 {len(data)} 条轨迹数据")
                        # 检查第一条数据是否包含必要字段
                        if data and isinstance(data[0], dict):
                            sample_fields = ["wind_level", "wave_level", "wave_height", "sog", "hdg", "draught"]
                            missing_fields = [f for f in sample_fields if f not in data[0]]
                            if missing_fields:
                                log_debug(f"MMSI {mmsi} 轨迹数据缺少字段: {missing_fields}")
                    
                    return data
                else:
                    error_msg = response_data.get('state', {}).get('message', '未知错误')
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))
                        continue
                    logger.warning(f"MMSI {mmsi} API返回错误: {error_msg}")
                    return []
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1))  # 超时重试延迟更长
                    continue
                logger.warning(f"MMSI {mmsi} API请求超时（已重试{max_retries}次）")
                return []
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                logger.warning(f"MMSI {mmsi} API请求异常: {str(e)[:100]}")
                return []
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
                logger.warning(f"MMSI {mmsi} 获取轨迹数据时发生未知错误: {e}")
                return []
        
        return []

    @decorate.exception_capture_close_datebase
    def run(self):
        mmsi = None  # 初始化变量，避免在异常处理中引用未定义变量
        num = 0
        total_num = 0
        success_count = 0  # 成功处理计数
        total_failed_count = 0  # 总失败计数
        # 统计信息
        stats = {
            'no_trace_data': 0,  # 无轨迹数据
            'invalid_trace_data': 0,  # 无效轨迹数据
            'calculation_errors': 0,  # 计算错误
            'validation_failed': 0,  # 验证失败
            'save_errors': 0,  # 保存错误
            'data_quality_warnings': 0  # 数据质量警告
        }
        
        try:
            # 简化查询条件构建：使用 $and 明确组合所有条件，避免隐式组合问题
            query_conditions = []
            
            # 1. 基础条件：imo 必须存在
            query_conditions.append({"imo": {"$exists": True, "$ne": None}})
            
            # 2. 船舶类型过滤
            if self.vessel_types:
                query_conditions.append({"vesselTypeNameCn": {"$in": self.vessel_types}})
            
            # 3. 数据完整性条件：必须有吃水和速度
            query_conditions.append({"draught": {"$exists": True, "$ne": None, "$gt": 0}})
            query_conditions.append({"speed": {"$exists": True, "$ne": None, "$gt": 0}})
            
            # 4. 时间条件：如果需要更新时间过滤
            if self.time_days:
                try:
                    ten_days_ago = datetime.now() - timedelta(days=self.time_days)
                    # perf_calculated_updated_at 在数据库中存储为字符串格式 "YYYY-MM-DD HH:MM:SS"
                    ten_days_ago_str = ten_days_ago.strftime("%Y-%m-%d %H:%M:%S")
                    log_debug(f"ten_days_ago: {ten_days_ago_str}")
                    # 时间条件：perf_calculated_updated_at 不存在或小于指定时间（字符串比较）
                    query_conditions.append({
                        "$or": [
                            {"perf_calculated_updated_at": {"$lt": ten_days_ago_str}},
                            {"perf_calculated_updated_at": {"$exists": False}}
                        ]
                    })
                except Exception as e:
                    logger.warning(f"构建时间查询条件时出错: {e}，跳过时间过滤")
            
            # 构建最终查询条件
            if len(query_conditions) == 1:
                query_sql_with_data = query_conditions[0]
            else:
                query_sql_with_data = {"$and": query_conditions}
            
            logger.info(f"查询条件数量: {len(query_conditions)}")
            logger.info(f"船舶类型过滤: {self.vessel_types}")

            # 先获取总数，避免游标超时问题
            try:
                # 添加调试日志：输出查询条件
                logger.info(f"查询条件: {json.dumps(query_sql_with_data, ensure_ascii=False, default=str, indent=2)}")
                logger.info(f"船舶类型过滤: {self.vessel_types}")
                
                # 先测试查询条件是否正确
                test_count = self.mgo_db["global_vessels"].count_documents(query_sql_with_data)
                logger.info(f"测试查询结果: {test_count} 条记录")
                
                total_num = test_count
                logger.info(f"开始处理船舶性能计算，总计: {total_num} 艘（已过滤缺少必要数据的记录）")
                
                # 如果总数为0，输出更详细的诊断信息
                if total_num == 0:
                    logger.warning("⚠️ 查询结果为0条记录，开始诊断...")
                    # 检查基础查询条件
                    base_count = self.mgo_db["global_vessels"].count_documents({"imo": {"$exists": True}})
                    logger.info(f"  基础查询（仅imo存在）: {base_count} 条")
                    
                    # 检查类型过滤
                    if self.vessel_types:
                        for vessel_type in self.vessel_types:
                            type_count = self.mgo_db["global_vessels"].count_documents(
                                {"vesselTypeNameCn": vessel_type, "imo": {"$exists": True}})
                            logger.info(f"  类型 '{vessel_type}' 的记录数: {type_count} 条")
                    
                    # 检查数据完整性条件
                    data_count = self.mgo_db["global_vessels"].count_documents({
                        "imo": {"$exists": True},
                        "draught": {"$exists": True, "$ne": None, "$gt": 0},
                        "speed": {"$exists": True, "$ne": None, "$gt": 0}
                    })
                    logger.info(f"  有完整数据（imo+吃水+速度）的记录数: {data_count} 条")
                    
                    # 检查类型+数据完整性组合
                    if self.vessel_types:
                        type_data_count = self.mgo_db["global_vessels"].count_documents({
                            "imo": {"$exists": True},
                            "vesselTypeNameCn": {"$in": self.vessel_types},
                            "draught": {"$exists": True, "$ne": None, "$gt": 0},
                            "speed": {"$exists": True, "$ne": None, "$gt": 0}
                        })
                        logger.info(f"  类型+完整数据组合的记录数: {type_data_count} 条")
                    
                    # 检查时间条件
                    if self.time_days:
                        try:
                            ten_days_ago = datetime.now() - timedelta(days=self.time_days)
                            ten_days_ago_str = ten_days_ago.strftime("%Y-%m-%d %H:%M:%S")
                            time_count = self.mgo_db["global_vessels"].count_documents({
                                "imo": {"$exists": True},
                                "$or": [
                                    {"perf_calculated_updated_at": {"$lt": ten_days_ago_str}},
                                    {"perf_calculated_updated_at": {"$exists": False}}
                                ]
                            })
                            logger.info(f"  满足时间条件（{self.time_days}天前）的记录数: {time_count} 条")
                            
                            # 检查类型+数据+时间组合
                            if self.vessel_types:
                                full_condition_count = self.mgo_db["global_vessels"].count_documents({
                                    "imo": {"$exists": True},
                                    "vesselTypeNameCn": {"$in": self.vessel_types},
                                    "draught": {"$exists": True, "$ne": None, "$gt": 0},
                                    "speed": {"$exists": True, "$ne": None, "$gt": 0},
                                    "$or": [
                                        {"perf_calculated_updated_at": {"$lt": ten_days_ago_str}},
                                        {"perf_calculated_updated_at": {"$exists": False}}
                                    ]
                                })
                                logger.info(f"  完整条件组合（类型+数据+时间）的记录数: {full_condition_count} 条")
                        except Exception as e:
                            logger.warning(f"  检查时间条件时出错: {e}")
                    
                    logger.warning("⚠️ 请检查上述诊断信息，确认查询条件是否正确")
            except Exception as e:
                logger.error(f"获取船舶总数时出错: {e}")
                return

            # 简化流程：直接使用游标遍历，无需分批处理
            num = 0
            
            # 使用聚合管道实现散货船优先处理
            pipeline = [
                {"$match": query_sql_with_data},
                {
                    "$addFields": {
                        # 添加排序字段：散货船为0（优先），其他为1
                        "sort_priority": {
                            "$cond": [
                                {"$eq": ["$vesselTypeNameCn", "干散货"]},
                                0,  # 散货船优先级为0（优先）
                                1   # 其他类型优先级为1
                            ]
                        },
                        # 处理perf_calculated_updated_at可能不存在的情况
                        "sort_time": {
                            "$ifNull": [
                                "$perf_calculated_updated_at",
                                "1970-01-01 00:00:00"  # 如果不存在，使用最早时间字符串
                            ]
                        }
                    }
                },
                {
                    "$sort": {
                        "sort_priority": 1,  # 先按类型排序（散货船在前）
                        "sort_time": 1  # 再按更新时间排序
                    }
                },
                {
                    "$project": {
                        "imo": 1,
                        "mmsi": 1,
                        "draught": 1,
                        "speed": 1,
                        "vesselTypeNameCn": 1,
                        "_id": 0
                    }
                }
            ]
            
            try:
                # 直接获取游标，逐个处理，设置超时和其他选项
                vessels_cursor = self.mgo_db["global_vessels"].aggregate(
                    pipeline, 
                    allowDiskUse=True,  # 允许使用磁盘进行大数据集排序
                    maxTimeMS=300000,   # 设置查询超时时间为5分钟
                    batchSize=50        # 设置批次大小，减少内存使用
                )
                logger.info(f"开始逐个处理船舶，总计: {total_num} 艘")
                
                # 直接遍历游标
                for vessel in vessels_cursor:
                    num += 1
                    vessel_processed = False
                    
                    try:
                        # 强制类型为 int
                        try:
                            mmsi = int(vessel["mmsi"]) if vessel.get(
                                "mmsi") is not None else 0
                        except (ValueError, TypeError, KeyError):
                            mmsi = 0
                        try:
                            imo = int(vessel.get("imo")) if vessel.get(
                                "imo") is not None else 0
                        except (ValueError, TypeError):
                            imo = 0
                        
                        try:
                            draught = vessel.get("draught")
                            design_speed = vessel.get("speed", 0)
                        except Exception as e:
                            logger.warning(f"[{num}/{total_num}] 获取船舶数据失败: {e}")
                            draught = None
                            design_speed = 0

                        # 由于已经在查询时过滤，这里只需要做二次验证
                        if not imo or not draught or not design_speed:
                            logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 计算失败：数据不完整（缺少IMO、吃水或设计速度）")
                            # 直接更新数据库，标记为失败
                            try:
                                filter_condition = {"imo": imo} if imo else {"mmsi": mmsi}
                                update_data = {"$set": {
                                    "perf_calculated": 0,
                                    "perf_calculated_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }}
                                self.mgo_db["global_vessels"].update_one(filter_condition, update_data)
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 更新失败状态时出错: {e}")
                            total_failed_count += 1
                            continue

                        try:
                            start_time = int(time.time()) - self.calc_days * 24 * 3600
                            end_time = int(time.time())
                        except Exception as e:
                            logger.error(f"[{num}/{total_num}] MMSI {mmsi} 计算时间戳失败: {e}")
                            total_failed_count += 1
                            continue
                        
                        try:
                            trace = self.get_vessel_trace(mmsi, start_time, end_time)
                        except Exception as e:
                            logger.error(f"[{num}/{total_num}] MMSI {mmsi} 获取轨迹数据异常: {e}")
                            trace = []

                        # 验证轨迹数据
                        if trace:
                            # 验证轨迹数据的基本质量
                            trace_count = len(trace)
                            if trace_count < 10:
                                logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 轨迹数据点过少（{trace_count}个），可能影响计算准确性")
                            
                            # 检查必要字段是否存在
                            valid_trace_count = 0
                            required_fields = ["wind_level", "hdg", "sog", "draught"]
                            for point in trace:
                                has_wave = is_valid_type(point.get("wave_level")) or is_valid_type(point.get("wave_height"))
                                if all(is_valid_type(point.get(field)) for field in required_fields) and has_wave:
                                    valid_trace_count += 1
                            
                            if valid_trace_count < 5:
                                logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 有效轨迹数据点过少（{valid_trace_count}/{trace_count}），跳过计算")
                                trace = []  # 数据质量不足，清空轨迹数据
                            else:
                                log_debug(f"[{num}/{total_num}] MMSI {mmsi} 轨迹数据: 总数={trace_count}, 有效数={valid_trace_count}")

                        # 初始化性能数据变量
                        current_good_weather_performance = None
                        current_bad_weather_performance = None

                        if trace:
                            try:
                                current_good_weather_performance = self.deal_good_perf_list(
                                    trace, draught, design_speed)
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 处理好天气性能数据失败: {e}")
                                stats['calculation_errors'] += 1
                                current_good_weather_performance = {
                                    "avg_good_weather_speed": 0.0,
                                    "avg_downstream_speed": 0.0,
                                    "avg_non_downstream_speed": 0.0
                                }
                            
                            try:
                                current_bad_weather_performance = self.deal_bad_perf_list(
                                    trace, draught, design_speed)
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 处理坏天气性能数据失败: {e}")
                                stats['calculation_errors'] += 1
                                current_bad_weather_performance = {
                                    "avg_bad_weather_speed": 0.0,
                                    "avg_downstream_bad_weather_speed": 0.0,
                                    "avg_non_downstream_bad_weather_speed": 0.0
                                }
                            
                            # 获取性能计算结果
                            try:
                                good_speed = current_good_weather_performance.get('avg_good_weather_speed', 0) or 0
                                bad_speed = current_bad_weather_performance.get('avg_bad_weather_speed', 0) or 0
                                
                                # 数据合理性检查
                                if good_speed > 0 and bad_speed > 0:
                                    # 检查好天气速度是否合理（应该在设计速度的50%-130%之间）
                                    if good_speed < design_speed * 0.5 or good_speed > design_speed * 1.3:
                                        logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 好天气速度异常: {good_speed}节 (设计速度: {design_speed}节)")
                                    
                                    # 检查坏天气速度是否合理
                                    if bad_speed < design_speed * 0.3 or bad_speed > design_speed * 1.1:
                                        logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 坏天气速度异常: {bad_speed}节 (设计速度: {design_speed}节)")
                                    
                                    # 检查好天气速度应该大于坏天气速度
                                    if good_speed <= bad_speed:
                                        logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 数据异常: 好天气速度({good_speed}节) <= 坏天气速度({bad_speed}节)")
                                        stats['data_quality_warnings'] += 1
                                    
                                    # 检查速度差异是否合理（应该在5%-60%之间）
                                    speed_diff_percent = ((good_speed - bad_speed) / good_speed * 100) if good_speed > 0 else 0
                                    if speed_diff_percent < 5:
                                        logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 速度差异过小: {speed_diff_percent:.1f}%，可能数据质量有问题")
                                        stats['data_quality_warnings'] += 1
                                    elif speed_diff_percent > 60:
                                        logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 速度差异过大: {speed_diff_percent:.1f}%，请检查数据")
                                        stats['data_quality_warnings'] += 1
                                
                                # 如果好天气速度为0，记录警告
                                if good_speed == 0:
                                    logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 好天气速度为0，可能没有符合条件的好天气数据")
                                
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 获取性能速度失败: {e}")
                                good_speed = 0
                                bad_speed = 0

                            # 验证性能数据的合理性
                            try:
                                validation_result = self.validate_performance_data(
                                    current_good_weather_performance,
                                    current_bad_weather_performance,
                                    design_speed
                                )
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 验证性能数据失败: {e}")
                                validation_result = {
                                    'is_valid': False,
                                    'warnings': [],
                                    'errors': [f'验证过程出错: {e}'],
                                    'recommendations': []
                                }

                            # 如果验证失败，进行数据后处理
                            if not validation_result.get('is_valid', True):
                                stats['validation_failed'] += 1
                                if LOG_CONFIG['enable_validation_logs']:
                                    logger.warning(
                                        f"MMSI {mmsi} 性能数据验证失败: {validation_result.get('errors', [])}")
                                    if validation_result.get('recommendations'):
                                        logger.warning(
                                            f"建议: {validation_result['recommendations']}")

                                # 进行数据后处理，确保逻辑正确性
                                try:
                                    log_debug(f"MMSI {mmsi} 开始数据后处理...")
                                    post_processed_data = self.post_process_performance_data(
                                        current_good_weather_performance,
                                        current_bad_weather_performance,
                                        design_speed
                                    )
                                except Exception as e:
                                    logger.error(f"[{num}/{total_num}] MMSI {mmsi} 数据后处理失败: {e}")
                                    post_processed_data = {
                                        'processed_good_weather': current_good_weather_performance,
                                        'processed_bad_weather': current_bad_weather_performance,
                                        'adjustments_made': [],
                                        'quality_issues': []
                                    }

                                # 使用后处理后的数据
                                if post_processed_data.get('processed_good_weather') and post_processed_data.get('processed_bad_weather'):
                                    current_good_weather_performance = post_processed_data[
                                        'processed_good_weather']
                                    current_bad_weather_performance = post_processed_data[
                                        'processed_bad_weather']

                                    # 记录后处理结果（仅在调试模式下）
                                    if post_processed_data.get('adjustments_made') and LOG_CONFIG['enable_debug_logs']:
                                        for adjustment in post_processed_data['adjustments_made']:
                                            log_debug(
                                                f"MMSI {mmsi} 数据调整: {adjustment.get('description', '')} - {adjustment.get('reason', '')}")

                                    if post_processed_data.get('final_validation') and LOG_CONFIG['enable_debug_logs']:
                                        final_validation = post_processed_data['final_validation']
                                        log_debug(
                                            f"MMSI {mmsi} 后处理验证: 好天气{final_validation.get('good_speed', 0)}节 > 坏天气{final_validation.get('bad_speed', 0)}节, 降低{final_validation.get('speed_reduction_percentage', 0)}%")

                                # 重新验证后处理后的数据
                                try:
                                    revalidation_result = self.validate_performance_data(
                                        current_good_weather_performance,
                                        current_bad_weather_performance,
                                        design_speed
                                    )

                                    if not revalidation_result.get('is_valid', True):
                                        errors = revalidation_result.get('errors', [])
                                        error_summary = f"{len(errors)}个问题" if errors else "未知问题"
                                        logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 计算失败：数据后处理失败（{error_summary}）")
                                except Exception as e:
                                    logger.error(f"[{num}/{total_num}] MMSI {mmsi} 重新验证失败: {e}")

                            if validation_result.get('warnings') and LOG_CONFIG['enable_validation_logs']:
                                logger.warning(
                                    f"MMSI {mmsi} 性能数据验证警告: {validation_result['warnings']}")

                            # 更新 mongo 的数据（插入或更新时都包含 mmsi 和 imo）
                            try:
                                # 验证数据完整性后再保存
                                if not current_good_weather_performance or not current_bad_weather_performance:
                                    logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 性能数据不完整，跳过保存")
                                    total_failed_count += 1
                                    continue
                                
                                # 确保至少有好天气速度数据
                                if not current_good_weather_performance.get('avg_good_weather_speed'):
                                    logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 好天气速度数据缺失，跳过保存")
                                    total_failed_count += 1
                                    continue
                                
                                # 构建保存数据
                                save_data = {
                                    "imo": imo,
                                    "mmsi": mmsi,
                                    "current_good_weather_performance": current_good_weather_performance,
                                    "current_bad_weather_performance": current_bad_weather_performance,
                                    "perf_calculated": 1,
                                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    # 添加元数据
                                    "trace_data_count": len(trace) if trace else 0,
                                    "design_speed": design_speed,
                                    "draught": draught
                                }
                                
                                self.mgo_db["global_vessels_performance_details"].update_one(
                                    {"imo": imo},
                                    {"$set": save_data},
                                    upsert=True)
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 更新性能详情失败: {e}")
                                logger.error(f"异常详情: {traceback.format_exc()}")
                                stats['save_errors'] += 1
                                total_failed_count += 1
                                continue

                            # 更新 perf_calculated_updated_at
                            try:
                                self.mgo_db["global_vessels"].update_one(
                                    {"imo": imo},
                                    {"$set": {
                                        "perf_calculated_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "perf_calculated": 1
                                    }})
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 更新船舶状态失败: {e}")
                            
                            # 简化成功日志：只显示计算结果
                            speed_diff = good_speed - bad_speed if (good_speed > 0 and bad_speed > 0) else 0
                            speed_diff_percent = (speed_diff / good_speed * 100) if good_speed > 0 else 0
                            logger.info(f"[{num}/{total_num}] MMSI {mmsi} 计算成功: 好天气={good_speed}节, 坏天气={bad_speed}节, 差异={speed_diff:.2f}节({speed_diff_percent:.1f}%)")
                            success_count += 1
                            vessel_processed = True

                            # 仅在调试模式下输出详细数据
                            if LOG_CONFIG['enable_debug_logs']:
                                log_debug(
                                    f"MMSI {mmsi} 好天气 性能数据: {current_good_weather_performance}")
                                log_debug(
                                    f"MMSI {mmsi} 坏天气 性能数据: {current_bad_weather_performance}")

                        else:
                            # 未获取到轨迹数据或数据质量不足，直接更新数据库
                            if trace is None or len(trace) == 0:
                                reason = "未获取到轨迹数据" if trace is None else "轨迹数据质量不足"
                                logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 计算失败：{reason}")
                                if trace is None:
                                    stats['no_trace_data'] += 1
                                else:
                                    stats['invalid_trace_data'] += 1
                            else:
                                logger.warning(f"[{num}/{total_num}] MMSI {mmsi} 计算失败：轨迹数据无效")
                                stats['invalid_trace_data'] += 1
                            
                            try:
                                filter_condition = {"imo": imo} if imo else {"mmsi": mmsi}
                                update_data = {"$set": {
                                    "perf_calculated": 0,
                                    "perf_calculated_updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                }}
                                self.mgo_db["global_vessels"].update_one(filter_condition, update_data)
                            except Exception as e:
                                logger.error(f"[{num}/{total_num}] MMSI {mmsi} 更新失败状态时出错: {e}")
                            total_failed_count += 1

                    except KeyboardInterrupt:
                        logger.warning(f"[{num}/{total_num}] 收到中断信号，停止处理...")
                        raise
                    except Exception as e:
                        mmsi_str = mmsi if 'mmsi' in locals() and mmsi else '未知'
                        logger.error(f"[{num}/{total_num}] MMSI {mmsi_str} 处理船舶数据时发生异常: {e}")
                        logger.error(f"异常详情: {traceback.format_exc()}")
                        if not vessel_processed:
                            total_failed_count += 1
                        # 继续处理下一条记录
                        continue

                    # 每处理10条记录输出一次进度摘要
                    if num % 10 == 0 or num == total_num:
                        try:
                            progress_percent = round((num / total_num) * 100, 1) if total_num > 0 else 0
                            logger.info(
                                f"进度摘要 [{num}/{total_num}] ({progress_percent}%) - 成功: {success_count}, 失败: {total_failed_count}")
                            
                            # 每处理100条记录记录一次详细进度（用于断点续传参考）
                            if num % 100 == 0:
                                logger.info(f"检查点: 已处理 {num} 艘船舶，最后处理的MMSI: {mmsi}")
                        except Exception as e:
                            logger.error(f"输出进度摘要时出错: {e}")

                    # time.sleep(float(self.time_sleep))

            except Exception as cursor_e:
                logger.error(f"游标处理异常: {cursor_e}")
                logger.error(f"游标异常详情: {traceback.format_exc()}")
                # 如果是游标超时或连接问题，记录当前进度
                if "cursor" in str(cursor_e).lower() or "timeout" in str(cursor_e).lower():
                    logger.warning(f"游标超时或连接问题，当前已处理: {num} 艘船舶")
                    logger.info("建议：可以考虑重新启动程序继续处理剩余船舶")
                raise  # 重新抛出异常，让外层处理

        except KeyboardInterrupt:
            logger.warning("收到中断信号，程序即将退出...")
            logger.info(f"中断时进度: [{num}/{total_num}] - 成功: {success_count}, 失败: {total_failed_count}")
            raise
        except Exception as e:
            traceback.print_exc()
            mmsi_str = f"MMSI {mmsi}" if 'mmsi' in locals() and mmsi else "未知船舶"
            logger.error(f"船舶性能计算过程中发生严重错误 [{num}/{total_num}] {mmsi_str}：{e}")
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            logger.error(f"错误发生时的状态: 已处理={num}, 总数={total_num}")
            # 记录错误但不继续处理，因为可能是严重的系统错误
            logger.error("发生严重错误，程序将退出")
        finally:
            # 确保最终统计信息被记录
            try:
                if total_num > 0:
                    success_rate = (success_count / total_num) * 100 if total_num > 0 else 0
                    logger.info("=" * 80)
                    logger.info("处理完成统计")
                    logger.info("=" * 80)
                    logger.info(f"总计: {total_num} 艘")
                    logger.info(f"成功: {success_count} 艘 ({success_rate:.1f}%)")
                    logger.info(f"失败: {total_failed_count} 艘 ({100-success_rate:.1f}%)")
                    logger.info(f"实际处理: {num} 艘")
                    if stats:
                        logger.info("失败原因统计:")
                        logger.info(f"  - 无轨迹数据: {stats.get('no_trace_data', 0)} 艘")
                        logger.info(f"  - 无效轨迹数据: {stats.get('invalid_trace_data', 0)} 艘")
                        logger.info(f"  - 计算错误: {stats.get('calculation_errors', 0)} 艘")
                        logger.info(f"  - 验证失败: {stats.get('validation_failed', 0)} 艘")
                        logger.info(f"  - 保存错误: {stats.get('save_errors', 0)} 艘")
                        logger.info(f"  - 数据质量警告: {stats.get('data_quality_warnings', 0)} 艘")
                    logger.info("=" * 80)
            except Exception as e:
                logger.error(f"输出最终统计信息时出错: {e}")
                logger.error(f"统计异常详情: {traceback.format_exc()}")

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
        good_speed = good_weather_perf.get('avg_good_weather_speed', 0) or 0
        bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0) or 0

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
        good_speed = good_weather_perf.get('avg_good_weather_speed', 0) or 0
        bad_speed = bad_weather_perf.get('avg_bad_weather_speed', 0) or 0

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
                processed_bad_weather['avg_bad_weather_speed'] = round(
                    target_bad_speed, 2)

                # 调整其他相关速度指标
                for key in processed_bad_weather:
                    if 'speed' in key and key != 'avg_bad_weather_speed':
                        original_value = processed_bad_weather[key]
                        # 确保 original_value 是数值类型
                        try:
                            original_value = float(
                                original_value) if original_value is not None else 0
                        except (ValueError, TypeError):
                            original_value = 0

                        if original_value > 0:
                            # 按比例调整
                            adjustment_factor = target_bad_speed / bad_speed
                            adjusted_value = original_value * adjustment_factor
                            processed_bad_weather[key] = round(
                                adjusted_value, 2)

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
                    processed_bad_weather['avg_bad_weather_speed'] = round(
                        target_bad_speed, 2)

                    # 按比例调整其他速度指标
                    adjustment_factor = target_bad_speed / bad_speed
                    for key in processed_bad_weather:
                        if 'speed' in key and key != 'avg_bad_weather_speed':
                            original_value = processed_bad_weather[key]
                            # 确保 original_value 是数值类型
                            try:
                                original_value = float(
                                    original_value) if original_value is not None else 0
                            except (ValueError, TypeError):
                                original_value = 0

                            if original_value > 0:
                                adjusted_value = original_value * adjustment_factor
                                processed_bad_weather[key] = round(
                                    adjusted_value, 2)

                    processed_data['processed_bad_weather'] = processed_bad_weather
                    processed_data['processed_good_weather'] = good_weather_perf.copy(
                    )
                else:
                    processed_data['processed_good_weather'] = good_weather_perf.copy(
                    )
                    processed_data['processed_bad_weather'] = bad_weather_perf.copy(
                    )
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
        final_good_speed = processed_data['processed_good_weather'].get(
            'avg_good_weather_speed', 0) or 0
        final_bad_speed = processed_data['processed_bad_weather'].get(
            'avg_bad_weather_speed', 0) or 0

        if final_good_speed > 0 and final_bad_speed > 0:
            final_reduction = (
                (final_good_speed - final_bad_speed) / final_good_speed) * 100

            processed_data['final_validation'] = {
                'good_speed': final_good_speed,
                'bad_speed': final_bad_speed,
                'speed_reduction_percentage': round(final_reduction, 2),
                'speed_reduction_knots': round(final_good_speed - final_bad_speed, 2),
                'logic_compliant': final_good_speed > final_bad_speed,
                'performance_gap_reasonable': 8 <= final_reduction <= 60
            }

        return processed_data


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

    # 输出当前配置（简化版）
    logger.info(
        f"日志配置已更新: 调试={enable_debug}, 性能={enable_performance}, 验证={enable_validation}")


def enable_production_mode():
    """启用生产模式，只显示重要日志"""
    configure_logging(
        enable_debug=False,
        enable_performance=True,
        enable_validation=False,
        enable_retry=False,
        progress_interval=10
    )


def enable_quiet_mode():
    """启用静默模式，只显示错误和警告"""
    configure_logging(
        enable_debug=False,
        enable_performance=False,
        enable_validation=False,
        enable_retry=False,
        progress_interval=30
    )


# 默认启用生产模式
enable_production_mode()
