#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import logging
import datetime
import pymongo
from pandas.errors import EmptyDataError
import pandas as pd
from basic.database import get_mgo, MgoStore
from tasks.typhoon.deps import HandleTyphoon
import subprocess
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/LS-handler-task/input/")


class GfsSyncMgo:
    def __init__(self):
        self.HISTORY_YEAR = os.getenv('HISTORY_YEAR', "2021")  
        mgo_client, mgo_db = get_mgo()
        config = {
            "mgo_client": mgo_client,
            "mgo_db": mgo_db,
            'collection': 'gfs_data',
            'uniq_idx': [
                ('forecast_time', pymongo.ASCENDING),
                ('StormID', pymongo.ASCENDING),
                ('Basin', pymongo.ASCENDING)
            ],
            'idx_dic': {
                    'typhoon_idx': [
                        ('forecast_time', pymongo.ASCENDING),
                        ('typhoon_id', pymongo.ASCENDING)
                    ],
                }
            }
        self.mgo = MgoStore(config)  # 初始化

    def close(self):
        self.mgo.close()

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
                        # break
        except Exception as e:
            logging.error('run error {}'.format(e))
        finally:
            self.close()
         
    def run(self):
        try:
            date_now = datetime.datetime.now().strftime("%Y%m%d")
            print(f'当前启动任务，入库时间== {date_now} ==')
            res = subprocess.getoutput(f"ls -a {INPUT_PATH} |grep gfs_{date_now}")
            if res:
                print(res)
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

                            # break
                    break
        except Exception as e:
            logging.error('run error {}'.format(e))
        finally:
            self.close()
