#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
from datetime import datetime, timedelta
import logging
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from tasks.irrigation.deps import read_real_prer_nc
import pymongo
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/jiufang-ls-tasks/irrigation/input/")

HANDLE_PATH = []
HANDLE_PATH.append(INPUT_PATH+"GFS/")
HANDLE_PATH.append(INPUT_PATH+"zktj/")
HANDLE_PATH.append(INPUT_PATH+"zktj/")


class ZktjNcMgo(BaseModel):
    def __init__(self):
        config = {
            'collection': 'zjtj_prer',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
                ('latitude', pymongo.ASCENDING),
                ('longitude', pymongo.ASCENDING),
            ]
            }
        super(ZktjNcMgo, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
            now_date_time = (datetime.now() + timedelta(days=-1)).strftime('%Y%m%d')
            input_path = INPUT_PATH+f"{now_date_time}/prer.nc"
            for index, path in enumerate(HANDLE_PATH):
                if index == 0 or index == 1:
                    date_time = now_date_time + "00"
                else:
                    date_time = now_date_time + "12"
                print(path, date_time)
                for row in read_real_prer_nc(path, date_time):
                    res = self.mgo.set(None, row)
                print(f'{now_date_time}导入成功')


