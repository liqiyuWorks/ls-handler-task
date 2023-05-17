#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import requests
import datetime
import logging
import os


def req_td_rest(url, params, headers={"Authorization": "Basic cm9vdDp0YW9zZGF0YQ=="}):
    res = requests.post(url=url,
                        data=params,
                        headers=headers
                        )
    print("=> res", res.status_code, res.text)
    return res.json()


class MonitorTD88Sync:
    def __init__(self):
        self.TD_URL = os.getenv("TD_URL", "tdengine.ninecosmos.cn")

    @decorate.exception_capture
    def run(self):
        date = (datetime.datetime.utcnow() +
                datetime.timedelta(days=-2)).strftime("%Y%m%d")
        exe_sql = "show databases"
        url = f"http://{self.TD_URL}/rest/sql/db_mfwam_0p08_{date}00"
        print("=> url", url)
        req_td_rest(url=url, params=exe_sql)
        # source_map = {}
        # source_map["gfs_25"] = []
        # source_map["smoc_25"] = []
        # source_map["smoc_08"] = []
        # source_map["mfwam_25"] = []
        # source_map["mfwam_08"] = []
        # for i in data:
        #     db_name = i[0]
        #     db_name_list = str(db_name).split("_")
        #     if len(db_name_list) == 4:
        #         if db_name_list[1] == "gfs" and db_name_list[2] == "0p25":
        #             source_map["gfs_25"].append(db_name_list[-1])
        #         if db_name_list[1] == "mfwam" and db_name_list[2] == "0p25":
        #             source_map["mfwam_25"].append(db_name_list[-1])
        #         if db_name_list[1] == "mfwam" and db_name_list[2] == "0p08":
        #             source_map["mfwam_08"].append(db_name_list[-1])
        #         if db_name_list[1] == "smoc" and db_name_list[2] == "0p25":
        #             source_map["smoc_25"].append(db_name_list[-1])
        #         if db_name_list[1] == "smoc" and db_name_list[2] == "0p08":
        #             source_map["smoc_08"].append(db_name_list[-1])

        # source_map["gfs_25"].sort(reverse=True)
        # source_map["mfwam_08"].sort(reverse=True)
        # source_map["mfwam_25"].sort(reverse=True)
        # source_map["smoc_08"].sort(reverse=True)
        # source_map["smoc_25"].sort(reverse=True)
        # for k, v in source_map.items():
        #     if v:
        #         if v[0] < date:
        #             logging.warn(f"{k} 没有及时同步 => {v}")
