#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.handle_mgo.subtasks.sync_mashan_hourly_data import SyncMashanHourlyData
from tasks.handle_mgo.subtasks.sync_cma_new_ground import SyncCmaNewGround
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "sync_mashan_hourly_data": (lambda: SyncMashanHourlyData(),'支撑环保=> 同步马山逐小时数据到mongo'),
        "sync_cma_new_ground": (lambda: SyncCmaNewGround(),'支撑环保=> 协助戴铭拉平new_ground表'),
        # "sync_history_cma_new_ground": (SyncCmaNewGround().history,'环保: 协助戴铭同步历史年的数据到new_ground表(需传HISTORY_YEAR)')
    }
    return task_dict
