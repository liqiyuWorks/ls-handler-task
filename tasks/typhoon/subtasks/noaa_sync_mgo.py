#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, logging
import pymongo
import pandas as pd
from pkg.util.spider import parse_url
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from lxml import etree
from tasks.typhoon.subtasks.ssec_sync_mgo import SsecSyncMgo

MGO_FIELD = [
    "Date", "Time", "CI", "MSLP", "Vmax", "Fnl_Tno", "Adj_Raw", "Ini_Raw",
    "Limit", "Wkng_Flag", "Rpd_Wkng", "ET_Flag", "ST_Flag", "Cntr_Region",
    "Mean_Cloud", "Scene_Type", "EstRMW", "MW_Score", "Lat", "Lon", "Fix_Mthd",
    "Sat", "VZA", "Comments"
]
month_abbr_list = [
    '', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT',
    'NOV', 'DEC'
]


class NoaaSyncMgo(BaseModel):
    def __init__(self):
        config = {
            'collection': 'noaa_data',
            'uniq_idx': [('dataTime', pymongo.ASCENDING),
                         ('StormID', pymongo.ASCENDING),
                         ('sea_area', pymongo.ASCENDING)]
        }
        super(NoaaSyncMgo, self).__init__(config)
        self.url_index = "https://www.ssd.noaa.gov/PS/TROP/adt.html"

    def handle_storm(self, item, Storm_url):
        r = parse_url(Storm_url)
        if r.status_code == 200:
            rows = str(r.text).split('\n')
            for line in rows[4:-1]:
                item["Date"] = line[:10].strip()
                item["Time"] = line[10:16].strip()
                item["CI"] = line[16:21].strip()
                item["MSLP"] = line[21:28].strip()
                item["Vmax"] = line[28:34].strip()
                item["Fnl_Tno"] = line[34:39].strip()
                item["Adj_Raw"] = line[39:43].strip()
                item["Ini_Raw"] = line[43:47].strip()
                item["Limit"] = line[47:59].strip()
                item["Wkng_Flag"] = line[59:62].strip()
                item["Rpd_Wkng"] = line[62:67].strip()
                item["ET_Flag"] = line[67:72].strip()
                item["ST_Flag"] = line[72:77].strip()
                item["Cntr_Region"] = line[77:84].strip()
                item["Mean_Cloud"] = line[84:91].strip()
                item["Scene_Type"] = line[91:99].strip()
                item["EstRMW"] = line[99:106].strip()
                item["MW_Score"] = line[106:112].strip()
                item["Lat"] = line[112:120].strip()
                item["Lon"] = line[120:128].strip()
                item["Fix_Mthd"] = line[128:138].strip()
                item["Sat"] = line[138:144].strip()
                item["VZA"] = line[144:150].strip()
                item["Comments"] = line[150:].strip()
                Date = item['Date']
                Date = Date[4:7]
                item['dataTime'] = item['Date'][:4] + '{:02d}'.format(
                    month_abbr_list.index(
                        Date)) + item['Date'][7:] + item['Time']
                item.pop('Date')
                item.pop('Time')
                yield item

    @decorate.exception_capture_close_datebase
    def run(self):
        r = parse_url(self.url_index)
        if r.status_code == 200:
            html_xpath = etree.HTML(r.text)
            tables = html_xpath.xpath('//*[@class="padding5"]/table')
            for table in tables[1:]:
                ocean_names_list = table.xpath(".//tr[2]")[0]
                storm_names = table.xpath(".//tr[3]/td")
                for index,td in enumerate(storm_names):
                    item = {}
                    a_list = td.xpath('./center/a')
                    if a_list:
                        item['sea_area'] = ocean_names_list[index].xpath('./div/text()')[0]
                        item['StormID']= td.xpath("./center/a[1]/strong/text()")[0]
                        Storm_url= td.xpath("./center/a[1]/@href")[0]
                        ## 查询 noaa 的数据
                        for item in self.handle_storm(item,Storm_url):
                            self.mgo.set(None, item)
                        print('Noaa 的数据导入成功！')

                        ## 查询 ssec 的数据
                        SsecSyncMgo(storm_id=item['StormID'], sea_area = item['sea_area']).run()
                        print('Ssec 的数据导入成功！')