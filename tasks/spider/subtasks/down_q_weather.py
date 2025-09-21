#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os
import re
import logging
from lxml import etree
import requests
import datetime
import pandas as pd

class DownQWeather():
    STATION_ID = 57039
    REQ_URL = "https://q-weather.info/weather/{}/history/?date={}"

    def __init__(self):
        start_day = os.getenv('START_DAY', '2021-10-06')
        end_day = os.getenv('END_DAY', '2021-10-18')
        self._days = self.calc_days(start_day, end_day)
        self.new_rows = []

    def calc_days(self,start, end):
        start_day = re.search(r'\d{4}-\d{2}-\d{2}', start).group(0)
        start_day_time = datetime.datetime.strptime(start_day, '%Y-%m-%d')
        end_day = re.search(r'\d{4}-\d{2}-\d{2}', end).group(0)
        end_day_time = datetime.datetime.strptime(end_day, '%Y-%m-%d')
        print(f"start_day_time={start_day_time} , end_day_time={end_day_time}")
        days = [start_day_time + datetime.timedelta(days=x) for x in range((end_day_time-start_day_time).days + 1)]
        return days

    def parse_html(self, response):
        try:
            data = []
            html_xpath = etree.HTML(response.text)
            table = html_xpath.xpath('/html/body/center/table/tbody/tr')
            for tr in table:
                item = {}
                item["dataTime"] = tr.xpath("./td[1]/text()")[0].replace("(","").replace(")","") if tr.xpath("./td[1]/text()") else None
                item["TEM"] = float(tr.xpath("./td[2]/text()")[0].replace("(","").replace(")","")) if tr.xpath("./td[2]/text()") else None
                item["PRS"] = float(tr.xpath("./td[3]/text()")[0].replace("(","").replace(")","")) if tr.xpath("./td[3]/text()") else None
                item["RHU"] = float(tr.xpath("./td[4]/text()")[0].replace("(","").replace(")","")) if tr.xpath("./td[4]/text()") else None
                item["WIN_D_Avg_2mi"] = tr.xpath("./td[5]/text()")[0].replace("(","").replace(")","") if tr.xpath("./td[5]/text()") else None
                item["WIN_S_Avg_2mi"] = float(tr.xpath("./td[6]/text()")[0].replace("(","").replace(")","")) if tr.xpath("./td[6]/text()") else None
                item["PRE_1h"] = float(tr.xpath("./td[8]/text()")[0].replace("(","").replace(")","")) if tr.xpath("./td[8]/text()") else None

                if item["dataTime"]:
                    item["dataTime"] = item["dataTime"][:16]+":00"
                if item["WIN_D_Avg_2mi"]:
                    item["WIN_D_Avg_2mi"] = float(str(item["WIN_D_Avg_2mi"]).split('/')[0])
                data.append(item)
            return data
        except Exception as e:
            logging.error(e)

    def to_csv(self,index, res):
        ColumnsName=["dataTime","TEM","PRS","RHU","WIN_D_Avg_2mi","WIN_S_Avg_2mi","PRE_1h"]
        df = pd.DataFrame(columns=ColumnsName, data=res)
        if index == 0:
            df.to_csv(f"长安.csv",index=True,sep=',', mode='a',header=True)
        else:
            df.to_csv(f"长安.csv",index=True,sep=',', mode='a',header=False)

    def run(self):
        for index, day in enumerate(self._days):
            day = day.strftime('%Y-%m-%d')
            print(f"index={index}, day={day}")
            time.sleep(5)
            res = requests.get(url=self.REQ_URL.format(self.STATION_ID, day))
            if res.status_code == 200:
                res = self.parse_html(res)
                self.to_csv(index, res)
                print(f"{day} write ok ...")
                


