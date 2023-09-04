#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os
import re
import logging
import requests
import datetime
from pkg.util.file import check_create_path
from pkg.util.time import look_recent_time
from pkg.public.obs import ObsStore


obs_config = {
    "obs_ak":
    os.getenv('OBS_AK', 'XJQLMEECPKMP9V7FFJAI'),
    "obs_sk":
    os.getenv('OBS_SK', 'AefBvozcNZwoUi5XeGkRcUeI8GerIdFPCasxVsaW'),
    "obs_server":
    os.getenv('OBS_SERVER', 'https://obs.cn-north-4.myhuaweicloud.com'),
    "obs_bucket":
    os.getenv('OBS_BUCKET', 'nine-confidential'),
    "obs_root":
    os.getenv('OBS_ROOT', 'resources'),
    "obs_domain":
    os.getenv('OBS_DOMAIN', 'https://cfdt.ninecosmos.cn'),
}


class DownWushikjCloudImagery():
    # radar_url = "https://typhoon.wushikj.com/images/cloud/zjwater_transparent/202309/01/202309011420.png"
    cloud_imagery_url = "https://typhoon.wushikj.com/images/cloud/zjwater_transparent/{}/{}/{}.png"

    def __init__(self) -> None:
        self._file_path = os.getenv(
            "FILE_PATH", "/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task")

    def upload_obs(self, save_file_path, obs_key):
        obs_data = {"file_name": save_file_path, "obs_key": obs_key}
        obs_store = ObsStore(obs_config)
        url = obs_store.set(obs_data)
        print('==>上传OBS成功，url={}'.format(url))

    def run(self):
        now_datetime = datetime.datetime.now()
        recent_time = look_recent_time(now_datetime)
        year = recent_time[:4]
        mon = recent_time[4:6]
        day = recent_time[6:8]
        req_month = recent_time[:6]
        req_day = recent_time[6:8]
        url = self.cloud_imagery_url.format(req_month, req_day, recent_time)
        response = requests.get(url)
        content_length = int(response.headers.get("Content-Length", 0))
        
        if content_length < 1000:
            print(content_length, "还未生成文件，请稍后再试")
        else:
            save_file_path = self._file_path + \
                f"/{year}/{mon}/{day}/" + recent_time + ".png"
            print(save_file_path)
            check_create_path(save_file_path)
            # 将下载到的图片数据写入文件
            with open(save_file_path, 'wb') as f:
                f.write(response.content)
            print(f'=> {save_file_path} write ok')
            obs_key = f"cloud_imagery/{year}/{mon}/{day}/" + \
                recent_time + ".png"
            self.upload_obs(save_file_path, obs_key)
