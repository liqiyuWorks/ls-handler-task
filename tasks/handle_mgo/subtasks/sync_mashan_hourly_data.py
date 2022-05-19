#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import logging
import sys, os
from pkg.db.mongo import get_mgo, MgoStore
import pymongo
import pandas as pd
import subprocess
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Desktop/")

class SyncMashanHourlyData:
    def __init__(self):
        mgo_client, mgo_db = get_mgo()
        config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'mashan_station_hourly_data',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
                ('stationId', pymongo.ASCENDING)
            ]
            }
        self.mgo = MgoStore(config)  # 初始化

    def close(self):
        self.mgo.close()

    def run(self):
        try:
            date_now = (datetime.datetime.now() + datetime.timedelta(hours=-2)).strftime("%Y%m%d%H")
            file = f"{date_now}.csv"
            print('当前同步的是: {}'.format(file))
            try:
                df = pd.read_csv(INPUT_PATH+file)
            except FileNotFoundError as e:
                pass
            else:
                for index, row in df.iterrows():
                    row = row.to_dict()
                    row['dataTime'] = str(row['time']).split('+')[0]
                    row['stationId'] = row['id']
                    row['PM25'] = row['PM2.5']
                    del row['time']
                    del row['id']
                    del row['PM2.5']
                    self.mgo.set(None, row)
        except Exception as e:
            logging.error(e)
        finally:
            self.close()


    def history(self):
        mgo_client, mgo_db = get_mgo()
        config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'mashan_station_hourly_data',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
                ('stationId', pymongo.ASCENDING)
            ]
            }
        mgo = MgoStore(config)  # 初始化
        fuzzy_file = os.getenv('FUZZY_FILE')
        res = subprocess.getoutput(f"ls -a {INPUT_PATH} |grep {fuzzy_file}")
        list_gfs = res.split('\n')
        for file in list_gfs:
            print('当前同步的是: {}'.format(file))
            df = pd.read_csv(INPUT_PATH+file)
            for index, row in df.iterrows():
                row = row.to_dict()
                row['dataTime'] = str(row['time']).split('+')[0]
                row['stationId'] = row['id']
                row['PM25'] = row['PM2.5']
                del row['time']
                del row['id']
                del row['PM2.5']
                mgo.set(None, row)
                print('===insert {} ok'.format(row))
        mgo.close()