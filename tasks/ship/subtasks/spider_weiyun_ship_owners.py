#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import time
import datetime
import random
import pymongo
import requests
from pkg.public.models import BaseModel
import os

HEADERS = {
    'content-type': 'application/json',  # 重要
    'referer': 'https://servicewechat.com/wx74cf9a63bf01c142/106/page-frame.html',
    "host": 'xcx.weiyun001.com',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.47(0x18002f2c) NetType/WIFI Language/zh_CN'
}


class SpiderWeiyunShipOwners(BaseModel):
    REQ_URL = "https://xcx.weiyun001.com/getIndustry/getBase/local_id/{}?token=ec15e0d053a52e32&timestamp=1710321611&log_id=245482"
    CARRIER_DESC_URL = "https://xcx.weiyun001.com/getIndustry/getCarrier?carrier_id={}&token=2a904c311c3a2cfd&timestamp=1710396737&log_id=245672"
    DEPARTMENT_URL = "https://xcx.weiyun001.com/GetContact/fromDepartment?department_id={}&token=4fd94f7762ebfd42&timestamp=1710387188&log_id=245482"
    RANDOM_NUM = int(os.getenv("RANDOM_NUM", 3))

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'weiyun_ship_owners',
            'uniq_idx': [
                ('company_id', pymongo.ASCENDING),
                ('company_name', pymongo.ASCENDING),
            ]
        }
        super(SpiderWeiyunShipOwners, self).__init__(config)
        self.locals = list(self.mgo.mgo_db["local_ids"].find({}, {'_id': 0}))
        self.ship_owners = list(
            self.mgo.mgo_db["weiyun_ship_owners"].find({}, {'_id': 0}))

    def request(self, url):
        # print(url)
        time.sleep(random.random() * 1)
        res = requests.get(url=url, headers=HEADERS)
        return res

    def get_compy_desc(self, item, company_id):
        url = self.CARRIER_DESC_URL.format(company_id)
        time.sleep(random.random() * self.RANDOM_NUM)
        res = self.request(url)
        data = res.json().get("data")
        if data:
            item.update(data)
        return item

    def get_departments(self, item):
        departments = item.get("departments", [])
        if not departments:
            return item
        for dep in departments:
            # print(dep)
            title = dep['title']
            res = self.request(self.DEPARTMENT_URL.format(dep['id']))
            data = res.json().get("data", [])
            # print(title, data)
            item[title] = data
        return item

    def fetch_data(self, local_id):
        url = self.REQ_URL.format(local_id["id"])
        res = self.request(url)
        if res.status_code == 200:
            carriers = res.json().get("carrier_list")

            if not carriers:
                return
            for item in carriers:
                time.sleep(random.random() * 3)
                item["area_name"] = local_id["area_name"]
                # 拿到公司的简介信息
                company_id = item["company_id"]
                # print(company_id)
                item = self.get_compy_desc(item, company_id)
                # 根据departments 去拿 销售部 客服部 操作部的人员信息
                item = self.get_departments(item)

                self.mgo.set(None, item)
                # print(item)
                print("--> ", item["company_name_en"], "校验成功")
                # break

    @decorate.exception_capture_close_datebase
    def run_once(self):
        for item in self.ship_owners:
            company_id = item["company_id"]
            
            if item.get("address"):
                continue
            time.sleep(random.random() * self.RANDOM_NUM)
            # print(company_id)
            item = self.get_compy_desc(item, company_id)
            # 根据departments 去拿 销售部 客服部 操作部的人员信息
            item = self.get_departments(item)
            self.mgo.set(None, item)
            print(item)
            print("--> ", item["company_name_en"], "校验成功")
            # break

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d")
        print("当前时间是：", dataTime)
        for local_id in self.locals:
            time.sleep(random.random() * 3)
            self.fetch_data(local_id)
            break
