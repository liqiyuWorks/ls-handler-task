#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from copy import deepcopy
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
            'uniq_idx': [('stormid', pymongo.ASCENDING),
                         ('year', pymongo.ASCENDING),
                         ('sea_area', pymongo.ASCENDING)
                         ],
            "idx_dic": {'embedded_idx': [('datatime.reporttime', pymongo.ASCENDING)]}  # 建立嵌套时间的索引
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
                # logging.info(f'{item["Date"]}:{item["Time"]}')
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

    def insert_noaa_datatime(self,id,item):
        datatime = deepcopy(item)
        aggregate_query = [{
            "$unwind": "$datatime"
        }, {
            "$match": {
                "_id": id,
                "datatime.reporttime": item['reporttime'],
            }
        }, {
            "$project": {
                "datatime": 1
            }
        }]
        res = list(self.mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            # logging.info("已有该时刻实测数据，准备更新....")
            r = self.mgo.mgo_coll.update_one(
                {
                    "_id": id,
                    "datatime.reporttime": item['reporttime']
                }, {
                    "$set": {
                        "end_reporttime": item['reporttime'],
                        "lat": item['lat'],
                        "lon": item['lon'],
                        "datatime.$.lat": item.get('lat'),
                        "datatime.$.lon": item.get('lon'),
                        "datatime.$.minp": item.get('minp'),
                        "datatime.$.maxsp": item.get('maxsp'),
                    }
                },
                upsert=True)

        else:
            datatime.pop("sea_area")
            datatime.pop("stormid")
            datatime.pop("year")
            r = self.mgo.mgo_coll.update({
                "_id": id,
            }, {
                "$set": {
                    "end_reporttime": item['reporttime'],
                    "lat": item['lat'],
                    "lon": item['lon'],
                    "year": item['year']
                },
                "$push": {
                    "datatime": datatime
                }
            })
            print("noaa realtime 嵌套新增成功res", r)

    def save_noaa(self, item):
        item['year'] =  str(item['reporttime'])[:4]
        data = {
            "stormid": item['stormid'],
            "end_reporttime": item['reporttime'],
            "lat": item['lat'],
            "lon": item['lon'],
            "year": item['year'],
            "sea_area": item['sea_area'],
        }

        query = {"stormid": item['stormid'], "year": item['year'], "sea_area": item['sea_area']}
        tythoon = self.mgo.mgo_coll.find_one(query, {"datatime": 0})
        if not tythoon:
            item.pop("sea_area")
            item.pop("stormid")
            item.pop("year")
            data['datatime'] = [item]
            self.mgo.set(None, data)
        else:
            id = tythoon.get('_id')
            self.insert_noaa_datatime(id,item)

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
                            Storm_url= i.xpath("./a[1]/@href")[0]
                            sea_area = ocean_names_list[index].xpath('./div/text()')[0]
                            stormid = i.xpath("./a[1]/strong/text()")[0]
                            # print(Storm_url)
                            # Storm_urls = ["http://www.ssd.noaa.gov/PS/TROP/DATA/2022/adt/text/06E-list.txt","http://www.ssd.noaa.gov/PS/TROP/DATA/2022/adt/text/05E-list.txt"]
                            # stormid = Storm_url[-12:-9]
                            # 查询 noaa 的数据
                            for item in self.handle_storm(item,Storm_url):
                                item['sea_area'] = sea_area
                                item['stormid'] = stormid
                                self.save_noaa(item) 
                            logging.info(f'Noaa {stormid} 的数据导入成功！')

                            ## 查询 ssec 的数据
                            SsecSyncMgo(storm_id=stormid, sea_area=sea_area).run()