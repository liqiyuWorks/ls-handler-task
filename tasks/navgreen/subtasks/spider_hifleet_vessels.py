#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import pymongo
import requests
import datetime
from pkg.public.models import BaseModel
import traceback
import time
import os


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
        self.PAGE_START = int(os.getenv('PAGE_START', 87))
        self.PAGE_END = int(os.getenv('PAGE_END', 600))
        self.HIFLEET_VESSELS_LIMIT = int(os.getenv('HIFLEET_VESSELS_LIMIT', 200))
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', 20))
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'global_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING)
            ]
        }
        self.payload = {
            "offset": 1,
            "limit": self.HIFLEET_VESSELS_LIMIT,
            # "limit": 20,
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
                "sorttype": "desc",
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

    def update_hifleet_vessels(self, token, mmsi):
        try:
            # 调用 svc 查询 海科 request_svc_detail
            res = request_svc_detail(token, [mmsi])
            if res:
                self.mgo.set(None, res[0])
                print("更新数据", mmsi, "ok")
            else:
                print("更新数据", mmsi, "error")
        except Exception as e:
            traceback.print_exc()
            print("error:", res, e)

    @decorate.exception_capture_close_datebase
    def run(self):
        # token = get_check_svc_token(self.cache_rds)
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
            print(dataTime)
            for index in range(self.PAGE_START, self.PAGE_END):
                print(f"## 开始插入第 {index} 页的数据")
                self.payload["offset"] = index
                response = requests.request(
                    "POST", self.HIFLEET_VESSELS_LIST_URL, json=self.payload, headers=self.headers)
                if response.status_code == 200:
                    data = response.json().get("data", [])
                    if data == [] or data == None:
                        print("读取完成，运行结束...",response.text)
                        break
                    else:
                        for item in data:
                            # 优先使用 IMO 作为唯一键，跳过无效 IMO 的记录
                            imo_raw = item.get("imo")
                            try:
                                imo_val = int(imo_raw)
                            except (TypeError, ValueError):
                                imo_val = None

                            if not imo_val or imo_val <= 0:
                                print(f"跳过无效IMO记录: imo={imo_raw}, shipname={item.get('shipname')}")
                                continue

                            # 可选：规范化 mmsi 类型为 int（若存在且可转换）
                            try:
                                if item.get("mmsi") is not None:
                                    item["mmsi"] = int(item["mmsi"])
                            except (TypeError, ValueError):
                                pass

                            item["imo"] = imo_val

                            existing_record = self.mgo_db["global_vessels"].find_one({"imo": imo_val})
                            if not existing_record:
                                self.mgo.set(None, item)
                                print(f"插入新记录: imo={imo_val}")
                            else:
                                print(f"已存在，不插入，imo={imo_val}")
                            # else:
                            #     if existing_record["dwt"] is None or existing_record["dwt"] == 0 or existing_record["dwt"] == "" or existing_record["dwt"] == "******":
                            #         self.update_hifleet_vessels(token, int(item.get('mmsi')))

                time.sleep(self.time_sleep_seconds)

        except Exception as e:
            print("error:", e)
