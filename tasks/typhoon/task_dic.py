#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.typhoon.noaa_sync_mgo import NoaaSyncMgo
from basic.scheduler import CustomScheduler

def get_task_dic():

    task_dict = {
        "noaa_sync_mgo": lambda: CustomScheduler(NoaaSyncMgo).run(),
    }
    print('任务列表: ',task_dict)

    return task_dict
