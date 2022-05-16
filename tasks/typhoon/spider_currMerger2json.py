#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import datetime
import requests
from basic.util import check_create_path

OUTPUT_PATH = os.getenv('OUTPUT_PATH', ".")

class SpiderCurrmergerJson:
    def __init__(self):
        pass

    def run(self):
        date_now = datetime.datetime.now().strftime("%Y%m%d%H%M")
        day = date_now[:8]
        print(f'当前启动任务，下载== {date_now} ==')
        res = requests.get(url="https://data.istrongcloud.com/v2/data/complex/currMerger.json")
        
        if res.status_code == 200:
            file_path = f"{OUTPUT_PATH}/{day}/{date_now}.json"
            check_create_path(file_path)
            with open(file_path, "w") as f:
                f.write(res.text)
                print(f'当前任务下载成功!')

