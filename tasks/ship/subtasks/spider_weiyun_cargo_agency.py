#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import time
import datetime
import random
import pymongo
import requests
from pkg.public.models import BaseModel


class SpiderWeiyunCargoAgencies(BaseModel):
    AREA_DICT = {
        0: "East Asia",
        1: "South East Asia",
        2: "South Asia",
        3: "Pacific",
    }
    AGENCY_URL = "https://xcx.weiyun001.com/yellow/getCommon"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'weiyun_cargo_agencies',
            'uniq_idx': [
                ('id', pymongo.ASCENDING),
                ('agency_name', pymongo.ASCENDING),
            ]
        }
        super(SpiderWeiyunCargoAgencies, self).__init__(config)
        self.locals = list(self.mgo.mgo_db["local_ids"].find(
            {}, {'_id': 0}))
        self.areas = list(self.mgo.mgo_db["area_ids"].find(
            {}, {'_id': 0}))
        self.carriers = list(
            self.mgo.mgo_db["carrier_ids"].find({}, {'_id': 0}))
        # print(self.locals)
        # print(self.areas)
        # print(self.carriers)

    def fetch_data(self, local_id, carrier_id={}, area_id={}):
        data = {
            "local_id": local_id["id"],
            # "carrier_id": carrier_id,
            # "area_id": area_id,
            "token": "13f8d17ee4369f2e",
            "timestamp": 1710313096
        }
        if carrier_id and area_id:
            data["carrier_id"] = carrier_id["company_id"]
            data["area_id"] = area_id["id"]

        res = requests.post(url=self.AGENCY_URL, params=data)
        if res.status_code == 200:
            msgs = res.json().get("message")

            if not msgs:
                return
            for i in msgs:
                i["area_name"] = local_id["area_name"]
                # i["carrier_name"] = carrier_id["company_name"]
                # i["title"] = area_id["title"]
                self.mgo.set(None, i)
                print("--> ", i["agency_name"], "校验成功")

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d")
        print("当前时间是：", dataTime)
        for local_id in self.locals:
            time.sleep(random.random() * 3)
            for carrier_id in self.carriers:
                time.sleep(random.random() * 2)
                for area_id in self.areas:
                    time.sleep(random.random() * 1)
                    # print(local_id["id"], carrier_id["company_id"],
                    #       area_id["id"])
                    self.fetch_data(
                        local_id, carrier_id, area_id)

    @decorate.exception_capture_close_datebase
    def run_local(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d")
        print("当前时间是：", dataTime)
        for local_id in self.locals:
            time.sleep(random.random() * 3)
            self.fetch_data(local_id["id"])
