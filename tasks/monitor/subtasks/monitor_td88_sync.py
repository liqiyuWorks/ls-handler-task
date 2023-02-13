#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import requests
import datetime
import logging


def req_td_rest(url, params, headers={"Authorization": "Basic cm9vdDp0YW9zZGF0YQ=="}):
    res = requests.post(url=url,
                        data=params,
                        headers=headers,
                        verify=False
                        )
    return res.json()


class MonitorTD88Sync:
    def __init__(self):
        self.TD_URL = "124.70.86.179:6041"

    @decorate.exception_capture
    def run(self):
        date = (datetime.datetime.utcnow() +
                datetime.timedelta(days=-2)).strftime("%Y%m%d%H")
        exe_sql = "show databases"
        res = req_td_rest(
            url=f"http://{self.TD_URL}/rest/sql/db_gfs'", params=exe_sql)

        data = res.get("data", [])
        source_map = {}
        source_map["gfs_25"] = []
        source_map["smoc_25"] = []
        source_map["smoc_08"] = []
        source_map["mfwam_25"] = []
        source_map["mfwam_08"] = []
        for i in data:
            db_name = i[0]
            db_name_list = str(db_name).split("_")
            if len(db_name_list) == 4:
                if db_name_list[1] == "gfs" and db_name_list[2] == "0p25":
                    source_map["gfs_25"].append(db_name_list[-1])
                if db_name_list[1] == "mfwam" and db_name_list[2] == "0p25":
                    source_map["mfwam_25"].append(db_name_list[-1])
                if db_name_list[1] == "mfwam" and db_name_list[2] == "0p08":
                    source_map["mfwam_08"].append(db_name_list[-1])
                if db_name_list[1] == "smoc" and db_name_list[2] == "0p25":
                    source_map["smoc_25"].append(db_name_list[-1])
                if db_name_list[1] == "smoc" and db_name_list[2] == "0p08":
                    source_map["smoc_08"].append(db_name_list[-1])

        source_map["gfs_25"].sort(reverse=True)
        source_map["mfwam_08"].sort(reverse=True)
        source_map["mfwam_25"].sort(reverse=True)
        source_map["smoc_08"].sort(reverse=True)
        source_map["smoc_25"].sort(reverse=True)
        for k, v in source_map.items():
            if v:
                if v[0] < date:
                    logging.warn(f"{k} 没有及时同步 => {v}")
