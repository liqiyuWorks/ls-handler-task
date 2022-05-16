#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.handle_mgo.subtasks.sync_mashan_hourly_data import SyncMashanHourlyData
from tasks.handle_mgo.subtasks.sync_cma_new_ground import SyncCmaNewGround
from basic.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "sync_mashan_hourly_data": lambda: CustomScheduler(SyncMashanHourlyData).run(),
        "sync_cma_new_ground": lambda: CustomScheduler(SyncCmaNewGround).run()
    }
    return task_dict
