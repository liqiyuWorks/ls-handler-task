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


class RichHifleetVesselsInfo(BaseModel):
    HIFLEET_VESSELS_LIST_URL = "https://www.hifleet.com/particulars/getShipDatav3"

    def __init__(self):
        self.batch_size = int(os.getenv('BATCH_SIZE', 1000))
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', 10))
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'hifleet_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }
        super(RichHifleetVesselsInfo, self).__init__(config)

    def update_hifleet_vessels(self, token, mmsi_list):
        try:
            # 调用 svc 查询 海科 request_svc_detail
            res = request_svc_detail(token, mmsi_list)
            print(res)
            if res:
                for item in res:
                    # if item["imo"] is None or item["imo"] == "":
                    #     del item["imo"]
                    self.mgo.set(None, item)
                    print("更新数据", item["mmsi"], "ok")
        except Exception as e:
            traceback.print_exc()
            print("error:", res, e)

    @decorate.exception_capture_close_datebase
    def run(self):
        token = get_check_svc_token(self.cache_rds)
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
            print(dataTime)

            existing_record_list = list(self.mgo_db["hifleet_vessels"].find(
                {
                    "mmsi": {"$exists": True},
                    "$or": [
                        {"updated_at": {"$exists": False}},
                        {"updated_at": "updated_at"}
                    ]
                },
                {"_id": 0, "imo": 1, "mmsi": 1, "dwt": 1, "type": 1}
            ).sort("mmsi", -1))

            mmsi_list = [int(item["mmsi"]) for item in existing_record_list if "mmsi" in item]
            print(len(mmsi_list))   
            batch_size = self.batch_size
            batches = [mmsi_list[i:i + batch_size]
                       for i in range(0, len(mmsi_list), batch_size)]
            for batch in batches:
                print(batch)
                self.update_hifleet_vessels(token, batch)
                time.sleep(self.time_sleep_seconds)

        except Exception as e:
            print("error:", e)
