#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import os
import pymongo
import requests
import datetime
from pkg.public.models import BaseModel
from pkg.public.wechat_push import WechatPush, PrefixEnums

class JDGoldPushWechat(BaseModel):
    LAST_BUY_PRICE = int(os.getenv('LAST_BUY_PRICE', '370'))
    JD_GOLD_URL = "https://api.jdjygold.com/gw/generic/hj/h5/m/latestPrice"

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'jd_gold_prices',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
            ]
            }
        super(JDGoldPushWechat, self).__init__(config)

    def compared_buyed_price(self,price):
        diff = round((price - self.LAST_BUY_PRICE)/price*100,2)
        if diff < 0:
            # 发送微信通知
            notify_user = WechatPush()
            notify_user.notify(prefix=f"[{PrefixEnums.gold.value}]: ", msg=f"\n当前京东积存金：{price} \n变动幅度：{diff}% \n推荐入手~")
            self.LAST_BUY_PRICE = price


    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        res = requests.get(url=self.JD_GOLD_URL)
        if res.status_code == 200:
            res = res.json()
            resultData = res.get("resultData",{}).get("datas")
            price = float(resultData.get('price'))
            yesterdayPrice = float(resultData.get('yesterdayPrice'))
            # print(f"current gold price: {price}, yesterdayPrice: {yesterdayPrice}")
            item = {"dataTime":dataTime, "price":price, "yesterdayPrice":yesterdayPrice}
            self.compared_buyed_price(price)
            self.mgo.set(None, item)


