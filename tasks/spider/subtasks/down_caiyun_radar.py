#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import os
import requests
from pkg.util.file import check_create_path
from pkg.public.obs import ObsStore
from pkg.public.decorator import decorate
from pkg.public.models import BaseModel


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


class DownCaiyunRadar(BaseModel):
    # radar_url = "http://data.istrongcloud.com/data/images/radar/mingle/caiyun_transparent.json?v=1693879739161"
    radar_url = "http://data.istrongcloud.com/data/images/radar/mingle/caiyun_transparent.json?v={}"

    def __init__(self) -> None:
        config = {"rds": True, "handle_db": "rds"}
        super(DownCaiyunRadar, self).__init__(config)
        # print("rds", self.rds.rds.set(
        #     "wztfw_radar_newest_reporttime", "202309051305"))
        # print("rds", self.rds.rds.set(
        #     "wztfw_cloud_newest_reporttime", "202309051240"))
        self._file_path = os.getenv(
            "FILE_PATH", "/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task")
        self.step = int(os.getenv("STEP", 3))
        self._rds_key = "wztfw_radar_newest_reporttime"

    def upload_obs(self, save_file_path, obs_key):
        obs_data = {"file_name": save_file_path, "obs_key": obs_key}
        obs_store = ObsStore(obs_config)
        url = obs_store.set(obs_data)
        print('==>上传OBS成功，url={}'.format(url))

    def save_local(self, save_file_path, res):
        check_create_path(save_file_path)
        # 将下载到的图片数据写入文件
        with open(save_file_path, 'wb') as f:
            f.write(res.content)
        print(f'=> {save_file_path} write ok')

    def check_duplicate(self, rds_newest_time, now_time):
        if rds_newest_time < now_time:
            self.rds.rds.set(
                self._rds_key, now_time)
            return True
        return False

    @decorate.exception_capture
    def run(self):
        # 获取当前本地时间
        local_time = time.localtime()
        # 将本地时间转换为时间戳
        timestamp = int(time.mktime(local_time))

        req_url = self.radar_url.format(timestamp)
        response = requests.get(req_url)
        radar_list = response.json()

        # 遍历res json\
        for rar in radar_list[-self.step:]:
            png_url = rar.get("url")
            reporttime_name = rar.get("name").lower()
            # 分别保存
            response = requests.get(png_url)
            year = reporttime_name[:4]
            mon = reporttime_name[4:6]
            day = reporttime_name[6:8]
            save_file_path = self._file_path + \
                f"/{year}/{mon}/{day}/" + reporttime_name
            # obs_key = f"radar/{year}/{mon}/{day}/" + reporttime_name
            rds_newest_time = self.rds.rds.get(self._rds_key)
            now_time = str(reporttime_name)[:-4]
            if self.check_duplicate(rds_newest_time, now_time):
                self.save_local(save_file_path, response)
                # self.upload_obs(save_file_path, obs_key)
