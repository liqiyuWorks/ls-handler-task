#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.typhoon.noaa_sync_mgo import NoaaSyncMgo
from tasks.typhoon.ssec_sync_mgo import SsecSyncMgo
from tasks.typhoon.typhoon_sync_mgo import TyphoonSyncMgo
from basic.scheduler import CustomScheduler

def get_task_dic():

    task_dict = {
        "noaa_sync_mgo": lambda: CustomScheduler(NoaaSyncMgo).run(),
        "ssec_sync_mgo": lambda: CustomScheduler(SsecSyncMgo).run(),
        "typhoon_sync_mgo": lambda: CustomScheduler(TyphoonSyncMgo).run(),
    }
    return task_dict
