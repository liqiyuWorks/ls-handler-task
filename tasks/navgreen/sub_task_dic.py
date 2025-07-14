#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.navgreen.subtasks.spider_hifleet_vessels import SpiderHifleetVessels
from tasks.navgreen.subtasks.gen_vessel_performance import GenVesselPerformance, GenVesselPerformanceFromRDS, GenVesselVPFromMGO
from tasks.navgreen.subtasks.calc_vessel_performance_details import CalcVesselPerformanceDetails
from tasks.navgreen.subtasks.spider_windy_zoom_storms import SpiderWindyZoomStorms
from tasks.navgreen.subtasks.calc_vessel_performance_details_from_wmy import CalcVesselPerformanceDetailsFromWmy

def get_task_dic():
    task_dict = {
        "spider_hifleet_vessels": (lambda: SpiderHifleetVessels(), 'Navgreen => hifleet的船舶档案'),
        # "gen_vessel_performance_hifleet": (lambda: GenVesselPerformance(), 'Navgreen：生产者 => 从 mgo 获取船舶档案，后台计算船舶性能（油耗）'),
        # "gen_vessel_performance_from_rds": (lambda: GenVesselPerformanceFromRDS(), 'Navgreen：生产者 => 从缓存 rds 后台计算船舶性能（油耗）'),
        # "gen_ck_vp_from_mgo": (lambda: GenVesselVPFromMGO(), '****Navgreen：每月 1 号生产一次 => 从 mgo 获取船舶档案，后台根据 CK计算船舶性能（油耗）'),
        "calc_vessel_performance_details": (lambda: CalcVesselPerformanceDetails(), '****Navgreen：后台计算船舶性能详情'),
        "calc_vessel_performance_details_from_wmy": (lambda: CalcVesselPerformanceDetailsFromWmy(), '****Navgreen：从茂源那边获取 mmsi 去计算船舶性能详情'),
        "spider_windy_zoom_storms": (lambda: SpiderWindyZoomStorms(), '****Navgreen：爬取 windy 的气旋和台风数据'),
    }
    return task_dict
