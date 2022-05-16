#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.typhoon.subtasks.noaa_sync_mgo import NoaaSyncMgo
from tasks.typhoon.subtasks.ssec_sync_mgo import SsecSyncMgo
from tasks.typhoon.subtasks.typhoon_sync_mgo import TyphoonSyncMgo
from tasks.typhoon.subtasks.gfs_sync_mgo import GfsSyncMgo
from tasks.typhoon.subtasks.spider_currMerger2json import SpiderCurrmergerJson
from basic.scheduler import CustomScheduler

def get_task_dic():

    task_dict = {
        "noaa_sync_mgo": lambda: CustomScheduler(NoaaSyncMgo).run(),
        "ssec_sync_mgo": lambda: CustomScheduler(SsecSyncMgo).run(),
        "typhoon_sync_mgo": lambda: CustomScheduler(TyphoonSyncMgo).run(),
        "gfs_sync_mgo": lambda: CustomScheduler(GfsSyncMgo).run(),
        "spider_currMerger2json": lambda: CustomScheduler(SpiderCurrmergerJson).run(),
        "history_gfs_sync_mgo": lambda: GfsSyncMgo().history(),
    }
    return task_dict
