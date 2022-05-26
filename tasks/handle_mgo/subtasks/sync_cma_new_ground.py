#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.util.format import format_time
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from tasks.handle_mgo.deps import query_one_year,query_all
import datetime
import os
import pymongo

class SyncCmaNewGround(BaseModel):
    def __init__(self):
        config = {
            'collection': 'new_ground_data',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
                ('stationId', pymongo.ASCENDING)
            ]
            }
        super(SyncCmaNewGround, self).__init__(config)
        self.HISTORY_YEAR = int(os.getenv('HISTORY_YEAR', 2021))

    @decorate.exception_capture_close_datebase
    def run(self):
        date_now = datetime.datetime.now()
        date_now = date_now + datetime.timedelta(hours=-9)
        year_now = date_now.year
        month_now = date_now.month
        day_now = date_now.day
        
        citys = self.config['mgo_db']['nation_city'].find({})
        for city in citys:
            fcityname = city.get('fcityname')
            fcitynameShi = city.get('fcitynameShi')
            print('...开始查询城市: ',fcityname)
            mgo_res = query_all(self.config['mgo_db'], 'ground_data', fcityname,year_now,month_now,day_now)
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

    @decorate.exception_capture_close_datebase
    def history(self):        
        citys = self.config['mgo_db']['nation_city'].find({})
        for city in citys:
            fcityname = city.get('fcityname')
            fcitynameShi = city.get('fcitynameShi')
            print('...开始查询城市: ',fcityname)
            mgo_res = query_one_year(self.config['mgo_db'], 'ground_data', fcityname,self.HISTORY_YEAR)
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
