#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
import datetime
import numpy as np

class DelPikaData(BaseModel):
    def __init__(self, rds_key):
        config = {"rds": True,"handle_db":"rds"}
        super(DelPikaData, self).__init__(config)
        self.days = int(os.getenv('DAYS', 7))
        self.rds_key = rds_key
        if self.days:
            self._hours = self.days * 2 * 24   # 过去 -7 ~ -14 天
        else:
            self._hours = 1
        self.hours_offset_from_zero  = np.arange(self.days * 24, self._hours, 3, dtype=float)
        # print(self.hours_offset_from_zero)


    def get_times(self,start_time, hours):
        start_time = datetime.datetime.strptime(start_time, '%Y%m%d%H')
        return np.array([str(datetime.datetime.strftime(start_time + datetime.timedelta(hours=-h), "%Y%m%d%H")) for h in hours])

    @decorate.exception_capture_close_datebase
    def run(self):
        today = datetime.datetime.now().strftime("%Y%m%d00")
        time_range = self.get_times(today, self.hours_offset_from_zero)
        print(time_range)
        
        for i in range(1440):
            for j in range(721):
                key = f"{self.rds_key}|{i}|{j}"
                res = self.rds.rds.hdel(key, *time_range)
        logging.info(f"{self.rds_key} - {key} delete {res} nums ")
            
