#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import pymongo
from pkg.util.spider import parse_url
from pkg.util.format import time2time
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from lxml import etree
from tasks.typhoon.subtasks.ssec_realtime_sync_mgo import SsecSyncMgo

month_abbr_list = [
    '', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'
]


class NoaaSyncMgo(BaseModel):
    def __init__(self):
        config = {
            'collection': 'noaa_realtime_data',
            'uniq_idx': [('reporttime', pymongo.ASCENDING),
                         ('stormid', pymongo.ASCENDING)]
        }
        super(NoaaSyncMgo, self).__init__(config)
        self.url_index = "https://www.ssd.noaa.gov/PS/TROP/adt.html"

    def handle_storm(self, item, Storm_url):
        r = parse_url(Storm_url)
        if r.status_code == 200:
            rows = str(r.text).split('\n')
            for line in rows[4:-1]:
                item["Date"] = line[:10].strip()
                item["Time"] = line[10:17].strip()
                logging.info(f'{item["Date"]}:{item["Time"]}')
                # item["CI"] = line[17:22].strip()
                item["minp"] = float(line[22:29].strip())   # MinP = MSLP
                item["maxsp"] = float(line[29:35].strip())  # MaxSP = Vmax
                # item["Fnl_Tno"] = line[35:40].strip()
                # item["Adj_Raw"] = line[40:44].strip()
                # item["Ini_Raw"] = line[44:48].strip()
                # item["Limit"] = line[48:59].strip()
                # item["Wkng_Flag"] = line[59:63].strip()
                # item["Rpd_Wkng"] = line[63:68].strip()
                # item["ET_Flag"] = line[68:73].strip()
                # item["ST_Flag"] = line[73:78].strip()
                # item["Cntr_Region"] = line[78:85].strip()
                # item["Mean_Cloud"] = line[85:92].strip()
                # item["Scene_Type"] = line[92:100].strip()
                # item["EstRMW"] = line[100:107].strip()
                # item["MW_Score"] = line[107:113].strip()
                item["lat"] = float(line[113:121].strip())
                item["lon"] = float(line[121:129].strip())*(-1)
                # item["Fix_Mthd"] = line[129:136].strip()
                # item["Sat"] = line[137:145].strip()
                # item["VZA"] = line[145:151].strip()
                # item["Comments"] = line[151:].strip()
                Date = item['Date']
                Date = Date[4:7]
                reporttime_str = item['Date'][:4] + '{:02d}'.format(month_abbr_list.index(Date)) + item['Date'][7:] + item['Time']
                item['reporttime'] = time2time(reporttime_str, "%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S")
                item.pop('Date', None)
                item.pop('Time', None)
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
                    a_list = td.xpath('./center')
                    for i in a_list:
                        a_list = i.xpath('./a')
                        if a_list:
                            item = {}
                            item['sea_area'] = ocean_names_list[index].xpath('./div/text()')[0]
                            item['stormid']= i.xpath("./a[1]/strong/text()")[0]
                            Storm_url= i.xpath("./a[1]/@href")[0]
                            print(Storm_url)
                            # 查询 noaa 的数据
                            for item in self.handle_storm(item,Storm_url):
                                self.mgo.set(None, item)
                            logging.info('Noaa 的数据导入成功！')

                            ## 查询 ssec 的数据
                            SsecSyncMgo(storm_id=item['stormid'], sea_area = item['sea_area']).run()
                            logging.info('Ssec 的数据导入成功！')