#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
from typing import Dict, Any
import csv
import datetime
import time
import os
import requests
import urllib3
import pymongo
import logging
import random
from pkg.public.models import BaseModel

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# AXS API 基础配置
AXS_BASE_URL = "https://app.axsmarine.com/Apps/VTD/api"


def optimize_vessel_data_fields(vessel_data: Dict[str, Any], imo: str) -> Dict[str, Any]:
    """
    优化船舶数据字段，与原始API响应数据区分

    Args:
        vessel_data: 从fuel_data.get("vessel")获取的原始船舶数据
        imo: 船舶IMO号，用于标识

    Returns:
        优化后的船舶数据字典
    """
    if not vessel_data or not isinstance(vessel_data, dict):
        return {}

    # 定义字段映射规则，将原始字段映射到优化后的字段名
    field_mapping = {
        # 基础标识字段
        'vessel_id': 'axs_vessel_id',
        'id': 'axs_vessel_id',
        'imo': 'vessel_imo',
        'mmsi': 'vessel_mmsi',
        'name': 'vessel_name',
        'nameEn': 'vessel_name_en',
        'nameCn': 'vessel_name_cn',

        # 船舶类型相关
        'vesselType': 'vessel_type',
        'vesselTypeName': 'vessel_type_name',
        'vesselTypeNameEn': 'vessel_type_name_en',
        'vesselTypeNameCn': 'vessel_type_name_cn',
        'vesselSubType': 'vessel_sub_type',
        'vesselSubTypeName': 'vessel_sub_type_name',
        'vesselSubTypeNameEn': 'vessel_sub_type_name_en',
        'vesselSubTypeNameCn': 'vessel_sub_type_name_cn',

        # 船舶规格相关
        'length': 'vessel_length',
        'width': 'vessel_width',
        'height': 'vessel_height',
        'dwt': 'vessel_dwt',
        'grt': 'vessel_grt',
        'nrt': 'vessel_nrt',
        'teu': 'vessel_teu',
        'draft': 'vessel_draft',
        'maxDraft': 'vessel_max_draft',

        # 建造信息
        'buildYear': 'vessel_build_year',
        'buildCountry': 'vessel_build_country',
        'buildCountryName': 'vessel_build_country_name',
        'builder': 'vessel_builder',

        # 船舶状态
        'status': 'vessel_status',
        'statusName': 'vessel_status_name',
        'flag': 'vessel_flag',
        'flagCountry': 'vessel_flag_country',
        'flagCountryName': 'vessel_flag_country_name',
        'flagCountryNameEn': 'vessel_flag_country_name_en',
        'flagCountryNameCn': 'vessel_flag_country_name_cn',

        # 位置和时间信息
        'latitude': 'vessel_latitude',
        'longitude': 'vessel_longitude',
        'course': 'vessel_course',
        'speed': 'vessel_speed',
        'heading': 'vessel_heading',
        'postime': 'vessel_position_time',
        'lastUpdateTime': 'vessel_last_update_time',

        # 联系信息
        'callSign': 'vessel_call_sign',
        'call_sign': 'vessel_call_sign',

        # 其他字段
        'classSociety': 'vessel_class_society',
        'classSocietyName': 'vessel_class_society_name',
        'operator': 'vessel_operator',
        'owner': 'vessel_owner',
        'manager': 'vessel_manager',
    }

    # 初始化优化后的数据
    optimized_data = {
        'query_imo': imo,  # 查询时使用的IMO
        # 'data_source': 'axs_api',  # 数据来源标识
        'data_version': '1.0',  # 数据版本
        'last_updated': int(time.time()),  # 最后更新时间戳
    }

    # 遍历原始数据，应用字段映射
    for original_key, value in vessel_data.items():
        if value is None or value == "":
            continue

        # 获取映射后的字段名
        mapped_key = field_mapping.get(original_key, f"raw_{original_key}")

        # 特殊处理某些字段
        if original_key in ['imo', 'mmsi'] and value:
            optimized_data[mapped_key] = str(value)
        elif original_key in ['latitude', 'longitude', 'speed', 'course', 'heading'] and value:
            try:
                optimized_data[mapped_key] = float(value)
            except (ValueError, TypeError):
                optimized_data[mapped_key] = value
        elif original_key in ['buildYear', 'dwt', 'grt', 'nrt', 'teu'] and value:
            try:
                optimized_data[mapped_key] = int(value)
            except (ValueError, TypeError):
                optimized_data[mapped_key] = value
        else:
            optimized_data[mapped_key] = value

    # 添加一些计算字段
    if 'vessel_length' in optimized_data and 'vessel_width' in optimized_data:
        try:
            length = float(optimized_data['vessel_length'])
            width = float(optimized_data['vessel_width'])
            optimized_data['vessel_length_width_ratio'] = round(
                length / width, 2) if width > 0 else None
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    # 添加数据质量标识
    optimized_data['data_quality'] = {
        'has_basic_info': bool(optimized_data.get('vessel_imo') and optimized_data.get('vessel_name')),
        'has_position': bool(optimized_data.get('vessel_latitude') and optimized_data.get('vessel_longitude')),
        'has_specs': bool(optimized_data.get('vessel_length') or optimized_data.get('vessel_dwt')),
        'has_type_info': bool(optimized_data.get('vessel_type') or optimized_data.get('vessel_type_name')),
        'has_flag_info': bool(optimized_data.get('vessel_flag_country') or optimized_data.get('vessel_flag_country_name')),
        'field_count': len([k for k in optimized_data.keys() if not k.startswith('raw_') and k not in ['query_imo', 'data_source', 'data_version', 'last_updated', 'data_quality']]),
        'original_field_count': len(vessel_data) if vessel_data else 0
    }

    return optimized_data


def get_axs_headers(cookie: str = None) -> Dict[str, str]:
    """
    获取AXS API请求头

    Args:
        cookie: 可选的cookie字符串

    Returns:
        请求头字典
    """
    headers = {
        'authority': 'app.axsmarine.com',
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'referer': 'https://app.axsmarine.com/Apps/VTD/ui/?app=VTD&singleFrame=true',
        'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    }

    if cookie:
        headers['Cookie'] = cookie

    return headers


def get_dc_timestamp() -> str:
    """
    获取当前时间戳（毫秒）

    Returns:
        时间戳字符串
    """
    return str(int(time.time() * 1000))


def get_vessel_id_from_imo(imo: str, cookie: str = None, retries: int = 3) -> Dict[str, Any]:
    """
    根据IMO号获取船舶ID

    Args:
        imo: 船舶IMO号
        cookie: 可选的cookie字符串
        retries: 重试次数

    Returns:
        船舶信息字典
    """
    url = f"{AXS_BASE_URL}/vtd/vessels/home"
    headers = get_axs_headers(cookie=cookie)

    params = {
        '_dc': get_dc_timestamp(),
        'query': imo,
        'logic': 'exact',
        'searchDemolished': 'false',
        'page': '1',
        'start': '0',
        'limit': '1'
    }

    for attempt in range(retries):
        try:
            response = requests.get(
                url=url, headers=headers, params=params, timeout=30, verify=False)
            response.raise_for_status()

            data = response.json()
            if data and isinstance(data, dict):
                if data.get('errors'):
                    raise ValueError(f"API返回错误: {data['errors']}")
                if data.get('data') and len(data['data']) > 0:
                    return data['data'][0]
                raise ValueError("未找到匹配的船舶")
            else:
                raise ValueError("API返回数据格式错误")

        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                logging.error("获取船舶ID失败: IMO=%s, 错误=%s", imo, str(e))
                raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                logging.error("获取船舶ID未知错误: IMO=%s, 错误=%s", imo, str(e))
                raise

    raise ValueError(f"未找到IMO为 {imo} 的船舶")


def get_fuel_data_from_vessel_id(vessel_id: str, page: int = 1, limit: int = 25, cookie: str = None, retries: int = 3) -> Dict[str, Any]:
    """
    根据vessel_id获取油耗数据

    Args:
        vessel_id: 船舶ID
        page: 页码
        limit: 每页数量
        cookie: 可选的cookie字符串
        retries: 重试次数

    Returns:
        油耗数据字典
    """
    url = f"{AXS_BASE_URL}/vtd/vessel/{vessel_id}"
    headers = get_axs_headers(cookie=cookie)

    params = {
        '_dc': get_dc_timestamp(),
        'vesselId': str(vessel_id),
        'page': str(page),
        'start': str((page - 1) * limit),
        'limit': str(limit)
    }

    for attempt in range(retries):
        try:
            response = requests.get(
                url=url, headers=headers, params=params, timeout=30, verify=False)
            response.raise_for_status()

            data = response.json()
            if data and isinstance(data, dict):
                return data
            else:
                raise ValueError("API返回数据格式错误")

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                logging.error("获取油耗数据网络错误: vessel_id=%s, 错误=%s",
                              vessel_id, str(e))
                raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                logging.error("获取油耗数据错误: vessel_id=%s, 错误=%s",
                              vessel_id, str(e))
                raise

    raise ValueError(f"无法获取vessel_id {vessel_id} 的油耗数据")


def search_vessels_by_query(
    query: str,
    logic: str = "begin",
    search_demolished: bool = False,
    page: int = 1,
    limit: int = 25,
    retries: int = 3,
    cookie: str = None
) -> Dict[str, Any]:
    """
    根据查询条件搜索船舶列表

    Args:
        query: 搜索关键词（IMO、船名等）
        logic: 搜索逻辑 (begin/contains/exact)
        search_demolished: 是否搜索已拆解船舶
        page: 页码
        limit: 每页数量
        retries: 重试次数
        cookie: 可选的 cookie 字符串，从 Redis 缓存获取

    Returns:
        船舶搜索结果
    """
    url = f"{AXS_BASE_URL}/vtd/vessels/home"
    headers = get_axs_headers(cookie=cookie)

    params = {
        '_dc': get_dc_timestamp(),
        'query': query,
        'logic': logic,
        'searchDemolished': str(search_demolished).lower(),
        'page': str(page),
        'start': str((page - 1) * limit),
        'limit': str(limit)
    }

    for attempt in range(retries):
        try:
            response = requests.get(
                url=url, headers=headers, params=params, timeout=30, verify=False)
            response.raise_for_status()

            data = response.json()
            if data and isinstance(data, dict):
                if data.get('errors'):
                    raise ValueError(f"API返回错误: {data['errors']}")
                return data
            else:
                raise ValueError("API返回数据格式错误")

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                logging.error("搜索船舶网络错误: query=%s, 错误=%s", query, str(e))
                raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                logging.error("搜索船舶错误: query=%s, 错误=%s", query, str(e))
                raise

    raise ValueError(f"未找到匹配查询条件 '{query}' 的船舶")


class SyncShipsFuelFromAxs(BaseModel):
    def __init__(self):
        config = {
            'cache_rds': True,
            'handle_db': 'mgo',
            'collection': 'axs_vessel_fuel_data',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
            ]
        }
        super(SyncShipsFuelFromAxs, self).__init__(config)
        
    def get_vessel_info_from_imo(self, imo: str, cookie: str = None, skip_count: int = 0, success_count: int = 0) -> None:
        # 2、获取vessel_id
        vessel_id = None
        try:
            search_result = search_vessels_by_query(
                query=imo, logic="exact", cookie=cookie)
            if search_result and search_result.get('errors'):
                error_msg = search_result['errors'][0] if isinstance(
                    search_result['errors'], list) else str(search_result['errors'])
                raise ValueError(f"搜索接口错误: {error_msg}")

            if search_result and search_result.get('data') and len(search_result['data']) > 0:
                vessel_data = search_result['data'][0]
                vessel_id = vessel_data.get(
                    'vessel_id') or vessel_data.get('id')
            else:
                raise ValueError("搜索接口未返回有效数据")

        except Exception:
            try:
                vessel_response = get_vessel_id_from_imo(
                    imo, cookie=cookie)
                if not vessel_response or not isinstance(vessel_response, dict):
                    raise ValueError(f"未找到IMO为 {imo} 的船舶信息")
                vessel_id = vessel_response.get(
                    'vessel_id') or vessel_response.get('id')
                if not vessel_id:
                    raise ValueError("无法获取船舶ID")
            except Exception:
                # 标记为未找到，避免下次再查询
                logging.warning("无法获取IMO %s 的船舶信息，标记为未找到", imo)
                no_data_marker = {
                    'imo': imo,
                    'no_data': True,
                    'status': 'not_found',
                    'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                self.mgo.set(None, no_data_marker)
                skip_count += 1
                return skip_count, success_count

        # 3、根据vessel_id获取油耗数据
        time.sleep(random.randint(1, 3))
        fuel_data = get_fuel_data_from_vessel_id(
            vessel_id, page=1, limit=25, cookie=cookie)
        raw_vessel_data = fuel_data.get(
            "vessel") if fuel_data else None

        # 4、优化并保存数据
        if raw_vessel_data and isinstance(raw_vessel_data, dict):
            optimized_data = optimize_vessel_data_fields(
                raw_vessel_data, imo)
            optimized_data['imo'] = imo
            optimized_data['created_at'] = datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S")
            print(f"{imo} - {optimized_data.get('raw_ecoIfoLaden')}")
            result = self.mgo.set(None, optimized_data)
            if result:
                success_count += 1
        else:
            # 即使获取到vessel_id但没有船体数据，也标记为未找到
            logging.warning("IMO %s 未获取到有效船舶数据，标记为未找到", imo)
            no_data_marker = {
                'imo': imo,
                'no_data': True,
                'status': 'no_vessel_data',
                'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.mgo.set(None, no_data_marker)
            skip_count += 1
                    
        return skip_count, success_count

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        print(f"sync_ships_fuel_from_axs start at {dataTime}")

        # 获取cookie（如果配置了Redis cache）
        cookie = None
        if hasattr(self, 'cache_rds') and self.cache_rds:
            try:
                cookie = self.cache_rds.get('axs_live_cookie')
            except Exception:
                pass

        # 从CSV文件读取船舶IMO列表
        csv_path = os.path.join(os.path.dirname(__file__), '../x_sp_ship.csv')
        if not os.path.exists(csv_path):
            logging.error("未找到CSV文件: %s", csv_path)
            return

        # 读取CSV文件
        imo_list = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    imo = row.get('imo', '').strip()
                    if imo and imo.isdigit():
                        imo_list.append(imo)
            logging.info("从CSV读取到 %d 个IMO号", len(imo_list))
        except Exception as e:
            logging.error("读取CSV文件失败: %s", str(e))
            return

        # 处理每个IMO
        success_count = 0
        skip_count = 0
        for idx, imo in enumerate(imo_list, 1):
            try:
                # 1、检查缓存数据是否存在且未过期
                cached_data = self.mgo.get({"imo": imo})
                if cached_data:
                    skip_count += 1
                    continue
                
                self.get_vessel_info_from_imo(imo, cookie, skip_count, success_count)

                # 请求间隔
                time.sleep(random.randint(1, 3))

                # 每处理10条打印一次进度
                if idx % 10 == 0:
                    print(
                        f"进度: {idx}/{len(imo_list)}, 跳过: {skip_count}, 成功: {success_count}")

            except Exception as e:
                logging.error("处理IMO %s 失败: %s", imo, str(e))
                continue

        print(
            f"sync_ships_fuel_from_axs completed: 总计 {len(imo_list)} 条, 已跳过 {skip_count} 条, 成功处理 {success_count} 条")


class SyncSearchVesselsFuelFromAxs(SyncShipsFuelFromAxs):
    """
    包装类：用于调用 run_search_vessels_by_query 方法
    """
    @decorate.exception_capture_close_datebase
    def run(self):
        """
        重写 run 方法，调用 run_search_vessels_by_query
        """
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        print(dataTime)

        # 获取cookie（如果配置了Redis cache）
        cookie = None
        if hasattr(self, 'cache_rds') and self.cache_rds:
            try:
                cookie = self.cache_rds.get('axs_live_cookie')
            except Exception:
                pass

        # 从mongo中获取vessel_search_history集合中的数据mmsi数据，去重
        mmsi_list = self.mgo_db["vessel_search_history"].find(
            {}, {"mmsi": 1, "_id": 0}).distinct("mmsi")
        print(f"从mongo中获取到 {len(mmsi_list)} 个mmsi")
        
        # 遍历 mmsi 从global_vessels获取对应的 imo
        for mmsi in mmsi_list:
            mmsi = int(mmsi)
            try:
                print(f"处理 mmsi: {mmsi}")
                # 使用 find_one 而不是 find，因为只需要获取一个文档
                vessel_info = self.mgo_db["global_vessels"].find_one(
                    {"mmsi": mmsi}, {"imo": 1, "_id": 0})
                if vessel_info and vessel_info.get("imo"):
                    imo = vessel_info.get("imo")
                    imo = str(imo)   # 油耗里面 imo是字符串，global_vessels里面 imo是整型。所以需要转换一下。
                    print(f"找到对应的 imo: {imo}")
                    # 在这里添加处理 imo 的逻辑
                    skip_count, success_count = self.get_vessel_info_from_imo(imo, cookie, 0, 0)
                    
                else:
                    print(f"未找到mmsi为 {mmsi} 的船舶或imo为空")
                    continue
                
            except Exception as e:
                print(f"获取mmsi为 {mmsi} 的船舶失败: {e}")
                continue
