#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from tasks.consumer.deps import read_gfs_nc, read_mfwam25_nc, sync_redis

obs_config = {
    "obs_ak": os.getenv('OBS_AK', 'JKRANSLTIOLXCZLBECVX'),
    "obs_sk": os.getenv('OBS_SK', 'ZhRyKdZq0yAGqFkXgbI2T8kMIaaapNWrHUbbb4IN'),
    "obs_server": os.getenv('OBS_SERVER', 'https://obs.cn-north-4.myhuaweicloud.com'),
    "obs_bucket": os.getenv('OBS_BUCKET', 'nine-confidential'),
    "obs_root": os.getenv('OBS_ROOT', 'air/nio'),
    "obs_domain": os.getenv('OBS_DOMAIN', 'https://cfdt.ninecosmos.cn'),
}


class ConvertGFSnc2jsonRds(BaseModel):
    def __init__(self):
        config = {"rds": True, "handle_db": "rds"}
        super(ConvertGFSnc2jsonRds, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self, task={}):
        
        input_file = task.get("input_file")
        print(input_file)
        if input_file:
            data = read_gfs_nc(input_file)
            if data:
                # 上传到redis
                date = data["dt"]
                value = data["data"]
                value = json.dumps(value)
                sync_redis(self.rds, date, "nc2rds:pressure", value)


class ConvertMFWAMnc2jsonRds(BaseModel):
    """传递 mfwam 0.25的文件地址"""

    def __init__(self):
        config = {"rds": True, "handle_db": "rds"}
        super(ConvertMFWAMnc2jsonRds, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self, task={}):
        input_file = task.get("input_file")
        if input_file:
            for data in read_mfwam25_nc(input_file):
                if data:
                    # 上传到redis
                    date = data["dt"]
                    value = data["data"]
                    value = json.dumps(value)
                    sync_redis(self.rds, date, "nc2rds:seawaveheight", value)
