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


class SpiderHifleetVessels(BaseModel):
    HIFLEET_VESSELS_LIST_URL = "https://www.hifleet.com/particulars/getShipDatav3"

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
        self.payload = {
            "offset": 1,
            "limit": 2000,
            "_v": "5.3.588",
            "params": {
                "shipname": "",
                "callsign": "",
                "shiptype": "",
                "shipflag": "",
                "keyword": "",
                "mmsi": -1,
                "imo": -1,
                "shipagemin": -1,
                "shipagemax": -1,
                "loamin": -1,
                "loamax": -1,
                "dwtmin": -1,
                "dwtmax": -1,
                "sortcolumn": "shipname",
                "sorttype": "asc",
                "isFleetShip": 0
            }
        }

        self.headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://www.hifleet.com",
            "Referer": "https://www.hifleet.com/vessels/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Host": "www.hifleet.com",
            "Content-Length": "474"
        }
        super(SpiderHifleetVessels, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        token = get_check_svc_token(self.cache_rds)
        try:
            # dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
            print(token)
            # for index in range(1, 70):
            #     print(f"## 开始插入第 {index} 页的数据")
            #     self.payload["offset"] = index
            #     response = requests.request(
            #         "POST", self.HIFLEET_VESSELS_LIST_URL, json=self.payload, headers=self.headers)
            #     if response.status_code == 200:
            #         data = response.json().get("data")

            #     mmsi_list = [item['mmsi'] for item in data]
            #     mmsi_list = list(dict.fromkeys(mmsi_list))

            #     # 调用 svc 查询 海科 request_svc_detail
            #     res = request_svc_detail(token, mmsi_list)
            #     for item in res:
            #         self.mgo.set(None, item)

        except Exception as e:
            print("error:", e)
