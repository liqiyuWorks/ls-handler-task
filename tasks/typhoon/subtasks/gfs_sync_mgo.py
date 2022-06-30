#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import logging
import datetime
import pymongo
from pandas.errors import EmptyDataError
import pandas as pd
from pkg.public.models import BaseModel
from tasks.typhoon.deps import HandleTyphoon
import subprocess
from pkg.public.decorator import decorate
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/LS-handler-task/input/")


class GfsSyncMgo(BaseModel):
    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'gfs_data',
            'uniq_idx': [
                ('start_forecast_time', pymongo.ASCENDING),
                ('end_forecast_time', pymongo.ASCENDING),
                ('StormID', pymongo.ASCENDING),
                ('Basin', pymongo.ASCENDING)
            ],
            'idx_dic': {
                    'typhoon_idx': [
                        ('forecast_time', pymongo.ASCENDING),
                        # ('typhoon_id', pymongo.ASCENDING)
                    ],
                }
            }
        super(GfsSyncMgo, self).__init__(config)
        self.HISTORY_YEAR = os.getenv('HISTORY_YEAR', "2022")  

    def history(self):
        try:
            res = subprocess.getoutput(f"ls -a {INPUT_PATH} |grep gfs_{self.HISTORY_YEAR}")
            list_gfs = res.split('\n')
            for file in list_gfs:
                if "swp" in file:
                    continue
                if "csv" not in file:
                    continue
                gfs_file = INPUT_PATH + file
                print(gfs_file)
                try:
                    df = pd.read_csv(gfs_file)
                except EmptyDataError as e:
                    continue
                for index, row in df.iterrows():
                    handle_typhoon = HandleTyphoon(mgo=self.mgo,row=row)
                    flag = handle_typhoon.query_gfs_typhoon()
                    if flag:
                        print('开始匹配数据...')
                        typhoon_id = handle_typhoon.query_real_time_typhoon()
                        handle_typhoon.save_gfs_data(typhoon_id)
                #     break
                # break
        except Exception as e:
            logging.error('run error {}'.format(e))
        finally:
            self.close()
    
    @decorate.exception_capture_close_datebase
    def run(self):
        date_now = datetime.datetime.now().strftime("%Y%m%d")
        print(f'当前启动任务，入库时间== {date_now} ==')
        date_now = "20220511"
        res = subprocess.getoutput(f"ls -a {INPUT_PATH} |grep gfs_{date_now}")
        if res:
            list_gfs = res.split('\n')
            for file in list_gfs:
                gfs_file = INPUT_PATH + file
                print(gfs_file)
                try:
                    df = pd.read_csv(gfs_file)
                except EmptyDataError as e:
                    pass  
                else:
                    for index, row in df.iterrows():
                        handle_typhoon = HandleTyphoon(mgo=self.mgo,row=row)
                        flag = handle_typhoon.query_gfs_typhoon()
                        if flag:
                            typhoon_id = handle_typhoon.query_real_time_typhoon()
                            handle_typhoon.save_gfs_data(typhoon_id)

                        break
                break
