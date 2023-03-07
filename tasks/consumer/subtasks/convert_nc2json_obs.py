#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
from tasks.consumer.deps import read_gfs_wind_nc, check_create_path, ObsStore, read_era5_wind_nc
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
        self._3h_data = []
        self._last_3h_data = []
        self._header_u = {
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
        self._header_v = {
            "nx": 1440,
            "ny": 721,
            "lo1": -180,
            "la1": 90,
            "lo2": 179.75,
            "la2": -90,
            "dx": 0.25,
            "dy": 0.25,
            "parameterCategory": 2,
            "parameterNumber": 3
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
            self._last_3h_data = res.json()

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
                data = [data["wind_u"], data["wind_v"]]
                # self._3h_data = np.array(data["data"]["data"])
                self._3h_data = data
                self.upload_obs(self._this_time, data)

    def interpolation_1h_2h(self):
        # 插值1h
        u_space = (
            np.array(self._3h_data[0]["data"]) - np.array(self._last_3h_data[0]["data"]))/3
        v_space = (
            np.array(self._3h_data[1]["data"]) - np.array(self._last_3h_data[1]["data"]))/3
        self._1h_data_u = self._last_3h_data[0]["data"] + u_space
        self._1h_data_v = self._last_3h_data[1]["data"] + v_space
        self._1h_data_u = np.around(
            self._1h_data_u,  # numpy数组或列表
            decimals=2  # 保留几位小数
        )
        self._1h_data_v = np.around(
            self._1h_data_v,  # numpy数组或列表
            decimals=2  # 保留几位小数
        )
        _1h_data = [
            {
                "header": self._header_u,
                "data": list(self._1h_data_u)
            },
            {
                "header": self._header_v,
                "data": list(self._1h_data_v)
            }
        ]
        self.upload_obs(self._1h_time, _1h_data)

        # 插值2h
        self._2h_data_u = self._last_3h_data[0]["data"] + u_space*2
        self._2h_data_v = self._last_3h_data[1]["data"] + u_space*2
        self._2h_data_u = np.around(
            self._2h_data_u,  # numpy数组或列表
            decimals=2  # 保留几位小数
        )
        self._2h_data_v = np.around(
            self._2h_data_v,  # numpy数组或列表
            decimals=2  # 保留几位小数
        )
        _2h_data = [
            {
                "header": self._header_u,
                "data": list(self._2h_data_u)
            },
            {
                "header": self._header_v,
                "data": list(self._2h_data_v)
            },
        ]
        self.upload_obs(self._2h_time, _2h_data)

    @decorate.exception_capture
    def run(self, task={}):
        input_file = task.get("input_file")
        self.upload_gfs_wind_3h_obs(input_file)
        self.get_last_3h_data()  # 获取上个时刻的数据
        if type(self._last_3h_data) == list and len(self._last_3h_data) ==2:
            self.interpolation_1h_2h()  # 插值缺失2h的数据
        else:
            self.upload_obs(self._1h_time, self._3h_data)
            self.upload_obs(self._2h_time, self._3h_data)


class ConvertEra5Windnc2jsonObs:
    def __init__(self):
        self._this_time = None
        self._header_u = {
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
        self._header_v = {
            "nx": 1440,
            "ny": 721,
            "lo1": -180,
            "la1": 90,
            "lo2": 179.75,
            "la2": -90,
            "dx": 0.25,
            "dy": 0.25,
            "parameterCategory": 2,
            "parameterNumber": 3
        }

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

    def upload_era5_wind_obs(self, input_file):
        print(input_file)
        if input_file:
            for data in read_era5_wind_nc(input_file):
                if data:
                    self._this_time = data["dt"]
                    wind_u = {"header": self._header_u, "data": data["wind_u"]}
                    wind_v = {"header": self._header_v, "data": data["wind_v"]}
                    data = [wind_u, wind_v]
                    self.upload_obs(self._this_time, data)

    @decorate.exception_capture
    def run(self, task={}):
        input_file = task.get("input_file")
        self.upload_era5_wind_obs(input_file)
