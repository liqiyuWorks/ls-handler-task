#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, logging
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
    def __init__(self, storm_id,sea_area):
        self.storm_id = storm_id
        self.sea_area = sea_area
        self.listing_index = "https://tropic.ssec.wisc.edu/real-time/adt/{}-list.txt".format(self.storm_id)
        self.archer_index = "https://tropic.ssec.wisc.edu/real-time/adt/ARCHER/ARCHERinfo_{}.html".format(self.storm_id)
        mgo_client, mgo_db = get_mgo()
        listing_config = {
            "mgo_client":
            mgo_client,
            "mgo_db":
            mgo_db,
            'collection':
            'ssec_listing_data',
            'uniq_idx': [('dataTime', pymongo.ASCENDING),
                         ('StormID', pymongo.ASCENDING),
                         ('sea_area', pymongo.ASCENDING)]
        }
        archer_config = {
            "mgo_client":
            mgo_client,
            "mgo_db":
            mgo_db,
            'collection':
            'ssec_archer_data',
            'uniq_idx': [('dataTime', pymongo.ASCENDING),
                         ('StormID', pymongo.ASCENDING),
                         ('sea_area', pymongo.ASCENDING)]
        }
        self.listing_mgo = MgoStore(listing_config)  # 初始化
        self.archer_mgo = MgoStore(archer_config)  # 初始化

    def handle_listing_storm(self, Storm_url):
        item = {"StormID": self.storm_id, "sea_area": self.sea_area}
        r = parse_url(Storm_url)
        if r.status_code == 200:
            rows = str(r.text).split('\n')
            for line in rows[5:-2]:
                item["Date"] = line[:10].strip()
                item["Time"] = line[10:16].strip()
                item["CI"] = line[16:21].strip()
                item["MSLP"] = line[21:28].strip()
                item["Vmax"] = line[28:34].strip()
                item["Fnl_Tno"] = line[33:38].strip()
                item["Adj_Raw"] = line[38:42].strip()
                item["Ini_Raw"] = line[42:46].strip()
                item["Limit"] = line[46:57].strip()
                item["Wkng_Flag"] = line[57:60].strip()
                item["Rpd_Wkng"] = line[62:67].strip()
                item["ET_Flag"] = line[67:72].strip()
                item["ST_Flag"] = line[72:75].strip()
                item["Cntr_Region"] = line[75:82].strip()
                item["Mean_Cloud"] = line[82:89].strip()
                item["Scene_Type"] = line[89:97].strip()
                item["EstRMW"] = line[99:106].strip()
                item["MW_Score"] = line[106:112].strip()
                item["Lat"] = line[112:120].strip()
                item["Lon"] = line[120:128].strip()
                item["Fix_Mthd"] = line[128:136].strip()
                item["Sat"] = line[135:142].strip()
                item["VZA"] = line[142:150].strip()
                item["Comments"] = line[150:].strip()
                Date = item['Date']
                Date = Date[4:7]
                item['dataTime'] = item['Date'][:4] + '{:02d}'.format(
                    month_abbr_list.index(
                        Date)) + item['Date'][7:] + item['Time']
                item.pop('Date')
                item.pop('Time')
                self.listing_mgo.set(None, item)

    def get_group1(self,item, data):
        group = str(data[2])
        for i in range(8,0,-1):
            group = group.replace(' '*i,'\t')
        group = group.split('\t')
        item['source'] = group[0]
        item['Sensor'] = group[1]
        item['FORECAST_lat'] = group[2]
        item['FORECAST_lon'] = group[3]
        item['Vmax'] = group[4]
        item['ARCHER_lat'] = group[5]
        item['ARCHER_lon'] = group[6]
        item['50_cert_radius'] = group[7]
        item['95_cert_radius'] = group[8]
        return item

    def get_group2(self,item, data):
        group = str(data[4])
        for i in range(8,0,-1):
            group = group.replace(' '*i,'\t')
        group = group.split('\t')
        item['conf_score']=group[0]
        item['alpha_score']=group[1]
        item['eye_prob']=group[2]
        return item


    def handle_archer_storm(self,Storm_url):
        r = parse_url(Storm_url)
        if r.status_code == 200:
            html_xpath = etree.HTML(r.text)
            pres = html_xpath.xpath('/html/body/center/table/tr[2]/td/font/pre//text()')
            new_pres = pres[3:]
            for index,i in enumerate(new_pres[::6]):
                item = {"StormID":self.storm_id, "sea_area":self.sea_area}
                data = []
                for elem in new_pres[index*6:6*(index+1)]:
                    elem = str(elem).strip().replace('\n','')
                    data.append(elem)
                data[1] = data[1].replace(':','')
                item['dataTime'] = f'{data[0]}{data[1]}'
                item['Eyewall radius'] = data[3]
                item = self.get_group1(item, data)
                item = self.get_group2(item, data)
                self.archer_mgo.set(None, item)

    def close(self):
        self.listing_mgo.close()
        self.archer_mgo.close()

    def run(self):
        try:
            try:
                self.handle_listing_storm(self.listing_index)
            except Exception as e:
                logging.error('run error {}'.format(e))
            logging.info('Ssec - listing 数据导入成功！') 

            try:
                self.handle_archer_storm(self.archer_index)
            except Exception as e:
                logging.error('run error {}'.format(e))
                
            logging.info('Ssec - archer 数据导入成功！') 
                
        except Exception as e:
            logging.error('run error {}'.format(e))
        finally:
            self.close()