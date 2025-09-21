#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,json
import logging
import datetime
import pymongo
import requests
import pandas as pd
from pkg.public.models import BaseModel
from tasks.typhoon.deps import HandleGFSTyphoon,WzTyphoon
import subprocess
from pkg.public.decorator import decorate
from pkg.util.spider import parse_url
INPUT_PATH = os.getenv('INPUT_PATH', "/Users/jiufangkeji/Documents/JiufangCodes/LS-handler-task/input/温州台风网")


class WZCurrSyncMgo(BaseModel):
    def __init__(self):
        config = {
            'handle_db': 'mgo',
            'collection': 'wztfw_data',
            'uniq_idx': [
                ('stormid', pymongo.ASCENDING),
                # ('stormname', pymongo.ASCENDING),
            ],
            'idx_dic': {
                    'embedded_realtime_data_idx': [
                        ('realtime_data.reporttime', pymongo.ASCENDING)
                    ],
                    'embedded_forecast_data_idx': [
                        ('forecast_data.forecast_time', pymongo.ASCENDING)
                    ],
                }
            }
        super(WZCurrSyncMgo, self).__init__(config)
        self.HISTORY_YEAR = os.getenv('HISTORY_YEAR', "202207")  

    def history(self):
        try:
            res = subprocess.getoutput(f"ls -a {INPUT_PATH} |grep {self.HISTORY_YEAR}")
            list_gfs = res.split('\n')
            list_gfs.sort(reverse=False)
            print(list_gfs)
            for dir in list_gfs:
                logging.info(f"目前的目录是:{dir}")
                files_list = os.listdir(f"{INPUT_PATH}/{dir}")
                files_list.sort(reverse=False)
                for file in files_list:
                    file_path = f"{INPUT_PATH}/{dir}/{file}"
                    logging.info(f"目前的文件是:{file_path}")
                    try:
                        with open(file_path, "r") as f:
                            json_data = json.load(f)
                    except Exception as e:
                        logging.error(str(e))

                    # 开始遍历改 时间点的 台风列表
                    for typhoon in json_data:
                        wz_typhoon = WzTyphoon(self.mgo, typhoon)
                        res = wz_typhoon.query_wz_exist()
                        if res:
                            
                            # 有的话，更新
                            wz_typhoon.update_real_time_mgo(res.get('_id'))
                            wz_typhoon.update_forecast_mgo(res.get('_id'))
                        else:
                            # 没有的话，增加
                            wz_typhoon.save_mgo()

        except Exception as e:
            logging.error('run error {}'.format(e))
        finally:
            self.close()
    
    @decorate.exception_capture_close_datebase
    def run(self):
        date_now = datetime.datetime.now().strftime("%Y%m%d")
        print(f'当前启动任务，入库时间== {date_now} ==')
        res = parse_url(url="https://data.istrongcloud.com/v2/data/complex/currMerger.json")
        if res.status_code == 200:
            try:
                json_data = json.loads(res.text)
            except Exception as e:
                logging.error(str(e))
            if json_data:
                # 开始遍历改 时间点的 台风列表
                for typhoon in json_data:
                    wz_typhoon = WzTyphoon(self.mgo, typhoon)
                    res = wz_typhoon.query_wz_exist()
                    if res:
                        # 有的话，更新
                        wz_typhoon.update_real_time_mgo(res.get('_id'))
                        wz_typhoon.update_forecast_mgo(res.get('_id'))
                    else:
                        # 没有的话，增加
                        wz_typhoon.save_mgo()
        else:
            raise ValueError(f">> 请求失败, code:{res.status_code}")