#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.db.mongo import MgoStore,get_mgo
from pkg.util.format import format_time
from tasks.handle_mgo.deps import query_one,update_one,query_all
import datetime
import logging
import pymongo

class SyncCmaNewGround:
    def __init__(self):
        self.mgo_client, self.mgo_db = get_mgo()
        config = {
            "mgo_client": self.mgo_client,
            "mgo_db": self.mgo_db,
            'collection': 'new_ground_data',
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
            date_now = datetime.datetime.now()
            yester_now = date_now + datetime.timedelta(hours=-3)
            year_now = yester_now.year
            month_now = yester_now.month
            day_now = yester_now.day
            
            citys = self.mgo_db['nation_city'].find({})
            for city in citys:
                fcityname = city.get('fcityname')
                fcitynameShi = city.get('fcitynameShi')
                print('...开始查询城市: ',fcityname)
                mgo_res = query_all(self.mgo_db, 'ground_data', fcityname,year_now,month_now,day_now)
                mgo_list = list(mgo_res[:])
                for row in mgo_list:
                    Day = row['Day']
                    Hour = row['Hour']
                    Mon = row['Mon']
                    Year = row['Year']
                    UTC_TIME = f"{Year}-{Mon}-{Day} {Hour}:00:00"
                    dataTime = format_time(india_time_str=UTC_TIME)
                    del row['Day']
                    del row['Hour']
                    del row['Year']
                    del row['Mon']
                    row['dataTime'] = dataTime
                    row['cityName'] = fcitynameShi
                    self.mgo.set(None, row)
        except Exception as e:
            logging.error(e)
        finally:
            self.close()

