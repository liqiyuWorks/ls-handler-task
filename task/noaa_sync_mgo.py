#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import pandas as pd
import datetime
import pymongo
import requests
import pandas as pd
from basic.database import get_mgo, MgoStore
from lxml import etree
URL_INDEX  =os.getenv('URL_INDEX', "https://www.ssd.noaa.gov/PS/TROP/adt.html")
COLLECTION = os.getenv('COLLECTION', "noaa_data")

UP_STORMS = ["Atlantic", "East Pacific", "Central Pacific", "South Indian"]
DOWN_STORMS = ["West Pacific", "Arabian Sea", "Bay of Bengal", "South Indian", "South Pacific"]
MGO_FIELD = ["Date","Time","CI","MSLP", "Vmax", "Fnl_Tno", "Adj_Raw", "Ini_Raw", "Limit", "Wkng_Flag","Rpd_Wkng", "ET_Flag", "ST_Flag", "Cntr_Region","Mean_Cloud", "Scene_Type","EstRMW", "MW_Score", "Lat", "Lon", "Fix_Mthd", "Sat", "VZA", "Comments"]
month_abbr_list = [
    '',
 'JAN',
 'FEB',
 'MAR',
 'APR',
 'MAY',
 'JUN',
 'JUL',
 'AUG',
 'SEP',
 'OCT',
 'NOV',
 'DEC']


def parse_url(url):
    '''发起请求'''
    try:
        print('当前请求的url={}'.format(url))
        res = requests.get(url)
        return res
    except Exception as e:
        print('出现问题={}'.format(e))

def handle_storm(item,Storm_url):
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
            item['dataTime'] = item['Date'][:4] + '{:02d}'.format(month_abbr_list.index(Date)) + item['Date'][7:] + item['Time']
            item.pop('Date')
            item.pop('Time')
            yield item


def noaa_sync_mgo():
    date_now = datetime.datetime.now()
    print(f'当前启动任务，入库时间== {date_now} ==')
    mgo_client, mgo_db = get_mgo()
    config = {
        "mgo_client": mgo_client,
        "mgo_db": mgo_db,
        'collection': COLLECTION,
        'uniq_idx': [
            ('dataTime', pymongo.ASCENDING),
            ('StormID', pymongo.ASCENDING),
            ('sea_area', pymongo.ASCENDING)
        ]
        }
    mgo = MgoStore(config)  # 初始化
    r = parse_url(URL_INDEX)
    if r.status_code == 200:
        html_xpath = etree.HTML(r.text)
        up_list = html_xpath.xpath('//*[@class="padding5"]/table[2]/tr[3]/td')
        down_list = html_xpath.xpath('//*[@class="padding5"]/table[3]/tr[3]/td')
        up_list = list(zip(UP_STORMS, up_list))
        down_list = list(zip(DOWN_STORMS, down_list))
        fin_list = up_list + down_list

        for td in fin_list:
            item = {}
            a_list = td[1].xpath('./center/a')
            if a_list:
                item['sea_area'] = td[0]
                item['StormID']= td[1].xpath("./center/a[1]/strong/text()")[0]
                Storm_url= td[1].xpath("./center/a[1]/@href")[0]
                print(item)
                for item in handle_storm(item,Storm_url):
                    res = mgo.set(None, item)
                    print(res)

    mgo.close()
