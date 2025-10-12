#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import requests
from datetime import datetime
from pkg.public.models import BaseModel
import traceback
from pkg.public.logger import logger
import json
from typing import Dict, List, Any, Optional
from collections import defaultdict
import time
import re
from functools import wraps

# 配置常量
CONFIG = {
    # 网络请求配置
    "REQUEST_TIMEOUT": 30,
    "MAX_RETRIES": 3,
    "RETRY_DELAY": 1,
    "RETRY_BACKOFF": 2,
    
    # Token配置
    "TOKEN_CACHE_KEY": "windy",
    "TOKEN_CACHE_FIELD": "jackleelisheng@gmail",
    "TOKEN_CACHE_EXPIRE": 3600 * 24,  # 24小时
    
    # API配置
    "WINDY_API_BASE": "https://node.windy.com/tc/v2",
    "ZOOM_API_BASE": "https://zoom.earth/data/storms",
    "NAVGREEN_API": "https://miniapi.navgreen.cn/api/mete/forecast/storms/v1",
    
    # 缓存配置
    "STORM_CACHE_KEY": "windy_current_storms",
    
    # 台风等级风速阈值（米/秒）
    "TYPHOON_LEVELS": {
        "tropical_depression": 10.8,
        "tropical_storm": 17.2,
        "severe_tropical_storm": 24.5,
        "typhoon": 32.7,
        "severe_typhoon": 41.5,
        "super_typhoon": 51.0
    }
}


def retry_on_failure(max_retries=None, delay=None, backoff=None):
    """重试装饰器，用于处理网络请求失败"""
    if max_retries is None:
        max_retries = CONFIG["MAX_RETRIES"]
    if delay is None:
        delay = CONFIG["RETRY_DELAY"]
    if backoff is None:
        backoff = CONFIG["RETRY_BACKOFF"]
        
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                    
                    if attempt < max_retries - 1:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {str(e)}")
                        raise last_exception
            
            return None
        return wrapper
    return decorator


def get_newest_token(cache_redis):
    """获取最新的Windy token"""
    try:
        url = "https://account.windy.com/api/info"
        querystring = {"country": "sg"}
        
        headers = {
            "Origin": "capacitor://app-webview.windy.com",
            "Accept": "application/json binary/4413mobc40b token/d6df4064e2379e732d643d20afbf3b9b",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Dest": "empty",
            "Host": "account.windy.com",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Sec-Fetch-Mode": "cors",
            "windy-csrf": "zs/Am4/CnpyckIqRi9CWkZmQ2ZuTwpyej56clouQjdrMvtrNudrNuZ6Pj9KImp2JlpqI0YiWkZuG0ZyQktmekcKolpGbhtmclpvCm5yemcmbzs/SnJ7PyNLLyceZ0sfNy57SnZmczs7HzJnGzcrO2YyNwszGzIfHys3ZipfCzpaVjJOeypjOz86aycyazs7PyJ3NmcrZipPCmpHSqqzZnpabwpyQktGIlpGbhtGWkIzZmYnCi42KmtmMjMKLjYqa2ZuLws7IzMbMy8bHxs/KzMjZm43C2ZqLws8=",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cookie": "_account_ss=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ODgyMTA4OCwidXNlcm5hbWUiOiJsaXFpeXVXb3JrcyIsImVtYWlsIjoiamFja2xlZWxpc2hlbmdAZ21haWwuY29tIiwiaWF0IjoxNzQxOTM4MDMxfQ.GE4DR_a4ebZUTdwZ5lJAPYpY9WWJVTuXrm6hjMPNNZA;_account_sid=s%3AMdg9k5DsOIM5R0hZwA-pfw9aBxVsHl7b.HKmgplkKt75eZoHPJdr%2BExqj%2FOMF1%2BGtGcdEoLTxE%2F8"
        }

        response = requests.get(
            url=url,
            headers=headers,
            params=querystring,
            timeout=CONFIG["REQUEST_TIMEOUT"]
        )
        response.raise_for_status()
        
        token = response.json().get("token")
        if not token:
            raise ValueError("No token found in response")
            
        cache_redis.hset(CONFIG["TOKEN_CACHE_KEY"], CONFIG["TOKEN_CACHE_FIELD"], token)
        cache_redis.expire(CONFIG["TOKEN_CACHE_KEY"], CONFIG["TOKEN_CACHE_EXPIRE"])
        logger.info("Successfully obtained new Windy token")
        return token
        
    except Exception as e:
        logger.error(f"Failed to get newest token: {str(e)}")
        raise


@retry_on_failure(max_retries=3, delay=2)
def get_check_token_expired(cache_redis):
    """检查并获取有效的token"""
    token = cache_redis.hget(CONFIG["TOKEN_CACHE_KEY"], CONFIG["TOKEN_CACHE_FIELD"])
    
    if not token:
        logger.info("Token not found in cache, attempting to get from navgreen API")
        try:
            response = requests.get(
                CONFIG["NAVGREEN_API"],
                headers={"accept": "application/json"},
                timeout=CONFIG["REQUEST_TIMEOUT"]
            )
            response.raise_for_status()
            
            # 重新从缓存获取token
            token = cache_redis.hget(CONFIG["TOKEN_CACHE_KEY"], CONFIG["TOKEN_CACHE_FIELD"])
            if token:
                logger.info("Successfully retrieved token from navgreen API")
            else:
                logger.error("Token still not available after navgreen API call")
                
        except Exception as e:
            logger.error(f"Failed to get token from navgreen API: {str(e)}")
            raise
    else:
        logger.debug("Token retrieved from cache successfully")
        
    return token


@retry_on_failure(max_retries=2, delay=1)
def request_svc_detail(token, mmsi_list):
    """请求船舶详情信息"""
    url = "https://svc.data.myvessel.cn/sdc/v1/vessels/details"
    
    payload = {"mmsiList": mmsi_list}
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        url=url,
        headers=headers,
        json=payload,
        timeout=CONFIG["REQUEST_TIMEOUT"]
    )
    response.raise_for_status()
    
    return response.json().get("data", [])


class SpiderWindyZoomStorms(BaseModel):
    def __init__(self):
        config = {
            "cache_rds": True
        }
        super(SpiderWindyZoomStorms, self).__init__(config)
        
        # 设置请求超时和重试参数
        self.timeout = CONFIG["REQUEST_TIMEOUT"]
        self.max_retries = CONFIG["MAX_RETRIES"]

    @retry_on_failure(max_retries=3, delay=1)
    def get_windy_storms(self, windy_token):
        """获取Windy风暴列表"""
        url = f"{CONFIG['WINDY_API_BASE']}/storms?pr=0&sc=23&token2={windy_token}"
        
        response = requests.get(url=url, timeout=self.timeout)
        response.raise_for_status()
        
        storms = response.json().get("storms", [])
        logger.info(f"Retrieved {len(storms)} storms from Windy")
        return storms

    @retry_on_failure(max_retries=3, delay=1)
    def get_windy_storm_track(self, windy_token, storm_name):
        """获取Windy风暴轨迹"""
        url = f"{CONFIG['WINDY_API_BASE']}/storms/{storm_name}?pr=0&sc=23&token2={windy_token}"
        
        response = requests.get(url=url, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()

    @retry_on_failure(max_retries=2, delay=2)
    def get_zoom_storms_list(self, date):
        """获取Zoom风暴列表"""
        url = CONFIG["ZOOM_API_BASE"]
        querystring = {"date": date, "to": "12"}

        headers = {
            "Host": "zoom.earth",
            "Cookie": "_tea_utm_cache_10000007=undefined",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "accept": "*/*",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://zoom.earth/",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "priority": "u=1, i",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        response = requests.get(
            url, 
            headers=headers, 
            params=querystring, 
            timeout=self.timeout
        )
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"Retrieved {len(result.get('storms', []))} storms from Zoom")
        return result

    @retry_on_failure(max_retries=2, delay=2)
    def get_zoom_storms_track(self, storm_name):
        """获取Zoom风暴轨迹"""
        url = CONFIG["ZOOM_API_BASE"]
        querystring = {"id": storm_name, "lang": "zh"}

        headers = {
            "Host": "zoom.earth",
            "Cookie": "_tea_utm_cache_10000007=undefined",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua-mobile": "?0",
            "accept": "*/*",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://zoom.earth/",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "priority": "u=1, i",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive"
        }

        response = requests.get(
            url, 
            headers=headers, 
            params=querystring, 
            timeout=self.timeout
        )
        response.raise_for_status()
        
        return response.json()

    def convert_zoom_to_windy_format(self, zoom_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Zoom.Earth typhoon data format to Windy format

        Args:
            zoom_data (dict): Typhoon data in Zoom.Earth format

        Returns:
            dict: Typhoon data in Windy format
        """
        try:
            # Extract basic info
            typhoon_data = {
                'id': zoom_data.get('id', ''),
                'name': zoom_data.get('name', ''),
                'lat': None,  # Will be updated with latest position
                'lon': None,  # Will be updated with latest position
                'strength': 1,  # Default value as it's not directly mappable
                'windSpeed': None,  # Will be updated with latest wind speed
                'history': [],
                'forecast': []
            }

            # Process track points
            current_time = None
            # Group forecast points by reference time
            forecast_points = defaultdict(list)

            track = zoom_data.get('track', [])
            if not track:
                logger.warning(f"No track data found for storm {zoom_data.get('id', 'unknown')}")
                return typhoon_data

            for point in track:
                try:
                    # Extract common fields
                    coordinates = point.get('coordinates', [])
                    if len(coordinates) < 2:
                        logger.warning(f"Invalid coordinates in track point: {point}")
                        continue
                        
                    point_data = {
                        'lat': coordinates[1],  # Zoom uses [lon, lat]
                        'lon': coordinates[0],
                        'windSpeed': (point.get('wind', 0) or 0) * 0.514444,  # Convert knots to m/s
                        'pressure': point.get('pressure'),
                        'time': point.get('date')
                    }

                    # Update latest position if this is the most recent non-forecast point
                    if not point.get('forecast', False) and (current_time is None or point.get('date', '') > current_time):
                        current_time = point.get('date', '')
                        typhoon_data['lat'] = point_data['lat']
                        typhoon_data['lon'] = point_data['lon']
                        typhoon_data['windSpeed'] = point_data['windSpeed']

                    # Add to appropriate list
                    if point.get('forecast', False):
                        # Group forecast points by their reference time (current_time)
                        forecast_points[current_time].append(point_data)
                    else:
                        typhoon_data['history'].append(point_data)
                        
                except Exception as e:
                    logger.warning(f"Error processing track point: {e}")
                    continue

            # Convert forecast points into the required format
            if forecast_points:
                for reftime, points in forecast_points.items():
                    forecast_entry = {
                        'reftime': reftime,
                        'modelIdentifier': 'JTWC',  # Using JTWC as the model identifier
                        'records': sorted(points, key=lambda x: x.get('time', ''))
                    }
                    typhoon_data['forecast'].append(forecast_entry)

            # Sort history by time in descending order (newest first)
            typhoon_data['history'].sort(key=lambda x: x.get('time', ''), reverse=True)
            
            return typhoon_data
            
        except Exception as e:
            logger.error(f"Error converting zoom data to windy format: {e}")
            return {}

    def classify_typhoon(self, wind_speed: Optional[float]) -> str:
        """根据风速（单位：米/秒）返回台风等级"""
        if not wind_speed or wind_speed < 0:
            return "未知"
            
        levels = CONFIG["TYPHOON_LEVELS"]
        if wind_speed < levels["tropical_depression"]:
            return "<热带低压"
        elif levels["tropical_depression"] <= wind_speed < levels["tropical_storm"]:
            return "热带低压"
        elif levels["tropical_storm"] <= wind_speed < levels["severe_tropical_storm"]:
            return "热带风暴"
        elif levels["severe_tropical_storm"] <= wind_speed < levels["typhoon"]:
            return "强热带风暴"
        elif levels["typhoon"] <= wind_speed < levels["severe_typhoon"]:
            return "台风"
        elif levels["severe_typhoon"] <= wind_speed < levels["super_typhoon"]:
            return "强台风"
        else:
            return "超强台风"

    def normalize_storm_id_prefix(self, prefix: str) -> str:
        """标准化风暴ID前缀"""
        if not prefix:
            return ""
            
        # 处理数字和英文数字的映射
        num_map = {
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
            "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
            "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
            "nineteen": "19", "twenty": "20"
        }
        
        prefix = prefix.lower()
        
        # 先查找是否是英文数字
        for k, v in num_map.items():
            if prefix.startswith(k):
                return v
                
        # 查找是否是数字+字母（如13w），只取数字部分
        m = re.match(r"(\d+)", prefix)
        if m:
            return m.group(1)
            
        return prefix

    def process_windy_storms(self, windy_token: str) -> List[Dict[str, Any]]:
        """处理Windy风暴数据"""
        try:
            storms = self.get_windy_storms(windy_token)
            data = []
            
            for storm in storms:
                try:
                    storm_id = storm.get("id")
                    if not storm_id:
                        logger.warning("Storm without ID found, skipping")
                        continue
                        
                    track = self.get_windy_storm_track(windy_token, storm_id)
                    wind_speed = storm.get("windSpeed")
                    
                    if wind_speed:
                        typhoon_level = self.classify_typhoon(wind_speed)
                        logger.debug(f"Storm {storm_id} classified as {typhoon_level}")
                        track["strength"] = typhoon_level
                    
                    data.append(track)
                    
                except Exception as e:
                    logger.error(f"Error processing Windy storm {storm.get('id', 'unknown')}: {e}")
                    continue
                    
            return data
            
        except Exception as e:
            logger.error(f"Error processing Windy storms: {e}")
            return []

    def process_zoom_storms(self, date_utc: str, windy_storms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理Zoom风暴数据"""
        try:
            zoom_storms_list = self.get_zoom_storms_list(date_utc)
            zoom_storms = zoom_storms_list.get("storms", [])
            
            data = []
            processed_storms = set()
            
            for storm in zoom_storms:
                try:
                    if not isinstance(storm, str):
                        logger.warning(f"Invalid storm format: {storm}")
                        continue
                        
                    # 如果 storm 的值分割-，取前一部分，然后看是否存在storms里，全部用小写对比
                    storm_id_prefix = storm.split('-')[0].lower()
                    
                    # 检查是否已存在于Windy数据中
                    norm_storm_id_prefix = self.normalize_storm_id_prefix(storm_id_prefix)
                    exists_in_storms = any(
                        self.normalize_storm_id_prefix(s.get("id", "").split('-')[0]) == norm_storm_id_prefix
                        for s in windy_storms if isinstance(s.get("id", ""), str)
                    )
                    
                    logger.debug(f"Storm {storm_id_prefix}, exists in Windy: {exists_in_storms}")
                    
                    if exists_in_storms:
                        # 修改 data 里面id 为 storm_id_prefix，然后修改 id 为 storm
                        for d in data:
                            if d.get("id", "").split('-')[0].lower() == storm_id_prefix:
                                d["id"] = storm
                        processed_storms.add(storm)
                        continue

                    track = self.get_zoom_storms_track(storm)
                    zoom_data = self.convert_zoom_to_windy_format(track)
                    
                    if not zoom_data:
                        logger.warning(f"Failed to convert zoom data for storm {storm}")
                        continue
                        
                    wind_speed = zoom_data.get("windSpeed")
                    if wind_speed:
                        typhoon_level = self.classify_typhoon(wind_speed)
                        logger.debug(f"Zoom storm {storm} classified as {typhoon_level}")
                        zoom_data["strength"] = typhoon_level

                    data.append(zoom_data)
                    processed_storms.add(storm)
                    
                except Exception as e:
                    logger.error(f"Error processing Zoom storm {storm}: {e}")
                    continue
                    
            return data
            
        except Exception as e:
            logger.error(f"Error processing Zoom storms: {e}")
            return []

    @decorate.exception_capture_close_datebase
    def run(self):
        """主运行方法"""
        dataTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_utc = datetime.utcnow().strftime("%Y-%m-%dT00:00Z")
        
        logger.info(f"Starting storm data collection at {dataTime}, date_utc={date_utc}")
        
        try:
            # 获取token
            windy_token = get_check_token_expired(self.cache_rds)
            if not windy_token:
                logger.error("Failed to obtain valid token")
                return
                
            # 处理Windy风暴数据
            windy_data = self.process_windy_storms(windy_token)
            
            # 处理Zoom风暴数据
            zoom_data = self.process_zoom_storms(date_utc, windy_data)
            
            # 合并数据
            all_data = windy_data + zoom_data
            
            # 进行排序
            # 优先排序 forecast 不为空的台风，其次按 id 倒序
            # 优先展示有forecast的台风，然后有forecast的台风按风速大小排序
            all_data.sort(key=lambda x: (not x.get("forecast"), -(x.get("windSpeed") or 0)))
            
            # 设置缓存
            windy_current_storms = {
                "data": all_data,
                "fresh_time": dataTime
            }
            
            self.cache_rds.set(CONFIG["STORM_CACHE_KEY"], json.dumps(windy_current_storms))
            logger.info(f"Successfully updated storm data with {len(all_data)} storms")
            
        except Exception as e:
            logger.error(f"Error in main run method: {e}")
            traceback.print_exc()
            raise
