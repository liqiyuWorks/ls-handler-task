#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.handle_mgo.sync_mashan_hourly_data import SyncMashanHourlyData
from basic.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "sync_mashan_hourly_data": lambda: CustomScheduler(SyncMashanHourlyData).run()
    }
    return task_dict
