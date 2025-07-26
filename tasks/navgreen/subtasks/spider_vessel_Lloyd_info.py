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


def get_check_voc_token(cache_rds):
    """检查和获取过期的海科 token """
    token = cache_rds.hget("voc:access_token", "access_token")
    print(token)
    return token


def request_voc_detail(token, imo_list):
    url = "https://voc.myvessel.cn/sdc/v1/ship/info/batch"
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "auth_app": "gee6af8f3v",
        "authorization": f"Bearer {token}",
        "content-type": "application/json",
        "origin": "https://voc.myvessel.cn",
        "priority": "u=1, i",
        "referer": "https://voc.myvessel.cn/microapps/dataship/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "xtoken": "bW9kZT10b2I7cHJvZD1WT0M7Y29tcGFueT1XWEpGS0pZWEdT",
        "Cookie": "user-language=zh_CN; HMACCOUNT=59B35BF0BBBA706E; WEBSOCKET_SESSION_ID=365e34b0aeee1948fecac346f2219091; Hm_lvt_ef2b526c8f49a47f15d2bfceb0841610=1751557869,1752390871; _tea_utm_cache_10000007=undefined; acw_tc=0a03334817533507260466571e63f51c8195d63184daa9ad7107afb23e22b6; Authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJiaXJ0aGRheSI6bnVsbCwiZ2VuZGVyIjoiLTEiLCJ1c2VyX25hbWUiOiIxNTE1MjYyNzE2MSIsIm9wZW5JZCI6Im8tOG5md2VkcnJQdGN6WTM2dlhiYTR0ZklnN2ciLCJyb2xlcyI6W10sInNlY3JldCI6bnVsbCwiY2xpZW50X2lkIjoic3dvcmQiLCJzY29wZSI6WyJhbGwiXSwibmlja25hbWUiOiJTaGFuZSBMZWUiLCJleHAiOjE3NTM0MzcxMjcsIm1hcCI6InN2IiwianRpIjoiMWEyMmZhYzEtNGQ0YS00MDljLWFjNzktZDQ2MmQ3Y2IxM2ViIiwiZW1haWwiOm51bGwsImNvbXBhbnlDb2RlIjoiV1hKRktKWVhHUyIsImFkZHJlc3MiOm51bGwsInByb2RzIjpudWxsLCJjb21wYW55TmFtZUVuIjpudWxsLCJtb2JpbGUiOiIxNTE1MjYyNzE2MSIsImNvbXBhbnlOYW1lQ24iOiLml6DplKHkuZ3mlrnnp5HmioDmnInpmZDlhazlj7giLCJhdmF0YXIiOiJodHRwczovL3RoaXJkd3gucWxvZ28uY24vbW1vcGVuL3ZpXzMyL05NcFpuVnNGQnQybnVQd2VBQU5KZ2pCbFlQZ3VWQTBIcE1yYjduT2RuMm55bkZkSXl5VmpUT3VGNVc1N2c3Z2IxNllPeFRhWmdlRmdjczN5OUZkcUp6RGw5Y3kyTUtJR3RHanY2Y0JFRWlhSS8xMzIiLCJ1c2VyTmFtZSI6IuadjuaYhyIsInVzZXJJZCI6IjFjNjhjZDRkYTQyYWYyNjBhMDg1NmI5NzVlZTQ0YzYxIiwicmVmcmVzaF9leHBpcmVzX2luIjo2MDQ4MDAsImNvbXBhbnlFeHBpcmVNaW5zIjpudWxsLCJzdGF0dXMiOjF9.tCyTZUyp11C22rfVMex3OBH9Vv9qq2y_AhydC_XJxxw; Hm_lpvt_ef2b526c8f49a47f15d2bfceb0841610=1753350731; sdc-session=e7e37931ba5e885fee7668be1e22a206; tfstk=gAfspZGP5iCEG_Axld4ENc3rX7OjHyPzGqTArZhZkCdtHisvYduwuPxvDgSpH1726ZIfkGGV7C7qS9jPyf5aIIlXsIAY4uPzaVbMiInr-csZIvL5JcH9MJRpFB0hLuPzaNI_J8GU4sy2jdxekIL9HhLLRUL2DIptBvUBkEotHhIYRyTXlVLvHFHdJFYWMnIvMy_pxEdvWidx65uWlRtG5zgMmP43Br_DAjhAOeEDcNiqHHXW5dtRW1_Pr6G6C3Q9AjElBq3vvU1Lmc-cOwC9oMFE1I_plgOOdkh1cNBlmUITOcL1Ba_ydsq-GeXdjp81drHpXaKM6H10ojxOQZC2h1E-uhCGb69licZe0T7F6ps8YXsDhOBJ6sZ79gyoa3OamxgBEjTB4yaInxv0QHdh5CuWLdLH5pzQRcBmqjhrZszIH599-FT_RyiOn",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"


    }

    payload = {"lrnoList": imo_list, "mmsiList": []}
    response = requests.request("POST", url, json=payload, headers=headers)
    print(response.json())
    return response.json().get("data", [])


class SpiderVesselsLloydInfo(BaseModel):
    def __init__(self):
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', 10))
        # "客船,干散货-ok,杂货船-ok,液体散货,特种船,集装箱"]
        self.batch_size = int(os.getenv('BATCH_SIZE', 100))
        # self.hifleet_types = os.getenv('HIFLEET_TYPES', None)
        self.hifleet_types = os.getenv('HIFLEET_TYPES', "集装箱船")
        if self.hifleet_types:
            self.hifleet_types = self.hifleet_types.split(",")
        else:
            self.hifleet_types = []
        self.vessel_types = os.getenv('VESSEL_TYPES', "特种船")
        if self.vessel_types:
            self.vessel_types = self.vessel_types.split(",")
        else:
            self.vessel_types = []
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'hifleet_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING),
                ('mmsi', pymongo.ASCENDING),
            ]
        }

        super(SpiderVesselsLloydInfo, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
            print(dataTime)
            
            if self.hifleet_types:
                imo_list = self.mgo_db["hifleet_vessels"].find({
                    "imo": {
                        "$exists": True,
                        "$ne": "None",
                        "$ne": "0",
                        "$ne": None,
                        "$ne": ""
                    },
                    "type": {"$in": self.hifleet_types}
                }).distinct("imo")
            else:
                imo_list = self.mgo_db["hifleet_vessels"].find({
                    "imo": {
                        "$exists": True,
                        "$ne": "None",
                        "$ne": "0",
                        "$ne": None,
                        "$ne": ""
                    },
                    "vesselTypeNameCn": {"$in": self.vessel_types}
                }).distinct("imo")

            # 获取已存在的lrno列表
            existing_lrno_list = self.mgo_db["Lloyd_info_vessels"].distinct(
                "lrno")
            # imo_list与已存在的lrno去重
            INVALID_IMO_VALUES = {None, "", "None",
                                  "0", "0000000", "12211", "123", "111", "128"}
            imo_list_after_deduplication = [
                imo for imo in reversed(imo_list)
                if imo not in existing_lrno_list and imo not in INVALID_IMO_VALUES
            ]
            print(len(imo_list), len(imo_list_after_deduplication))
            # print(imo_list_after_deduplication)

            # imo_list按照 1000 个一个数组，拆分循环
            batch_size = self.batch_size
            token = get_check_voc_token(self.cache_rds)
            imo_batches = [imo_list_after_deduplication[i:i + batch_size]
                           for i in range(0, len(imo_list_after_deduplication), batch_size)]
            for batch in imo_batches:
                try:
                    print(f"Processing batch of {len(batch)} IMOs")
                    print(batch)
                    res = request_voc_detail(token, batch)
                    for item in res:
                        lrno = item.get("fmShipDTO", {}).get("lrno")
                        print(lrno, " -- 插入完成")
                        # 如果以imo为主键，存在则更新，不存在则插入（upsert=True已实现此逻辑）
                        # 插入更新时间
                        item["update_time"] = datetime.datetime.now()
                        self.mgo_db["Lloyd_info_vessels"].update_one(
                            {"lrno": lrno}, {"$set": item}, upsert=True)
                except Exception as e:
                    print(f"Error processing item: {e}")
                    traceback.print_exc()
                    break

                time.sleep(self.time_sleep_seconds)

        except Exception as e:
            traceback.print_exc()
            print("error:", e)
