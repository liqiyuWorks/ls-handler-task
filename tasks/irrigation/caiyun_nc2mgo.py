#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta
import logging
from basic.database import get_mgo, MgoStore
from tasks.irrigation.deps import write_caiyun_mgo,supplement_request2png,PREP_URL
import pymongo
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/jiufang-ls-tasks/irrigation/input/cy_rain/")


class CaiyunNcMgo:
    def __init__(self):
        mgo_client, mgo_db = get_mgo()
        config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'caiyun_precip',
            'uniq_idx': [
                ('dataTime', pymongo.ASCENDING),
                ('lon', pymongo.ASCENDING),
                ('lat', pymongo.ASCENDING)
            ]
            }
        self.mgo = MgoStore(config)  # 初始化

    def close(self):
        self.mgo.close()

    def run(self):
        try:
            now_date_time = (datetime.now() + timedelta(minutes=-5)).strftime('%Y%m%d%H%M')
            input_path = INPUT_PATH+f"{now_date_time[:4]}/{now_date_time[:8]}/{now_date_time}"

            for row in write_caiyun_mgo(input_path):
                res = self.mgo.set(None, row)
            print(f'{now_date_time}写入成功！')
        except Exception as e:
            logging.error(e)
        finally:
            self.close()

    def supplement_history(self):
        START_DATE = os.getenv('START_DATE', "20220201")
        END_DATE = os.getenv('END_DATE', "20220501")
        SLEEP_INTERVAL = int(os.getenv('SLEEP_INTERVAL', "4"))
        supplement_request2png(INPUT_PATH,START_DATE,END_DATE,SLEEP_INTERVAL)
        
