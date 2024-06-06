#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import re
import datetime
from lxml import html
import pymongo
import requests
from pkg.public.models import BaseModel


class SpiderHyfocus(BaseModel):
    AREA_DICT = {
        0: "East Asia",
        1: "South East Asia",
        2: "South Asia",
        3: "Pacific",
    }
    HYFOCUS_URL = "https://www.hyqfocus.com/m/bunker_by_mini_area.jsp?areaFlagRow=0&areaRow={}&app="

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'hy_focus_oil_prices',
            'uniq_idx': [
                ('title', pymongo.ASCENDING),
                ('date', pymongo.ASCENDING),
            ]
        }
        super(SpiderHyfocus, self).__init__(config)

    def fetch_data(self, url, dataTime, area):
        res = requests.get(url=url)
        if res.status_code == 200:
            # print(res.content)
            tree = html.fromstring(res.content)
            # trs = tree.xpath('/html/body/div[1]/div[2]/div[1]/table/tbody//tr')
            # ths = tree.xpath('//*[@class="row"]/th//text()')
            trs = tree.xpath(
                '/html/body/div[1]/div[2]/div[1]/table/tbody/tr')
            # for th in ths:
            #     print('--', str(th).strip())

            item = {"area": area}
            for tr in trs:
                item["title"] = str(tr.xpath("./th/a/text()")
                                    [0]).replace("\\r\\n", "").strip()
                item["IFO380"] = tr.xpath(
                    "./td[1]/div[1]/text()  | ./td[1]/span/text()")[0]
                item["VLSFO"] = tr.xpath(
                    "./td[2]/div[1]/text()  | ./td[2]/span/text()")[0]
                item["MGO"] = tr.xpath(
                    "./td[3]/div[1]/text()  | ./td[3]/span/text()")[0]
                item["date"] = tr.xpath(
                    "./td[4]/div[1]/text()  | ./td[4]/span/text()")[0]

                if item["date"] <= dataTime[5:]:
                    item["date"] = dataTime[:5] + item["date"]
                else:
                    item["date"] = str(int(dataTime[:4])-1) + "-" + item["date"]
                self.mgo.set(None, item)

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d")
        print("当前时间是：", dataTime)
        for i in range(0, 4):
            url = self.HYFOCUS_URL.format(i)
            print(url)
            self.fetch_data(url, dataTime, self.AREA_DICT[i])
