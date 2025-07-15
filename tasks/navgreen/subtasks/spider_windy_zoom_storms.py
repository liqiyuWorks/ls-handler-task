#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import requests
from datetime import datetime
from pkg.public.models import BaseModel
import traceback
from pkg.public.logger import logger
import json
from typing import Dict, List, Any
from collections import defaultdict


def get_newest_token(cache_redis):
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
        data=querystring)

    token = response.json().get("token")

    cache_redis.hset("windy", "jackleelisheng@gmail", token)
    cache_redis.expire("windy", 3600*24)  # 3600*24 -> 1 day
    return token


def get_check_token_expired(cache_redis):
    token2 = cache_redis.hget("windy", "jackleelisheng@gmail")
    if not token2:
        # 获取新的token
        token2 = get_newest_token(cache_redis)
        print(f"get new token from windy success!,token2={token2}")
    else:
        print(f"get token from cache success!,token2={token2}")
        token2 = token2
    return token2


def request_svc_detail(token, mmsi_list):
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
        json=payload)

    return response.json().get("data", [])


class SpiderWindyZoomStorms(BaseModel):
    def __init__(self):
        config = {
            "cache_rds": True
        }

        super(SpiderWindyZoomStorms, self).__init__(config)

    def get_windy_storms(self, windy_token):
        url = f"https://node.windy.com/tc/v2/storms?pr=0&sc=23&token2={windy_token}"

        response = requests.get(url=url)
        storms = response.json().get("storms", [])

        return storms

    def get_windy_storm_track(self, windy_token, storm_name):
        url = f"https://node.windy.com/tc/v2/storms/{storm_name}?pr=0&sc=23&token2={windy_token}"

        response = requests.get(url=url)

        return response.json()

    def get_zoom_storms_list(self, date):
        url = f"https://zoom.earth/data/storms"
        querystring = {"date": date, "to": "12"}

        payload = ""
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

        response = requests.request(
            "GET", url, data=payload, headers=headers, params=querystring)
        return response.json()

    def get_zoom_storms_track(self, storm_name):
        url = f"https://zoom.earth/data/storms"
        querystring = {"id": storm_name, "lang": "zh"}

        payload = ""
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

        response = requests.request(
            "GET", url, data=payload, headers=headers, params=querystring)

        return response.json()

    def convert_zoom_to_windy_format(self, zoom_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Zoom.Earth typhoon data format to Windy format

        Args:
            zoom_data (dict): Typhoon data in Zoom.Earth format

        Returns:
            dict: Typhoon data in Windy format
        """
        # Extract basic info
        typhoon_data = {
            'id': zoom_data['id'],
            'name': zoom_data['name'],
            'lat': None,  # Will be updated with latest position
            'lon': None,  # Will be updated with latest position
            'strength': 1,  # Default value as it's not directly mappable
            'windSpeed': None,  # Will be updated with latest wind speed
            'history': [],
            'forecast': []
        }

        result = {
            'data': [typhoon_data],
            'fresh_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Process track points
        current_time = None
        # Group forecast points by reference time
        forecast_points = defaultdict(list)

        for point in zoom_data['track']:
            # Extract common fields
            point_data = {
                'lat': point['coordinates'][1],  # Zoom uses [lon, lat]
                'lon': point['coordinates'][0],
                'windSpeed': point['wind'] * 0.514444,  # Convert knots to m/s
                'pressure': point['pressure'] if point['pressure'] else None,
                'time': point['date']
            }

            # Update latest position if this is the most recent non-forecast point
            if not point['forecast'] and (current_time is None or point['date'] > current_time):
                current_time = point['date']
                typhoon_data['lat'] = point_data['lat']
                typhoon_data['lon'] = point_data['lon']
                typhoon_data['windSpeed'] = point_data['windSpeed']

            # Add to appropriate list
            if point['forecast']:
                # Group forecast points by their reference time (current_time)
                forecast_points[current_time].append(point_data)
            else:
                typhoon_data['history'].append(point_data)

        # Convert forecast points into the required format
        if forecast_points:
            for reftime, points in forecast_points.items():
                forecast_entry = {
                    'reftime': reftime,
                    'modelIdentifier': 'JTWC',  # Using JTWC as the model identifier
                    'records': sorted(points, key=lambda x: x['time'])
                }
                typhoon_data['forecast'].append(forecast_entry)

        # Sort history by time in descending order (newest first)
        typhoon_data['history'].sort(key=lambda x: x['time'], reverse=True)

        return result.get("data", [])[0]

    def classify_typhoon(self, wind_speed):
        """根据风速（单位：米/秒）返回台风等级"""
        if wind_speed < 10.8:
            return "<热带低压"
        elif 10.8 <= wind_speed < 17.2:
            return "热带低压"
        elif 17.2 <= wind_speed < 24.5:  # 热带风暴范围
            return "热带风暴"
        elif 24.5 <= wind_speed < 32.7:
            return "强热带风暴"
        elif 32.7 <= wind_speed < 41.5:
            return "台风"
        elif 41.5 <= wind_speed < 51.0:
            return "强台风"
        else:
            return "超强台风"

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_utc = datetime.utcnow().strftime("%Y-%m-%dT00:00Z")
        print(f"date_utc={date_utc}")
        try:
            windy_token = get_check_token_expired(self.cache_rds)
            data = []
            storms = self.get_windy_storms(windy_token)
            for storm in storms:
                id = storm.get("id")
                track = self.get_windy_storm_track(windy_token, id)
                wind_speed = storm.get("windSpeed")
                if wind_speed:
                    typhoon_level = self.classify_typhoon(wind_speed)
                    print(f"typhoon_level={typhoon_level}")
                    track["strength"] = typhoon_level
                
                data.append(track)

            # 获取 zoom 的气旋和台风数据
            try:
                zoom_storms_list = self.get_zoom_storms_list(date_utc)
                print(f"zoom_storms_list={zoom_storms_list}")
                zoom_storms_list = zoom_storms_list.get("storms", [])
                for storm in zoom_storms_list:
                    # print(f"storm={storm}")
                    # 如果 storm 的值 分割-，取前一部分，然后看是否存在storms里，全部用小写对比
                    storm_id_prefix = storm.split(
                        '-')[0].lower() if isinstance(storm, str) else ""
                    # storms 是 windy 的 storms 列表
                    exists_in_storms = any(
                        (s.get("id", "").split('-')
                         [0].lower() == storm_id_prefix)
                        for s in storms if isinstance(s.get("id", ""), str)
                    )
                    print(
                        f"storm_id_prefix={storm_id_prefix}, exists_in_storms={exists_in_storms}")
                    if exists_in_storms:
                        # 修改 data 里面id 为 storm_id_prefix，然后修改 id 为 storm
                        for d in data:
                            if d.get("id", "").split('-')[0].lower() == storm_id_prefix:
                                d["id"] = storm

                        continue

                    track = self.get_zoom_storms_track(storm)
                    # print(f"track={track}")
                    zoom_data = self.convert_zoom_to_windy_format(track)
                    wind_speed = zoom_data.get("windSpeed")
                    if wind_speed:
                        typhoon_level = self.classify_typhoon(wind_speed)
                        print(f"typhoon_level={typhoon_level}")
                        zoom_data["strength"] = typhoon_level

                    # if not zoom_data.get("forecast"):
                    #     continue
                    # print(f"zoom_data={zoom_data}")
                    data.append(zoom_data)
                # print(f"data={data}")
            except Exception as e:
                traceback.print_exc()
            finally:
                # 设置缓存
                windy_current_storms = {
                    "data": data,
                    "fresh_time": dataTime
                }
                self.cache_rds.set("windy_current_storms",
                                   json.dumps(windy_current_storms))

        except Exception as e:
            traceback.print_exc()
