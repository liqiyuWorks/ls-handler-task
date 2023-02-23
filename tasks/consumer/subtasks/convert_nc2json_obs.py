#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
from tasks.consumer.deps import read_gfs_wind_nc, check_create_path, ObsStore
import logging
import requests
import datetime
import numpy as np
from pkg.public.decorator import decorate

obs_config = {
    "obs_ak": os.getenv('OBS_AK', 'JKRANSLTIOLXCZLBECVX'),
    "obs_sk": os.getenv('OBS_SK', 'ZhRyKdZq0yAGqFkXgbI2T8kMIaaapNWrHUbbb4IN'),
    "obs_server": os.getenv(
        'OBS_SERVER', 'https://obs.cn-north-4.myhuaweicloud.com'),
    "obs_bucket": os.getenv('OBS_BUCKET', 'nine-confidential'),
    "obs_root": os.getenv('OBS_ROOT', 'air/zte'),
    "obs_domain": os.getenv('OBS_DOMAIN', 'https://cfdt.ninecosmos.cn'),
}


class ConvertGFSWindnc2jsonObs:
    def __init__(self):
        self._this_time = None
        self._last_3h_time = None
        self._3h_data = None
        self._last_3h_data = None
        self._header = {
            "nx": 1440,
            "ny": 721,
            "lo1": -180,
            "la1": 90,
            "lo2": 179.75,
            "la2": -90,
            "dx": 0.25,
            "dy": 0.25,
            "parameterCategory": 2,
            "parameterNumber": 2
        }

    def get_last_3h_data(self):
        self._this_time = datetime.datetime.strptime(
            self._this_time, "%Y%m%d%H")
        self._last_3h_time = (
            self._this_time + datetime.timedelta(hours=-3)).strftime("%Y%m%d%H")
        self._1h_time = (
            self._this_time + datetime.timedelta(hours=-2)).strftime("%Y%m%d%H")
        self._2h_time = (
            self._this_time + datetime.timedelta(hours=-1)).strftime("%Y%m%d%H")
        year = self._last_3h_time[:4]
        mon = self._last_3h_time[4:6]
        day = self._last_3h_time[6:8]
        hour = self._last_3h_time[8:]
        url = f"http://cfdt.ninecosmos.cn/air/zte/wind/{year}/{mon}/{day}/{hour}.json"
        res = requests.get(url=url)
        if res.status_code == 404:
            logging.error(">>> 暂无上个时刻数据 >>> 不进行插值，直接赋值")
        else:
            self._last_3h_data = np.array(res.json().get("data"))

    def upload_obs(self, date, data):
        year = date[:4]
        mon = date[4:6]
        day = date[6:8]
        hour = date[8:]
        file = f'wind/{year}/{mon}/{day}/{hour}.json'
        json_str = json.dumps(data)
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

    def upload_gfs_wind_3h_obs(self, input_file):
        print(input_file)
        if input_file:
            data = read_gfs_wind_nc(input_file)
            if data:
                self._this_time = data["dt"]
                self._3h_data = np.array(data["data"]["data"])
                self.upload_obs(self._this_time, data["data"])

    def interpolation_1h_2h(self):
        space = (self._3h_data - self._last_3h_data)/3
        self._1h_data = self._last_3h_data + space
        self._1h_data = np.around(
            self._1h_data,  # numpy数组或列表
            decimals=2  # 保留几位小数
        )
        self._1h_data = {
            "header": self._header,
            "data": list(self._1h_data)
        }
        self.upload_obs(self._1h_time, self._1h_data)
        self._2h_data = self._last_3h_data + space*2
        self._2h_data = np.around(
            self._2h_data,  # numpy数组或列表
            decimals=2  # 保留几位小数
        )
        self._2h_data = {
            "header": self._header,
            "data": list(self._2h_data)
        }
        self.upload_obs(self._2h_time, self._2h_data)

    @decorate.exception_capture
    def run(self, task={}):
        input_file = task.get("input_file")
        self.upload_gfs_wind_3h_obs(input_file)
        self.get_last_3h_data()  # 获取上个时刻的数据
        if self._last_3h_data is not None:
            self.interpolation_1h_2h()  # 插值缺失2h的数据
        else:
            # 就地赋值 3h
            self._3h_data = {
                "header": self._header,
                "data": list(self._3h_data)
            }
            self.upload_obs(self._1h_time, self._3h_data)
            self.upload_obs(self._2h_time, self._3h_data)
