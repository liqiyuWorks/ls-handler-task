#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
from datetime import datetime, timedelta
import logging
from basic.database import get_mgo, MgoStore
from tasks.irrigation.deps import read_real_prer_nc
import pymongo
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/jiufang-ls-tasks/irrigation/input/")

HANDLE_PATH = []
HANDLE_PATH.append(INPUT_PATH+"GFS/")
HANDLE_PATH.append(INPUT_PATH+"zktj/")
HANDLE_PATH.append(INPUT_PATH+"zktj/")


class ZktjNcMgo:
    def __init__(self):
        mgo_client, mgo_db = get_mgo()
        config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'zjtj_prer',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
                ('latitude', pymongo.ASCENDING),
                ('longitude', pymongo.ASCENDING),
            ]
            }
        self.mgo = MgoStore(config)  # 初始化

    def close(self):
        self.mgo.close()

    def run(self):
        try:
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
        except Exception as e:
            logging.error(e)
        finally:
            self.close()


