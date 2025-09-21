#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,json
import logging
import datetime
import pandas as pd
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from pkg.util.format import check_create_path,time2time,unix_time
from pkg.util.spider import parse_url
HEU_INPUT_PATH: str = os.getenv('HEU_INPUT_PATH', '/Users/jiufangkeji/Desktop/台风')


class HeuGenTyphoonJson(BaseModel):
    def __init__(self):
        pass
    
    @decorate.exception_capture
    def run(self):
        cst_now = datetime.datetime.now()
        date_time_utc = cst_now + datetime.timedelta(hours=-8)
        date_cst_time = cst_now.strftime("%Y%m%d%H")
        res = parse_url(url="http://124.70.86.179:21612/api/typhoon/query")
        if res.status_code == 200:
            data = res.json().get("data")
            print(data)
            for typhoon_name, typhoon_info in data.items():
                typhoon_info['base_info']['begintime'] = unix_time(typhoon_info['base_info']['begintime'])
                typhoon_info['history_sets']['source'] = "jiufang"
                print(typhoon_info['base_info']['year'])
                typhoon_info['base_info']['year'] = int(typhoon_info['base_info']['year'])

                for i in typhoon_info['history_sets']['history_point']:
                    i['reporttime'] = unix_time(i['reporttime'])
                    i.pop("remark", None)
                    i.pop("direction", None)
                    i.pop("strong", None)

                for i in typhoon_info.get('forecast_sets', []):
                    if i['source'] == "gfs":
                        i['source'] = "jiufang"
                        typhoon_info["forecast_sets"] = i

                if not isinstance(typhoon_info["forecast_sets"], dict):
                    for i in typhoon_info.get('forecast_sets', []):
                        if i['source'] == "中国":
                            i['source'] = "jiufang"
                            typhoon_info["forecast_sets"] = i


                if typhoon_info["forecast_sets"]:
                    for fore in typhoon_info['forecast_sets'].get('forecast_point',[]):
                        fore['forecast_time'] = unix_time(fore['forecast_time'])
                        fore.pop("basin", None)
                        fore.pop("stormid", None)
                        fore.pop("remark", None)
                        fore.pop("leadtime", None)
                else:
                    typhoon_info['forecast_sets']={}

            for typhoon_id, value in data.items():
                name = value['base_info']["stormname"]
                file_path = f"{HEU_INPUT_PATH}/{date_time_utc.year}/{date_time_utc.month:02d}/{date_time_utc.day:02d}/Typhoon/{date_cst_time}/{typhoon_id}_{name}.json"
                check_create_path(file_path)
                with open(file_path, "w") as f:
                    f.write(json.dumps(value))
                    logging.info(f">>> {date_cst_time} - {name} gen ok !")
        else:
            raise ValueError(f">> 请求失败, code:{res.status_code}")