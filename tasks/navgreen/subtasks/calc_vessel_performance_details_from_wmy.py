#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymongo
from pkg.public.decorator import decorate
from pkg.public.models import BaseModel
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
        'empty_downstream': SpeedStats(), # 空载顺流
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
            is_downstream = is_sailing_downstream(float(current_u), float(current_v), hdg)
        
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
    print(f"数据统计: 空载={stats['empty'].count}, 满载={stats['full'].count}, "
          f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}")
    
    return performance


def is_sailing_downstream(u: float, v: float, ship_angle: float) -> bool:
    """
    判断船舶是否顺流航行（优化版）
    :param u: 洋流东向分量(m/s)
    :param v: 洋流北向分量(m/s)
    :param ship_angle: 船舶航向角(°)，从正北顺时针方向
    :return: 布尔值，True表示顺流，False表示逆流或横流
    """
    # 计算洋流方向角度（0°为正北，顺时针增加）
    current_angle = math.degrees(math.atan2(u, v)) % 360
    if current_angle < 0:
        current_angle += 360

    # 计算船舶航向与洋流方向的夹角差
    angle_diff = abs(ship_angle - current_angle)
    min_angle_diff = min(angle_diff, 360 - angle_diff)

    # 判断顺流条件（夹角≤45°视为顺流）
    return min_angle_diff <= 45


class CalcVesselPerformanceDetailsFromWmy(BaseModel):
    def __init__(self):
        # "客船,干散货,杂货船,液体散货,特种船,集装箱"]
        self.vessel_types = os.getenv('VESSEL_TYPES', "干散货")

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
            'empty_downstream': SpeedStats(), # 空载顺流
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
                is_downstream = is_sailing_downstream(float(current_u), float(current_v), hdg)
            
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
        print(f"数据统计: 空载={stats['empty'].count}, 满载={stats['full'].count}, "
              f"顺流={stats['downstream'].count}, 逆流={stats['upstream'].count}")
        
        return performance

    def get_vessel_trace(self, mmsi: int, start_time: int, end_time: int) -> List[Dict[str, Any]]:
        """
        获取船舶轨迹数据
        :param mmsi: 船舶MMSI号
        :param start_time: 开始时间戳（毫秒）
        :param end_time: 结束时间戳（毫秒）
        :return: 轨迹数据列表
        """
        url = "https://openapi.navgreen.cn/api/vessel/trace"
        # 构造请求体，使用当前vessel的mmsi，时间戳可根据需要调整
        data = {
            "mmsi": mmsi,
            "interval_hour": 3,
            # 这里需要将时间字符串转换为时间戳（毫秒）
            # 90天前
            "start_timestamp": start_time,
            "end_timestamp": end_time
        }
        print(data)

        response = requests.post(url, json=data, verify=False)
        response_data = response.json()
        
        # 检查响应状态
        if response_data.get("state", {}).get("code") == 0:
            return response_data.get("traces", [])
        else:
            print(f"API请求失败: {response_data.get('state', {}).get('message', '未知错误')}")
            return []

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            query_sql: Dict[str, Any] = {"mmsi": {"$exists": True}}
            if self.vessel_types:
                query_sql["vesselTypeNameCn"] = {"$in": self.vessel_types}

            if self.mgo_db is None:
                print("数据库连接失败")
                return
                
            vessels = self.mgo_db["hifleet_vessels"].find(query_sql,
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
                                                          })

            total_num = vessels.count()
            num = 0
            print(f"total_num: {total_num}")

            # 请求接口，获取轨迹气象数据和船舶轨迹数据
            for vessel in vessels:
                mmsi = vessel["mmsi"]
                mmsi = 414439000
                draught = vessel.get("draught")
                design_speed = vessel.get("speed")
                if not draught or not design_speed:
                    continue

                start_time = int(datetime.now().timestamp()
                                 * 1000) - 90 * 24 * 3600 * 1000
                end_time = int(datetime.now().timestamp() * 1000)
                trace = self.get_vessel_trace(mmsi, start_time, end_time)
                
                if trace:
                    performance = self.deal_good_perf_list(
                        trace, draught, design_speed)
                    print(f"MMSI {mmsi} 性能数据: {performance}")
                else:
                    print(f"MMSI {mmsi} 未获取到轨迹数据")

                # 测试时只处理第一条数据
                break

        except Exception as e:
            traceback.print_exc()
            print("error:", e)
        finally:
            print("运行结束")
