#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.typhoon.subtasks.noaa_realtime_sync_mgo import NoaaSyncMgo
from tasks.typhoon.subtasks.ssec_realtime_sync_mgo import SsecSyncMgo
from tasks.typhoon.subtasks.gfs_realtime_sync_mgo import GfsRealtimeSyncMgo
from tasks.typhoon.subtasks.gfs_forecast_sync_mgo import GfsForecastSyncMgo
from tasks.typhoon.subtasks.spider_currMerger2json import SpiderCurrmergerJson
from tasks.typhoon.subtasks.wztfw_sync_mgo import WZCurrSyncMgo
from tasks.typhoon.subtasks.match_typhoon_gfs_forecast import MatchTyphoonGfsForecast
from pkg.public.scheduler import CustomScheduler

def get_task_dic():

    task_dict = {
        "noaa_ssec_sync_mgo": (lambda: NoaaSyncMgo(),'同时下载noaa和ssec台风源到mongo'),
        "ssec_sync_mgo": (lambda: SsecSyncMgo(),'下载ssec台风源到mongo'),
        "gfs_realtime_sync_mgo": (lambda: GfsRealtimeSyncMgo(),'同步GFS实时监测的数据到mgo'),
        "gfs_forecast_sync_mgo": (lambda: GfsForecastSyncMgo(),'同步GFS预报的数据到mgo'),
        "spider_currMerger2json": (lambda: SpiderCurrmergerJson(), "下载台风数据，生成json"),
        "wztfw_sync_mgo": (lambda: WZCurrSyncMgo(), "同步温州台风实时和预报数据！"),
        "match_typhoon_gfs_forecast": (lambda: MatchTyphoonGfsForecast(), "定匹配新台风库实时台风的预报台风编号"),
        
        "history_wztfw_sync_mgo": (lambda: WZCurrSyncMgo().history(), "一次性同步温州台风实时和预报数据(需传HISTORY_YEAR)"),
        "history_gfs_forecast_sync_mgo": (lambda: GfsForecastSyncMgo().history(),'一次性导入GFS的历史数据(需传HISTORY_YEAR)'),
    }
    return task_dict
