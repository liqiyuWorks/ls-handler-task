#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.typhoon.subtasks.noaa_sync_mgo import NoaaSyncMgo
from tasks.typhoon.subtasks.ssec_sync_mgo import SsecSyncMgo
from tasks.typhoon.subtasks.typhoon_sync_mgo import TyphoonSyncMgo
from tasks.typhoon.subtasks.gfs_sync_mgo import GfsSyncMgo
from tasks.typhoon.subtasks.spider_currMerger2json import SpiderCurrmergerJson
from tasks.typhoon.subtasks.wz_curr_sync_mgo import WZCurrSyncMgo
from pkg.public.scheduler import CustomScheduler

def get_task_dic():

    task_dict = {
        "noaa_ssec_sync_mgo": (lambda: CustomScheduler(NoaaSyncMgo).run(),'同时下载noaa和ssec台风源到mongo'),
        # "ssec_sync_mgo": (lambda: CustomScheduler(SsecSyncMgo).run(),'下载ssec台风源到mongo'),
        "typhoon_sync_mgo": (lambda: CustomScheduler(TyphoonSyncMgo).run(),'同步实时监测台风的数据到mongo'),
        "gfs_sync_mgo": (lambda: CustomScheduler(GfsSyncMgo).run(),'同步GFS预报的数据到mongo'),
        "spider_currMerger2json": (lambda: CustomScheduler(SpiderCurrmergerJson).run(), "下载台风数据，生成json"),
        "wz_sync_mgo": (lambda: CustomScheduler(WZCurrSyncMgo).run(), "同步温州台风实时和预报数据！"),
        "history_wz_sync_mgo": (lambda: WZCurrSyncMgo().history(), "一次性同步温州台风实时和预报数据(需传HISTORY_YEAR)"),
        "history_gfs_sync_mgo": (lambda: GfsSyncMgo().history(),'一次性导入GFS的历史数据(需传HISTORY_YEAR)'),
    }
    return task_dict
