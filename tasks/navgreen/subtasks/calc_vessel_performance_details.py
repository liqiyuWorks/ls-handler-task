#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymongo
from pkg.public.decorator import decorate
from pkg.public.models import BaseModel
import requests
from datetime import datetime, timedelta
from datetime import timezone
from pkg.public.convert import convert_era5_wave_point, convert_era5_wind_point, convert_era5_flow_point
import math
import traceback
import os
import time
import json


def request_mmsi_details(mmsi):
    try:
        url = "https://api.navgreen.cn/api/vessel/details"

        querystring = {"mmsi": mmsi}

        payload = ""
        headers = {
            "accept": "application/json",
            "token": "NAVGREEN_ADMIN_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjE1MDAxNTMsInVzZXJuYW1lIjoiaml1ZmFuZyIsImFjY2Vzc19rZXkiOiJMUzhBOUVGMTk2NDFGQkI1Q0Q4QUI3RUZFMjVGMUE3NSIsInNlY3JldF9rZXkiOiJMUzQzQkMzRUIzNkMyMzNDRDI0QTYwN0EzRkVDQUIxOCJ9.8zYU58Mxfiu-GDpOEGva1iGzxA0Dyexw1FoGfrdIrtc",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Host": "api.navgreen.cn"
        }

        response = requests.request(
            "GET", url, headers=headers, params=querystring)
    except Exception as e:
        traceback.print_exc()

    return response.json().get("data", {}).get("data", [])


def is_valid_type(s):
    try:
        if s != "" and s != None:
            return True
    except (ValueError, TypeError):
        return False


def deal_good_perf_list(data, DESIGN_DRAFT, DESIGN_SPEED):
    """
    处理船舶数据列表，计算符合条件的平均船速（优化版）
    新增功能：根据吃水(draft)区分空载(<60%)和满载(>80%)船速
    """
    # 设计吃水深度阈值
    EMPTY_LOAD = DESIGN_DRAFT*0.7  # 60%
    FULL_LOAD = DESIGN_DRAFT*0.8   # 80%

    # 第一阶段：强化初步筛选（过滤无效值并预转换类型）
    filtered = (
        d for d in data
        if is_valid_type(d.get("wind_level"))
        and is_valid_type(d.get("wave_height"))
        and is_valid_type(d.get("hdg"))
        and is_valid_type(d.get("sog"))
        and is_valid_type(d.get("draught"))  # 新增吃水有效性检查
        and int(d.get("wind_level", 5)) <= 4
        and float(d.get("wave_height", 1.26)) <= 1.25
        and float(d.get("sog", 0.0)) >= DESIGN_SPEED*0.5
    )

    # 第二阶段：分别统计空载和满载数据
    empty_total = 0.0
    empty_count = 0
    full_total = 0.0
    full_count = 0

    sog_empty_downstream_true = []  # 新增：空载顺流航速列表
    sog_empty_downstream_false = []  # 新增：空载逆流航速列表
    sog_full_downstream_true = []  # 新增：满载顺流航速列表
    sog_full_downstream_false = []  # 新增：满载逆流航速列表
    sog_downstream_true = []  # 新增：顺流航速列表
    sog_downstream_false = []  # 新增：逆流航速列表

    for item in filtered:
        try:
            # 单次字典遍历提取所有字段（减少字典访问次数）
            draft = item.get("draught")
            speed = item.get("sog")
            hdg = item.get("hdg")
            if draft is None or speed is None or hdg is None:
                continue
            draft = float(draft)
            speed = float(speed)
            hdg = float(hdg)
            u_flow = item.get("u_flow")
            v_flow = item.get("v_flow")
            if u_flow is not None and v_flow is not None:
                if is_sailing_downstream(u_flow, v_flow, hdg):
                    sog_downstream_true.append(speed)  # 新增
                    if draft < EMPTY_LOAD:
                        sog_empty_downstream_true.append(speed)
                    elif draft > FULL_LOAD:
                        sog_full_downstream_true.append(speed)
                else:
                    sog_downstream_false.append(speed)  # 新增
                    if draft < EMPTY_LOAD:
                        sog_empty_downstream_false.append(speed)
                    elif draft > FULL_LOAD:
                        sog_full_downstream_false.append(speed)

            # 根据吃水比例分类统计
            if draft < EMPTY_LOAD:
                empty_total += speed
                empty_count += 1
            elif draft > FULL_LOAD:
                full_total += speed
                full_count += 1

        except (ValueError, KeyError) as e:
            print(f"数据异常跳过: {e}")
            continue

    # 计算各类平均速度
    avg_empty_speed = round(empty_total / empty_count,
                            2) if empty_count else 0.0
    avg_full_speed = round(full_total / full_count, 2) if full_count else 0.0
    avg_good_weather_speed = round((empty_total + full_total) / (
        empty_count + full_count), 2) if (empty_count + full_count) else 0.0

    # 新增：计算顺流/逆流的平均航速
    avg_downstream_speed = round(sum(
        sog_downstream_true) / len(sog_downstream_true), 2) if sog_downstream_true else 0.0
    avg_non_downstream_speed = round(sum(
        sog_downstream_false) / len(sog_downstream_false), 2) if sog_downstream_false else 0.0

    performance = {
        "avg_good_weather_speed": avg_good_weather_speed,
        "avg_downstream_speed": avg_downstream_speed,
        "avg_non_downstream_speed": avg_non_downstream_speed,
    }

    print("空载数：", empty_count, "，满载数：", full_count, "，顺流数：", len(
        sog_downstream_true), "，逆流数：", len(sog_downstream_false))
    if empty_count:
        performance["avg_ballast_speed"] = avg_empty_speed
        # 新增：空载顺流/逆流平均航速
        performance["avg_ballast_downstream_speed"] = round(sum(
            sog_empty_downstream_true) / len(sog_empty_downstream_true), 2) if sog_empty_downstream_true else 0.0
        performance["avg_ballast_non_downstream_speed"] = round(sum(
            sog_empty_downstream_false) / len(sog_empty_downstream_false), 2) if sog_empty_downstream_false else 0.0

    if full_count:
        performance["avg_laden_speed"] = avg_full_speed
        # 新增：满载顺流/逆流平均航速
        performance["avg_laden_downstream_speed"] = round(sum(
            sog_full_downstream_true) / len(sog_full_downstream_true), 2) if sog_full_downstream_true else 0.0
        performance["avg_laden_non_downstream_speed"] = round(sum(
            sog_full_downstream_false) / len(sog_full_downstream_false), 2) if sog_full_downstream_false else 0.0

    return performance


def deal_bad_perf_list(data, DESIGN_DRAFT, DESIGN_SPEED):
    """
    处理船舶数据列表，计算符合条件的平均船速（优化版）
    新增功能：根据吃水(draft)区分空载(<60%)和满载(>80%)船速
    """
    # 设计吃水深度阈值
    EMPTY_LOAD = DESIGN_DRAFT*0.7  # 60%
    FULL_LOAD = DESIGN_DRAFT*0.8   # 80%

    # 第一阶段：强化初步筛选（过滤无效值并预转换类型）
    filtered = (
        d for d in data
        if is_valid_type(d.get("wind_level"))
        and is_valid_type(d.get("wave_height"))
        and is_valid_type(d.get("hdg"))
        and is_valid_type(d.get("sog"))
        and is_valid_type(d.get("draught"))  # 新增吃水有效性检查
        and int(d.get("wind_level", 5)) > 4
        and float(d.get("wave_height", 1.26)) <= 1.25
        and float(d.get("sog", 0.0)) >= DESIGN_SPEED*0.5
    )

    # 第二阶段：分别统计空载和满载数据
    empty_total = 0.0
    empty_count = 0
    full_total = 0.0
    full_count = 0

    sog_empty_downstream_true = []  # 新增：空载顺流航速列表
    sog_empty_downstream_false = []  # 新增：空载逆流航速列表
    sog_full_downstream_true = []  # 新增：满载顺流航速列表
    sog_full_downstream_false = []  # 新增：满载逆流航速列表
    sog_downstream_true = []  # 新增：顺流航速列表
    sog_downstream_false = []  # 新增：逆流航速列表

    for item in filtered:
        try:
            # 单次字典遍历提取所有字段（减少字典访问次数）
            draft = item.get("draught")
            speed = item.get("sog")
            hdg = item.get("hdg")
            if draft is None or speed is None or hdg is None:
                continue
            draft = float(draft)
            speed = float(speed)
            hdg = float(hdg)
            u_flow = item.get("u_flow")
            v_flow = item.get("v_flow")
            if u_flow is not None and v_flow is not None:
                if is_sailing_downstream(u_flow, v_flow, hdg):
                    sog_downstream_true.append(speed)  # 新增
                    if draft < EMPTY_LOAD:
                        sog_empty_downstream_true.append(speed)
                    elif draft > FULL_LOAD:
                        sog_full_downstream_true.append(speed)
                else:
                    sog_downstream_false.append(speed)  # 新增
                    if draft < EMPTY_LOAD:
                        sog_empty_downstream_false.append(speed)
                    elif draft > FULL_LOAD:
                        sog_full_downstream_false.append(speed)

            # 根据吃水比例分类统计
            if draft < EMPTY_LOAD:
                empty_total += speed
                empty_count += 1
            elif draft > FULL_LOAD:
                full_total += speed
                full_count += 1

        except (ValueError, KeyError) as e:
            print(f"数据异常跳过: {e}")
            continue

    # 计算各类平均速度
    avg_empty_speed = round(empty_total / empty_count,
                            2) if empty_count else 0.0
    avg_full_speed = round(full_total / full_count, 2) if full_count else 0.0
    avg_good_weather_speed = round((empty_total + full_total) / (
        empty_count + full_count), 2) if (empty_count + full_count) else 0.0

    # 新增：计算顺流/逆流的平均航速
    avg_downstream_speed = round(sum(
        sog_downstream_true) / len(sog_downstream_true), 2) if sog_downstream_true else 0.0
    avg_non_downstream_speed = round(sum(
        sog_downstream_false) / len(sog_downstream_false), 2) if sog_downstream_false else 0.0

    performance = {
        "avg_good_weather_speed": avg_good_weather_speed,
        "avg_downstream_speed": avg_downstream_speed,
        "avg_non_downstream_speed": avg_non_downstream_speed,
    }

    print("空载数：", empty_count, "，满载数：", full_count, "，顺流数：", len(
        sog_downstream_true), "，逆流数：", len(sog_downstream_false))
    if empty_count:
        performance["avg_ballast_speed"] = avg_empty_speed
        # 新增：空载顺流/逆流平均航速
        performance["avg_ballast_downstream_speed"] = round(sum(
            sog_empty_downstream_true) / len(sog_empty_downstream_true), 2) if sog_empty_downstream_true else 0.0
        performance["avg_ballast_non_downstream_speed"] = round(sum(
            sog_empty_downstream_false) / len(sog_empty_downstream_false), 2) if sog_empty_downstream_false else 0.0

    if full_count:
        performance["avg_laden_speed"] = avg_full_speed
        # 新增：满载顺流/逆流平均航速
        performance["avg_laden_downstream_speed"] = round(sum(
            sog_full_downstream_true) / len(sog_full_downstream_true), 2) if sog_full_downstream_true else 0.0
        performance["avg_laden_non_downstream_speed"] = round(sum(
            sog_full_downstream_false) / len(sog_full_downstream_false), 2) if sog_full_downstream_false else 0.0

    return performance


def get_vessel_track(mmsi, start_time, end_time):
    """
    根据船舶 mmsi 和时间，读取船舶的航行轨迹

    Args:
        mmsi (str): 船舶的MMSI号
        start_time (str): 开始时间，格式：YYYY-MM-DD HH:MM:SS
        end_time (str): 结束时间，格式：YYYY-MM-DD HH:MM:SS

    Returns:
        dict: API返回的JSON响应
    """
    url = "https://api.navgreen.cn/api/vessel/status/track"

    params = {
        "mmsi": mmsi,
        "status": 0,
        "start_time": start_time,
        "end_time": end_time
    }

    headers = {
        "accept": "application/json",
        "token": "NAVGREEN_ADMIN_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2NjE1MDAxNTMsInVzZXJuYW1lIjoiaml1ZmFuZyIsImFjY2Vzc19rZXkiOiJMUzhBOUVGMTk2NDFGQkI1Q0Q4QUI3RUZFMjVGMUE3NSIsInNlY3JldF9rZXkiOiJMUzQzQkMzRUIzNkMyMzNDRDI0QTYwN0EzRkVDQUIxOCJ9.8zYU58Mxfiu-GDpOEGva1iGzxA0Dyexw1FoGfrdIrtc"
    }

    response = requests.get(url, params=params, headers=headers)
    track_data = response.json().get("data", {}).get("data", [])
    # 1. 解析postime为datetime，假定为北京时间
    for point in track_data:
        point["postime_dt"] = datetime.strptime(
            point.get("postime"), "%Y-%m-%d %H:%M:%S")
        # 假定原始时间为北京时间（UTC+8）
        point["postime_dt"] = point["postime_dt"].replace(
            tzinfo=timezone(timedelta(hours=8)))
    # 2. 按时间排序
    track_data.sort(key=lambda x: x["postime_dt"])
    # 3. 以1小时为间隔重采样
    resampled = []
    last_time = None
    for point in track_data:
        if last_time is None or (point["postime_dt"] - last_time).total_seconds() >= 3600:
            resampled.append(point)
            last_time = point["postime_dt"]
    # 4. 对齐到最近的3小时整点，并去重
    aligned = {}
    for point in resampled:
        dt_utc = point["postime_dt"].astimezone(timezone.utc)
        # 计算最近的3小时整点
        hour = round(dt_utc.hour / 3) * 3
        if hour == 24:
            dt_utc = dt_utc.replace(hour=0) + timedelta(days=1)
            hour = 0
        aligned_time = dt_utc.replace(
            hour=hour, minute=0, second=0, microsecond=0)
        key = aligned_time.strftime("%Y-%m-%d %H:%M:%S")
        if key not in aligned:
            aligned[key] = {
                "lon": point.get("lon"),
                "lat": point.get("lat"),
                "sog": point.get("sog"),
                "cog": point.get("cog"),
                "hdg": point.get("hdg"),
                "draught": point.get("draught"),
                "postime": key
            }
    track_data = list(aligned.values())
    track_data.sort(key=lambda x: x["postime"])  # 按时间排序
    # 修复hdg为None
    for point in track_data:
        if point.get("hdg") is None:
            if point.get("cog") is not None:
                point["hdg"] = point["cog"]
            else:
                point["hdg"] = 0
    return track_data


def handle_track_point_weather(i, ck_client):
    lon = i.get("lon")
    lat = i.get("lat")
    sog = i.get("sog")
    cog = i.get("cog")
    hdg = i.get("hdg")
    draught = i.get("draught")
    postime = i.get("postime")
    # 将时间转换为datetime对象
    print(lon, lat, sog, cog, hdg, draught, postime)

    lat_index, lon_index = convert_era5_wave_point(lat, lon)

    sql_ck = f"""
    SELECT *
    FROM shipping_history.era5_wave_0p5
    WHERE lat_index = {lat_index}
    AND lon_index = {lon_index} 
    AND history_date = toDateTime('{postime}')
    LIMIT 10
    """

    result = ck_client.query(sql_ck)
    print(result)


def batch_query_ck(client, sql_template, index_time_list, batch_size=500):
    results = []
    for i in range(0, len(index_time_list), batch_size):
        batch = index_time_list[i:i+batch_size]
        values_clause = ",\n".join(
            f"({lat},{lon},toDateTime('{postime}'))"
            for lat, lon, postime in batch
        )
        sql = sql_template.format(values=values_clause)
        results.extend(client.query(sql))
    return results


def fetch_era5_wave_for_track(track_data, ck_client, batch_size=500):
    # 1. 生成索引和时间元组，去重
    seen = set()
    index_time_list = []
    for point in track_data:
        lat = point["lat"]
        lon = point["lon"]
        postime = point["postime"]
        lat_index, lon_index = convert_era5_wave_point(lat, lon)
        key = (lat_index, lon_index, postime)
        if key not in seen:
            seen.add(key)
            index_time_list.append(key)
        point["lat_index"] = lat_index
        point["lon_index"] = lon_index

    # 2. SQL模板
    sql_template = """
    SELECT *
    FROM shipping_history.era5_wave_0p5
    WHERE (lat_index, lon_index, history_date) IN (
        {values}
    )
    """

    # 3. 分批查询
    results = batch_query_ck(ck_client, sql_template,
                             index_time_list, batch_size)

    # 4. 构建映射
    weather_map = {}
    for row in results:
        lat_index, lon_index, history_date = row[0], row[1], row[2]
        weather_map[(lat_index, lon_index, str(history_date))] = row

    # 5. 合并到track_data
    weather_keys = [
        "lat_index", "lon_index", "history_date",
        "wave_height", "wave_direction", "wave_period",
        "swell_wave_height", "swell_wave_direction", "swell_wave_period",
        "wind_wave_height", "wind_wave_direction", "wind_wave_period"
    ]
    for point in track_data:
        key = (point["lat_index"], point["lon_index"], point["postime"])
        weather = weather_map.get(key)
        if weather:
            for k, v in zip(weather_keys, weather):
                point[k] = v

    return track_data


def fetch_era5_wind_for_track(track_data, ck_client, batch_size=500):
    seen = set()
    index_time_list = []
    for point in track_data:
        lat = point["lat"]
        lon = point["lon"]
        postime = point["postime"]
        lat_index, lon_index = convert_era5_wind_point(lat, lon)
        key = (lat_index, lon_index, postime)
        if key not in seen:
            seen.add(key)
            index_time_list.append(key)
        point["wind_lat_index"] = lat_index
        point["wind_lon_index"] = lon_index

    sql_template = """
    SELECT *
    FROM shipping_history.era5_0p25
    WHERE (lat_index, lon_index, history_date) IN (
        {values}
    )
    """

    results = batch_query_ck(ck_client, sql_template,
                             index_time_list, batch_size)

    weather_map = {}
    for row in results:
        lat_index, lon_index, history_date = row[0], row[1], row[2]
        weather_map[(lat_index, lon_index, str(history_date))] = row

    weather_keys = [
        "wind_lat_index", "wind_lon_index", "wind_history_date",
        "pressure", "temperature", "u_wind", "v_wind"
    ]
    for point in track_data:
        key = (point["wind_lat_index"],
               point["wind_lon_index"], point["postime"])
        weather = weather_map.get(key)
        if weather:
            for k, v in zip(weather_keys, weather):
                point[k] = v
    return track_data


def fetch_era5_flow_for_track(track_data, ck_client, batch_size=500):
    seen = set()
    index_time_list = []
    for point in track_data:
        lat = point["lat"]
        lon = point["lon"]
        postime = point["postime"]
        lat_index, lon_index = convert_era5_flow_point(lat, lon)
        key = (lat_index, lon_index, postime)
        if key not in seen:
            seen.add(key)
            index_time_list.append(key)
        point["flow_lat_index"] = lat_index
        point["flow_lon_index"] = lon_index

    sql_template = """
    SELECT *
    FROM shipping_history.era5_flow_0p83
    WHERE (lat_index, lon_index, history_date) IN (
        {values}
    )
    """

    results = batch_query_ck(ck_client, sql_template,
                             index_time_list, batch_size)

    weather_map = {}
    for row in results:
        lat_index, lon_index, history_date = row[0], row[1], row[2]
        weather_map[(lat_index, lon_index, str(history_date))] = row

    weather_keys = [
        "flow_lat_index", "flow_lon_index", "flow_history_date",
        "u_flow", "v_flow"
    ]
    for point in track_data:
        key = (point["flow_lat_index"],
               point["flow_lon_index"], point["postime"])
        weather = weather_map.get(key)
        if weather:
            for k, v in zip(weather_keys, weather):
                point[k] = v
    return track_data


def merge_track_data(track_data, track_wave_data, track_wind_data, track_flow_data):
    # 1. 构建映射
    def build_map(data, lat_key, lon_key, time_key):
        return {
            (str(d[lat_key]), str(d[lon_key]), str(d[time_key])): d
            for d in data
        }

    wave_map = build_map(track_wave_data, "lat", "lon", "postime")
    wind_map = build_map(track_wind_data, "lat", "lon", "postime")
    flow_map = build_map(track_flow_data, "lat", "lon", "postime")

    merged = []
    for point in track_data:
        key = (str(point["lat"]), str(point["lon"]), str(point["postime"]))
        merged_point = point.copy()
        # 合并wave
        wave = wave_map.get(key)
        if wave:
            for k, v in wave.items():
                if k not in merged_point:
                    merged_point[k] = v
        # 合并wind
        wind = wind_map.get(key)
        if wind:
            for k, v in wind.items():
                if k not in merged_point:
                    merged_point[k] = v
        # 合并flow
        flow = flow_map.get(key)
        if flow:
            for k, v in flow.items():
                if k not in merged_point:
                    merged_point[k] = v
        merged.append(merged_point)
    return merged


def format_history_dates(data):
    for point in data:
        for key in ["history_date", "wind_history_date", "flow_history_date"]:
            if key in point and isinstance(point[key], datetime):
                point[key] = point[key].strftime("%Y-%m-%d %H:%M:%S")
    return data


def filter_fields(data):
    keep_keys = [
        "lon", "lat", "sog", "cog", "hdg", "draught", "postime",
        "wave_height", "wave_direction", "wave_period",
        "swell_wave_height", "swell_wave_direction", "swell_wave_period",
        "wind_wave_height", "wind_wave_direction", "wind_wave_period",
        "pressure", "temperature", "u_wind", "v_wind", "u_flow", "v_flow"
    ]
    return [
        {k: d[k] for k in keep_keys if k in d}
        for d in data
    ]


def calculate_wind_level(speed):
    if speed is None or math.isnan(speed):
        return 0
    if speed <= 0.2:
        return 0
    elif speed <= 1.5:
        return 1
    elif speed <= 3.3:
        return 2
    elif speed <= 5.4:
        return 3
    elif speed <= 7.9:
        return 4
    elif speed <= 10.7:
        return 5
    elif speed <= 13.8:
        return 6
    elif speed <= 17.1:
        return 7
    elif speed <= 20.7:
        return 8
    elif speed <= 24.4:
        return 9
    elif speed <= 28.4:
        return 10
    elif speed <= 32.6:
        return 11
    else:
        return 12


def convert_uv_wind_to_speed_and_angle(u, v):
    if u is None or v is None or math.isnan(u) or math.isnan(v):
        return 0.0, 0.0
    speed = math.sqrt(u ** 2 + v ** 2)
    angle = math.degrees(math.atan2(u, v))
    if angle > 0:
        angle = angle - 180
    else:
        angle = angle + 180
    return speed, angle


directions_list = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                   "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]


def convert_angle_to_direction(angle):
    if angle < 0:
        angle = 360 + angle
    if math.isnan(angle):
        return directions_list[0]
    index = int((angle + 11.25) / 22.5) % 16
    return directions_list[index]


def ms_to_kts(speed):
    if speed is None or math.isnan(speed):
        return 0.0
    return speed * 1.94384449


def enrich_wind_info(data):
    for point in data:
        u = point.get("u_wind")
        v = point.get("v_wind")
        if u is not None and v is not None:
            speed, angle = convert_uv_wind_to_speed_and_angle(u, v)
            level = calculate_wind_level(speed)
            direction = convert_angle_to_direction(angle)
            point["wind_speed"] = speed
            point["wind_angle"] = angle
            point["wind_level"] = level
            point["wind_direction"] = direction
            point["wind_speed_kts"] = ms_to_kts(speed)
    return data


def calculate_flow_degree(angle):
    if angle < 0:
        angle += 360.
    return angle


def convert_uv_flow_to_speed_and_angle(u, v):
    if u is None or v is None or math.isnan(u) or math.isnan(v):
        return 0.0, 0.0
    speed = math.sqrt(u ** 2 + v ** 2)
    angle = math.degrees(math.atan2(u, v))
    return speed, angle


def enrich_flow_info(data):
    for point in data:
        u = point.get("u_flow")
        v = point.get("v_flow")
        if u is not None and v is not None:
            speed, angle = convert_uv_flow_to_speed_and_angle(u, v)
            if speed > 0:
                angle = calculate_flow_degree(angle)
            else:
                angle = 0.0
            direction = convert_angle_to_direction(angle)
            point["flow_speed"] = speed
            point["flow_angle"] = angle
            point["flow_direction"] = direction
            point["flow_speed_kts"] = ms_to_kts(speed)
    return data


def is_sailing_downstream(u, v, ship_angle):
    """
    判断船舶是否顺流航行
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

    # 判断顺流条件（夹角≤45°视为顺流）[2,7](@ref)
    return min_angle_diff <= 45


class CalcVesselPerformanceDetails(BaseModel):
    def __init__(self):
        self.QUERY_SQL_DUPLICATE = os.getenv('QUERY_SQL_DUPLICATE', False)
        self.vessel_types = os.getenv('VESSEL_TYPES', "液体散货,特种船") # "客船,干散货,杂货船,液体散货,特种船,集装箱"]

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

        super(CalcVesselPerformanceDetails, self).__init__(config)

    def get_current_performance(self, vessel, start_time, end_time):
        mmsi = vessel["mmsi"]
        draught = vessel.get("draught")
        desgin_speed = vessel.get("speed")
        # print(details)
        # 修正：details为list，增加健壮性检查
        if not draught or not desgin_speed:
            return None

        track_data = get_vessel_track(mmsi, start_time, end_time)
        track_wave_data = fetch_era5_wave_for_track(
            track_data, self.ck_client)  # era5 wave
        track_wind_data = fetch_era5_wind_for_track(
            track_data, self.ck_client)  # era5 wind
        track_flow_data = fetch_era5_flow_for_track(
            track_data, self.ck_client)  # era5 flow
        merged_track_data = merge_track_data(
            track_data, track_wave_data, track_wind_data, track_flow_data)
        merged_track_data = format_history_dates(merged_track_data)
        filtered_track_data = filter_fields(merged_track_data)
        filtered_track_data = enrich_wind_info(filtered_track_data)
        filtered_track_data = enrich_flow_info(filtered_track_data)
        # 处理数据
        if draught is None or desgin_speed is None:
            return None
        good_performance = deal_good_perf_list(
            filtered_track_data, draught, desgin_speed)
        # bad_performance = deal_bad_perf_list(
        #     filtered_track_data, draught, desgin_speed)
        return good_performance

    @decorate.exception_capture_close_datebase
    def run(self):
        # 健壮性检查：确保MongoDB连接和集合可用
        if not self.mgo_db:
            print("MongoDB连接未初始化")
            return
        try:
            _ = self.mgo_db["vessels_performance_details"]
        except Exception as e:
            print("MongoDB集合不存在或不可用", e)
            return
        try:
            query_sql = {"mmsi": {"$exists": True}}
            if self.vessel_types:
                query_sql["vesselTypeNameCn"] = {"$in": self.vessel_types}

                # 计算船舶分别在过去的12个月里面，每个月的平均速度
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
            for vessel in vessels:
                num += 1
                mmsi = vessel["mmsi"]
                draught = vessel["draught"]
                buildYear = vessel["buildYear"]
                length = vessel["length"]
                width = vessel["width"]
                height = vessel["height"]
                load_weight = vessel["dwt"]

                if self.QUERY_SQL_DUPLICATE:
                    # 默认走这个去重逻辑
                    query_sql = {"mmsi": mmsi}
                    query_sql["perf_calculated"] = 1
                    query_sql["current_performance"] = {"$ne": None}
                    res = self.mgo_db["vessels_performance_details"].find_one(
                        query_sql)
                    if res:
                        current_performance = res.get("current_performance")
                        print(current_performance)
                        # 是否有油耗的数据
                        if current_performance.get("avg_fuel"):
                            continue

                end_time = datetime.now()
                start_time = end_time - timedelta(days=180)  # 3个月 = 90天
                start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
                end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
                print(start_time, end_time)
                # 1、计算当前的航速性能（最近季度-每月更新）
                try:
                    current_performance = self.get_current_performance(
                        vessel, start_time, end_time)
                except Exception as e:
                    traceback.print_exc()
                    print("error:", e)
                    time.sleep(10)
                    continue

                if current_performance:
                    current_performance["mmsi"] = mmsi
                    current_performance["load_weight"] = load_weight
                    current_performance["ship_draft"] = draught
                    current_performance["ballast_draft"] = round(
                        current_performance["ship_draft"]*0.7, 2)
                    current_performance["length"] = length
                    current_performance["width"] = width
                    current_performance["height"] = height
                    current_performance["ship_year"] = buildYear
                    if current_performance["ship_year"]:
                        current_performance["ship_year"] = int(
                            datetime.now().year) - int(current_performance["ship_year"])

                # 计算2024年的性能数据
                # start_time_2024 = datetime(
                #     2024, 1, 1).strftime("%Y-%m-%d %H:%M:%S")
                # end_time_2024 = datetime(
                #     2024, 12, 31, 23, 59, 59).strftime("%Y-%m-%d %H:%M:%S")
                # perf_2024 = self.get_current_performance(
                #     mmsi, start_time_2024, end_time_2024)

                self.mgo_db["vessels_performance_details"].update_one(
                    {"mmsi": mmsi}, {"$set": {"current_performance": current_performance,
                                              "perf_calculated": 1,
                                              "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                              #   "perf_2024": perf_2024
                                              }}, upsert=True)

                # 入计算油耗队列
                task = {
                    'task_type': "handler_calculate_vessel_performance_ck",
                    'process_data': current_performance
                }
                if current_performance:
                    self.cache_rds.rpush(
                        "handler_calculate_vessel_performance_ck", json.dumps(task))
                    print(f"已推送mmsi={mmsi}的船舶进入油耗计算队列")
                print(
                    f"性能：{current_performance}, 已计算{num}/{total_num} 进度：{round((num / total_num) * 100, 2)}%")
                time.sleep(0.1)

        except Exception as e:
            traceback.print_exc()
            print("error:", e)
        finally:
            print("运行结束")
