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

def get_task_dic():

    task_dict = {
        "noaa_ssec_sync_mgo": (lambda: NoaaSyncMgo(),'台风实时数据同步=> noaa和ssec源'),
        "ssec_sync_mgo": (lambda: SsecSyncMgo(),'台风实时数据同步=> ssec源'),
        "gfs_realtime_sync_mgo": (lambda: GfsRealtimeSyncMgo(),'台风实时数据同步=> tcvital源'),
        "gfs_forecast_sync_mgo": (lambda: GfsForecastSyncMgo(),'台风预报数据同步=> GFS预报源'),
        "spider_currMerger2json": (lambda: SpiderCurrmergerJson(), "温州台风网数据下载=> 生成json"),
        "wztfw_sync_mgo": (lambda: WZCurrSyncMgo(), "台风实时预报双数据同步=> 温州台风网源"),
        "match_typhoon_gfs_forecast": (lambda: MatchTyphoonGfsForecast(), "台风离线定时自动匹配=> 匹配实时和gfs预报"),
        "history_match_typhoon_gfs_forecast": (lambda: MatchTyphoonGfsForecast().history(), "历史:台风离线定时自动匹配=> 匹配实时和gfs预报"),
        "history_wztfw_sync_mgo": (lambda: WZCurrSyncMgo().history(), "历史:一次性台风实时预报双数据同步=> 温州台风网源(需传HISTORY_YEAR)"),
        "history_gfs_forecast_sync_mgo": (lambda: GfsForecastSyncMgo().history(),'历史:一次性台风预报数据同步=> GFS预报源(需传HISTORY_YEAR)'),
    }
    return task_dict
