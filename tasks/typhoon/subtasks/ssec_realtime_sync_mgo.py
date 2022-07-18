#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, logging
from copy import deepcopy
from pkg.util.format import time2time
import pymongo
import pandas as pd
from pkg.db.mongo import get_mgo, MgoStore
from pkg.util.spider import parse_url
from lxml import etree

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

class SsecSyncMgo:
    def __init__(self, storm_id="05W",sea_area="05W"):
        self.storm_id = storm_id
        self.sea_area = sea_area
        self.listing_index = "https://tropic.ssec.wisc.edu/real-time/adt/{}-list.txt".format(self.storm_id)
        self.archer_index = "https://tropic.ssec.wisc.edu/real-time/adt/ARCHER/ARCHERinfo_{}.html".format(self.storm_id)
        self.real_time_wind_index = "https://tropic.ssec.wisc.edu/real-time/adt/{}.2dwind.txt".format(self.storm_id)
        mgo_client, mgo_db = get_mgo()
        real_time_config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'ssec_realtime_data',
            'uniq_idx': [('year', pymongo.ASCENDING),
                         ('stormid', pymongo.ASCENDING),
                         ('sea_area', pymongo.ASCENDING)]
        }
        archer_config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'ssec_archer_data',
            'uniq_idx': [('year', pymongo.ASCENDING),
                         ('stormid', pymongo.ASCENDING),
                         ('sea_area', pymongo.ASCENDING)]
        }
        self.real_time_mgo = MgoStore(real_time_config)  # 初始化
        self.archer_mgo = MgoStore(archer_config)  # 初始化

    def handle_listing_storm(self, Storm_url):
        r = parse_url(Storm_url)
        if r.status_code == 200:
            rows = str(r.text).split('\n')
            for line in rows[5:-4]:
                item = {"stormid": self.storm_id, "sea_area": self.sea_area}
                item["Date"] = line[:10].strip()
                item["Time"] = line[10:17].strip()
                # item["CI"] = line[16:21].strip()
                item["minp"] = float(line[21:28].strip())   # MinP = MSLP
                item["maxsp"] = float(line[28:34].strip())    # MaxSP = Vmax
                # item["Fnl_Tno"] = line[33:38].strip()
                # item["Adj_Raw"] = line[38:42].strip()
                # item["Ini_Raw"] = line[42:46].strip()
                # item["Limit"] = line[46:57].strip()
                # item["Wkng_Flag"] = line[57:60].strip()
                # item["Rpd_Wkng"] = line[62:67].strip()
                # item["ET_Flag"] = line[67:72].strip()
                # item["ST_Flag"] = line[72:75].strip()
                # item["Cntr_Region"] = line[75:82].strip()
                # item["Mean_Cloud"] = line[82:89].strip()
                # item["Scene_Type"] = line[89:97].strip()
                # item["EstRMW"] = line[99:106].strip()
                # item["MW_Score"] = line[106:112].strip()
                item["lat"] = float(line[112:119].strip())
                item["lon"] = float(line[120:128].strip())*(-1)
                # item["Fix_Mthd"] = line[128:136].strip()
                # item["Sat"] = line[135:142].strip()
                # item["VZA"] = line[142:150].strip()
                # item["Comments"] = line[150:].strip()
                Date = item['Date']
                Date = Date[4:7]
                reporttime_str = item['Date'][:4] + '{:02d}'.format(month_abbr_list.index(Date)) + item['Date'][7:] + item['Time']
                item['reporttime'] = time2time(reporttime_str, "%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S")
                item.pop('Date')
                item.pop('Time')
                self.save_ssec_list_mgo(item)
                

    def save_ssec_list_mgo(self, item):
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
        tythoon = self.real_time_mgo.mgo_coll.find_one(query, {"datatime": 0})
        if not tythoon:
            item.pop("sea_area")
            item.pop("stormid")
            item.pop("year")
            data['datatime'] = [item]
            self.real_time_mgo.set(None, data)
        else:
            id = tythoon.get('_id')
            self.insert_ssec_datatime(id,item)

    def insert_ssec_datatime(self,id, item):
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
        res = list(self.real_time_mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            # logging.info("已有ssec该时刻实测数据，准备更新....")
            r = self.real_time_mgo.mgo_coll.update_one(
                {
                    "_id": id,
                    "datatime.reporttime": item['reporttime']
                }, {
                    "$set": {
                        # "datatime.$.lat": item.get('lat'),
                        # "datatime.$.lon": item.get('lon'),
                        # "datatime.$.minp": item.get('minp'),
                        # "datatime.$.maxsp": item.get('maxsp'),
                        "datatime.$.r34_ne": item.get("r34_ne", None),
                        "datatime.$.r34_se": item.get("r34_se", None),
                        "datatime.$.r34_sw": item.get("r34_sw", None),
                        "datatime.$.r34_nw": item.get("r34_nw", None),
                        "datatime.$.r50_ne": item.get("r50_ne", None),
                        "datatime.$.r50_se": item.get("r50_se", None),
                        "datatime.$.r50_sw": item.get("r50_sw", None),
                        "datatime.$.r50_nw": item.get("r50_nw", None),
                        "datatime.$.r64_ne": item.get("r64_ne", None),
                        "datatime.$.r64_se": item.get("r64_se", None),
                        "datatime.$.r64_sw": item.get("r64_sw", None),
                        "datatime.$.r64_nw": item.get("r64_nw", None),
                        "datatime.$.speed": item.get('speed'),
                        "datatime.$.direction": item.get('direction'),
                        "datatime.$.rmw": item.get('rmw'),
                    }
                },
                upsert=True)

        else:
            datatime.pop("sea_area")
            datatime.pop("stormid")
            datatime.pop("year")
            r = self.real_time_mgo.mgo_coll.update({
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
            print("ssec realtme 嵌套新增成功res", r)


    def save_ssec_archer_mgo(self, item):
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
        tythoon = self.archer_mgo.mgo_coll.find_one(query, {"datatime": 0})
        if not tythoon:
            item.pop("sea_area")
            item.pop("stormid")
            item.pop("year")
            data['datatime'] = [item]
            self.archer_mgo.set(None, data)
        else:
            id = tythoon.get('_id')
            self.insert_ssec_archer_datatime(id,item)

    def insert_ssec_archer_datatime(self,id, item):
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
        res = list(self.archer_mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            # logging.info("已有ssec该时刻实测数据，准备更新....")
            r = self.archer_mgo.mgo_coll.update_one(
                {
                    "_id": id,
                    "datatime.reporttime": item['reporttime']
                }, {
                    "$set": {
                        "datatime.$.lat": item.get('lat'),
                        "datatime.$.lon": item.get('lon'),
                        "datatime.$.maxsp": item.get('maxsp'),
                        "datatime.$.eyewall_radius": item.get('eyewall_radius')
                    }
                },
                upsert=True)

        else:
            datatime.pop("sea_area")
            datatime.pop("stormid")
            datatime.pop("year")
            r = self.archer_mgo.mgo_coll.update({
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
            print("ssec archer 嵌套新增成功res", r)

    def get_group1(self,item, data):
        group = str(data[2])
        for i in range(8,0,-1):
            group = group.replace(' '*i,'\t')
        group = group.split('\t')
        # item['source'] = group[0]
        # item['Sensor'] = group[1]
        item['lat'] = float(group[2])
        item['lon'] = float(group[3])*(-1)
        item['maxsp'] = float(group[4])  # MaxSP=Vmax
        # item['ARCHER_lat'] = group[5]
        # item['ARCHER_lon'] = group[6]
        # item['50_cert_radius'] = group[7]
        # item['95_cert_radius'] = group[8]
        return item

    def get_group2(self,item, data):
        group = str(data[4])
        for i in range(8,0,-1):
            group = group.replace(' '*i,'\t')
        group = group.split('\t')
        # item['conf_score']=group[0]
        # item['alpha_score']=group[1]
        # item['eye_prob']=group[2]
        return item


    def handle_archer_storm(self,Storm_url):
        r = parse_url(Storm_url)
        if r.status_code == 200:
            html_xpath = etree.HTML(r.text)
            pres = html_xpath.xpath('/html/body/center/table/tr[2]/td/font/pre//text()')
            new_pres = pres[3:]
            for index,i in enumerate(new_pres[::6][:-1]):
                item = {"stormid":self.storm_id, "sea_area":self.sea_area}
                data = []
                loop_pres = new_pres[index*6:6*(index+1)]
                for elem in loop_pres:
                    elem = str(elem).strip().replace('\n','')
                    data.append(elem)
                data[1] = data[1].replace(':','')
                reporttime_str = f'{data[0]}{data[1]}'
                item['reporttime'] = time2time(reporttime_str, "%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S")
                
                item['eyewall_radius'] = data[3]
                item = self.get_group1(item, data)
                # item = self.get_group2(item, data)
                self.save_ssec_archer_mgo(item)

    def handle_wind_storm(self,Storm_url):
        r = parse_url(Storm_url)
        if r.status_code == 200:
            rows = str(r.text).split('\n')
            for line in rows[2:-2]:
                item = {"stormid": self.storm_id, "sea_area": self.sea_area}
                item["Date"] = line[:10].strip()
                item["Time"] = line[10:17].strip()
                item["speed"] = round(float(line[17:23].strip()),0)
                item["direction"] = round(float(line[24:28].strip()),0)
                item["maxsp"] = float(line[28:34].strip())   # minp = mslp
                item["rmw"] = float(line[35:40].strip())    # maxsp = vmax
                item["r34_ne"] = float(line[44:49].strip())    # maxsp = vmax
                item["r34_se"] = float(line[50:55].strip())    # maxsp = vmax
                item["r34_sw"] = float(line[55:60].strip())    # maxsp = vmax
                item["r34_nw"] = float(line[60:66].strip())    # maxsp = vmax
                item["r50_ne"] = float(line[67:73].strip())    # maxsp = vmax
                item["r50_se"] = float(line[74:80].strip())    # maxsp = vmax
                item["r50_sw"] = float(line[80:86].strip())    # maxsp = vmax
                item["r50_nw"] = float(line[86:92].strip())    # maxsp = vmax
                item["r64_ne"] = float(line[92:98].strip())    # maxsp = vmax
                item["r64_se"] = float(line[98:104].strip())    # maxsp = vmax
                item["r64_sw"] = float(line[104:110].strip())    # maxsp = vmax
                item["r64_nw"] = float(line[110:116].strip())    # maxsp = vmax
                # item["lat"] = float(line[118:124].strip())    # maxsp = vmax
                # item["lon"] = float(line[124:131].strip())*(-1)    # maxSP = Vmax
                Date = item['Date']
                Date = Date[4:7]
                reporttime_str = item['Date'][:4] + '{:02d}'.format(month_abbr_list.index(Date)) + item['Date'][7:] + item['Time']
                item['reporttime'] = time2time(reporttime_str, "%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S")
                item['year'] =  str(item['reporttime'])[:4]
                
                item.pop('Date')
                item.pop('Time')
                # logging.info(f'{item["reporttime"]}:{item["lon"]}-{item["lat"]}')
                query = {"stormid": item['stormid'], "year": item['year'], "sea_area": item['sea_area']}
                tythoon_id = self.real_time_mgo.mgo_coll.find_one(query, {"_id": 1})
                if tythoon_id:
                    self.insert_ssec_datatime(tythoon_id['_id'], item)

    def close(self):
        self.real_time_mgo.close()
        self.archer_mgo.close()

    def run(self):
        # 爬取 ssec 的实时数据
        try:
            self.handle_listing_storm(self.listing_index)
            logging.info(f'ssec {self.storm_id} - 实时数据列表 数据导入成功！') 
        except Exception as e:
            logging.error('run error {}'.format(e))
        else:
            # 爬取 ssec 的 风圈数据
            try:
                self.handle_wind_storm(self.real_time_wind_index)
                logging.info(f'ssec {self.storm_id} - 实时数据详情 数据导入成功！') 
            except Exception as e:
                logging.error('ssec:handle_wind_storm error {}'.format(e))

        # 爬取 ssec 的 archer数据
        try:
            self.handle_archer_storm(self.archer_index)
            logging.info(f'Ssec {self.storm_id} - archer 数据导入成功！') 
        except Exception as e:
            logging.error('ssec:handle_archer_storm error {}'.format(e))
        
        self.close()
                
        