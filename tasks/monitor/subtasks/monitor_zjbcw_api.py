#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import requests
import datetime


class MonitorBCWApis:
    def __init__(self):
        self.TD_URL = "124.70.86.179:6041"

    @decorate.exception_capture
    def run(self):
        date = (datetime.datetime.utcnow() +
                datetime.timedelta(days=+7)).strftime("%Y%m%d145400")

        url = "http://devapi.ninecosmos.cn/api/bcw/v1/ocean/date_00?access_key=LS8A9EF19641FBB5CD8AB7EFE25F1A75&timestamp=1682322569&sign=2ECC54AAAD6FFADB69137C677E8D7142"

        data = {
            "date_time": str(date),
            "latitude": "39.2332",
            "longitude": "119.324",
            "days": 1
        }
        res = requests.post(url, json=data)
        if res.status_code == 200:
            data = res.json().get("data")
            
            if len(data) > 1:
                print("data len = ", len(data))
            else:
                raise Exception("date_00-数据有问题, 请及时上线查看")
        else:
            raise Exception("请求失败")
