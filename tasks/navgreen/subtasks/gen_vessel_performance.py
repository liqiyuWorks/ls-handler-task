#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import pymongo
import requests
import time
from pkg.public.models import BaseModel


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
                {"vesselTypeNameCn": "干散货", "mmsi": {"$exists": True}, "perf_updated": {"$ne": 1}}, {"mmsi": 1, '_id': 0})

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

        except Exception as e:
            print("error:", e)
