#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import logging
import pymongo
import datetime
import pandas as pd
import subprocess
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from tasks.typhoon.deps import HandleGFSTyphoon
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/LS-handler-task/input/")


class GfsRealtimeSyncMgo(BaseModel):
    def __init__(self):
        config = {
            'collection': "gfs_realtime_data",
            'uniq_idx': [
                ('start_reporttime', pymongo.ASCENDING),
                ('end_reporttime', pymongo.ASCENDING),
                ('lat', pymongo.ASCENDING),
                ('lon', pymongo.ASCENDING),
                ('stormid', pymongo.ASCENDING),
                ('year', pymongo.ASCENDING)
            ],
            "idx_dic": {'embedded_idx': [('datatime.reporttime', pymongo.ASCENDING)]}  # 建立嵌套时间的索引
            }
        super(GfsRealtimeSyncMgo, self).__init__(config)
        self.GLOBAL_ROWS_TYPHOON = int(os.getenv('GLOBAL_ROWS_TYPHOON', 0))
        self.GLOBAL_YEAR = int(os.getenv('GLOBAL_YEAR', 2022))
   
    @decorate.exception_capture_close_datebase
    def run(self):
        YEAR = (datetime.datetime.now() + datetime.timedelta(hours=-9)).year
        # YEAR = datetime.datetime.now().year
        # if YEAR != self.GLOBAL_YEAR:
        #     self.GLOBAL_ROWS_TYPHOON = 0

        file_name = "tcvitals_2_{}.csv".format(YEAR)
        csv_file = INPUT_PATH + file_name
        res = subprocess.getoutput(f"wc -l {csv_file}")
        try:
            temp_rows_typhoon = int(res.replace(' ','').split('/')[0])
        except Exception as e:
            print("error:",e)
        else:
            if self.GLOBAL_ROWS_TYPHOON == temp_rows_typhoon:
                print(f'该时刻暂无新台风值')
            else:
                print(self.GLOBAL_ROWS_TYPHOON)
                df = pd.read_csv(csv_file)
                for index, row in df.iterrows():
                    if index < (self.GLOBAL_ROWS_TYPHOON-5):
                        continue
                    handle_typhoon = HandleGFSTyphoon(mgo=self.mgo,year=YEAR,row=row)
                    handle_typhoon.save_realtime_data()
                    handle_typhoon.close()

            self.GLOBAL_ROWS_TYPHOON = temp_rows_typhoon
            print(f'定时任务运行完毕，此时GLOBAL_ROWS_TYPHOON={self.GLOBAL_ROWS_TYPHOON}')