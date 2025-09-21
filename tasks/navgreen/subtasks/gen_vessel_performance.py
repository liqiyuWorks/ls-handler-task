#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import pymongo
import requests
import json
from pkg.public.models import BaseModel
import time
import traceback
from datetime import datetime


def get_check_svc_token(cache_rds):
    """检查和获取过期的海科 token """
    token = cache_rds.hget("svc", "access_token")
    return token


def request_mmsi_detail(mmsi):
    url = "https://api.navgreen.cn/api/performance/vessel/speed"

    querystring = {"mmsi": mmsi, "version": "v1"}

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

    return response.json().get("data", [])


def request_mmsi_performance(mmsi):
    try:
        url = "https://api.navgreen.cn/api/analyze/v2/speed"

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

    return response.json().get("data", [])


class GenVesselPerformance(BaseModel):

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'hifleet_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }

        super(GenVesselPerformance, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            vessels = self.mgo_db["hifleet_vessels"].find(
                {"vesselTypeNameCn": "干散货", "mmsi": {"$exists": True}, "perf_updated": {"$ne": 1}, "request_hi_weather": {"$ne": 0}}, {"mmsi": 1, '_id': 0})

            # print("total num", len(list(vessels)))
            for vessel in vessels:
                print(vessel)
                # 请求我的接口
                try:
                    res = request_mmsi_detail(vessel["mmsi"])
                    print(res)
                except Exception as e:
                    print("error:", e)
                else:
                    # 更新船舶perf_updated字段为1
                    if res:
                        self.mgo_db["hifleet_vessels"].update_one(
                            {"mmsi": vessel["mmsi"]},
                            {"$set": {"perf_updated": 1}}
                        )
                    else:
                        self.mgo_db["hifleet_vessels"].update_one(
                            {"mmsi": vessel["mmsi"]},
                            {"$set": {"request_hi_weather": 0}}
                        )

                time.sleep(1)

        except Exception as e:
            print("error:", e)


class GenVesselPerformanceFromRDS(BaseModel):

    def __init__(self):
        config = {
            "cache_rds": True,
        }

        super(GenVesselPerformanceFromRDS, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            # 从rds hget 所有的字段
            vessels = self.cache_rds.hgetall("vessels_performance_v1|202505")

            for vessel_key, vessel_data in vessels.items():
                try:
                    vessel = json.loads(vessel_data)
                    print(vessel)
                    # 入计算油耗队列
                    task = {
                        'task_type': "handler_calculate_vessel_performance",
                        'process_data': vessel
                    }
                    self.cache_rds.rpush(
                        "handler_calculate_vessel_performance", json.dumps(task))
                    print(f"已推送mmsi={vessel.get('mmsi')}的船舶进入油耗计算队列")
                except json.JSONDecodeError as e:
                    print(f"Error parsing vessel data: {e}")
                    continue

        except Exception as e:
            print("error:", e)


class GenVesselVPFromMGO(BaseModel):

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'hifleet_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }
        super(GenVesselVPFromMGO, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        try:

            vessels = self.mgo_db["hifleet_vessels"].find({"vesselTypeNameCn": {
                                                          "$in": ["杂货船", "干散货"]}, "mmsi": {"$exists": True}}, {"mmsi": 1, '_id': 0})

            total_num = vessels.count()
            num = 0
            for vessel in vessels:
                num += 1
                year_month = datetime.now().strftime("%Y%m")
                vessel_data = self.cache_rds.hget(
                    f"vessels_performance_v2|{year_month}", vessel["mmsi"])
                if vessel_data:
                    res = json.loads(vessel_data)
                    continue
                    if res.get("avg_fuel") and res.get("avg_good_weather_speed"):
                        print(f"mmsi={vessel['mmsi']} 已计算过")
                        continue
                try:
                    res = request_mmsi_performance(vessel["mmsi"])
                    print(f"mmsi={vessel['mmsi']} 计算成功")
                except Exception as e:
                    traceback.print_exc()
                print(f"已计算{num}/{total_num} 进度：{round((num / total_num) * 100, 2)}%")
                time.sleep(2)

        except Exception as e:
            traceback.print_exc()
