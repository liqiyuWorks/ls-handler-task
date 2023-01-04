#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from pkg.public.decorator import decorate
from tasks.consumer.deps import read_gfs_nc,read_mfwam25_nc, check_create_path, ObsStore
import json
import logging

obs_config = {
    "obs_ak": os.getenv('OBS_AK', 'JKRANSLTIOLXCZLBECVX'),
    "obs_sk": os.getenv('OBS_SK', 'ZhRyKdZq0yAGqFkXgbI2T8kMIaaapNWrHUbbb4IN'),
    "obs_server": os.getenv('OBS_SERVER', 'https://obs.cn-north-4.myhuaweicloud.com'),
    "obs_bucket": os.getenv('OBS_BUCKET', 'nine-confidential'),
    "obs_root": os.getenv('OBS_ROOT', 'air/nio'),
    "obs_domain": os.getenv('OBS_DOMAIN', 'https://cfdt.ninecosmos.cn'),
}

class ConvertGFSnc2jsonOBS:
    @decorate.exception_capture
    def run(self,task={}):
        input_file = task.get("input_file")
        if input_file:
            data = read_gfs_nc(input_file)
            if data:
                year = data["dt"][:4]
                mon = data["dt"][5:7]
                day = data["dt"][8:10]
                hour = data["dt"][11:13]
                file = f'gfs/{year}/{mon}/{day}/{hour}.json'
                json_str = json.dumps(data["data"])
                check_create_path(file)
                with open(file, 'w') as json_file:
                    json_file.write(json_str)
                    
                try:
                    obs_data = {
                        "file_name": file,
                        "obs_key": file
                    }

                    obs_store = ObsStore(obs_config)
                    url = obs_store.set(obs_data)
                    logging.info('上传OBS成功, url={}'.format(url))
                except Exception as e:
                    logging.info('上传OBS发生错误, 错误信息是={}'.format(str(e)))
                finally:
                    if os.path.exists(file):
                        os.remove(file)
                
                
class ConvertMFWAMnc2jsonOBS:
    """传递 mfwam 0.25的文件地址"""
    @decorate.exception_capture
    def run(self,task={}):
        input_file = task.get("input_file")
        if input_file:
            for data in read_mfwam25_nc(input_file):
                if not data:
                    break
                year = data["dt"][:4]
                mon = data["dt"][5:7]
                day = data["dt"][8:10]
                hour = data["dt"][11:13]
                file = f'mfwam25/{year}/{mon}/{day}/{hour}.json'
                json_str = json.dumps(data["data"])
                check_create_path(file)
                with open(file, 'w') as json_file:
                    json_file.write(json_str)
                    
                try:
                    obs_data = {
                        "file_name": file,
                        "obs_key": file
                    }

                    obs_store = ObsStore(obs_config)
                    url = obs_store.set(obs_data)
                    logging.info('上传OBS成功, url={}'.format(url))
                except Exception as e:
                    logging.info('上传OBS发生错误, 错误信息是={}'.format(str(e)))
                finally:
                    if os.path.exists(file):
                        os.remove(file)