#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import re
import datetime
from lxml import html
import pymongo
import requests
from pkg.public.models import BaseModel


class SpideSol(BaseModel):

    SOL_URL = "http://supply.sol.com.cn/productList.asp?/{}.html"
    
    # 定义要替换的字符集合
    characters_to_replace = r"[\\xa0]"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'hy_sol',
            'uniq_idx': [
                ('bianhao', pymongo.ASCENDING),
                ('name', pymongo.ASCENDING),
            ]
        }
        super(SpideSol, self).__init__(config)

    def fetch_data(self, url):
        for i in range(200,300):
            res = requests.get(url=url.format(i))
            items = []
            if res.status_code == 200:
                # print(res.content)
                tree = html.fromstring(res.content)

                divs = tree.xpath(
                    '/html/body/div[3]/div[2]/div[3]/div')
                print(divs)

                for div in divs[1:]:
                    item ={}
                    print(div)
                    item["bianhao"] = str(div.xpath("./table/tr/td[2]/span/text()")[0])
                    item["name"] = str(div.xpath("./table/tr/td[2]/h2/a//text()")[0]).replace("\xa0"," ")
                    item["text"] = str(div.xpath("./table/tr/td[2]//text()")).replace("\\r\\n", "").replace("\\u3000\\u3000","").replace("\\xa0"," ").strip()

                    print(item)
                    self.mgo.set(None, item)
                    # break

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d")
        print("当前时间是：", dataTime)
        self.fetch_data(self.SOL_URL)
