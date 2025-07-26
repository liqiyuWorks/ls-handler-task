#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.navgreen.subtasks.spider_hifleet_vessels import SpiderHifleetVessels
from tasks.navgreen.subtasks.gen_vessel_performance import GenVesselPerformance, GenVesselPerformanceFromRDS, GenVesselVPFromMGO
from tasks.navgreen.subtasks.calc_vessel_performance_details import CalcVesselPerformanceDetails
from tasks.navgreen.subtasks.spider_windy_zoom_storms import SpiderWindyZoomStorms
from tasks.navgreen.subtasks.calc_vessel_performance_details_from_wmy import CalcVesselPerformanceDetailsFromWmy
from tasks.navgreen.subtasks.spider_vessel_Lloyd_info import SpiderVesselsLloydInfo
from tasks.navgreen.subtasks.spider_vessel_finder_vessels import SpiderVesselFinderVessels
from tasks.navgreen.subtasks.rich_hifleet_vessels_info import RichHifleetVesselsInfo

def get_task_dic():
    task_dict = {
        "spider_hifleet_vessels": (lambda: SpiderHifleetVessels(), 'Navgreen => 1、hifleet的船舶列表'),
        "rich_hifleet_vessels_info": (lambda: RichHifleetVesselsInfo(), 'Navgreen => 2、丰富hifleet的船舶详情档案'),
        # "spider_vessel_finder_vessels": (lambda: SpiderVesselFinderVessels(), 'Navgreen => vesselfinder的列表'),
        "spider_vessel_Lloyd_info": (lambda: SpiderVesselsLloydInfo(), 'Navgreen => ***查询船舶劳氏船级社的档案'),
        "calc_vessel_performance_details": (lambda: CalcVesselPerformanceDetails(), '****Navgreen：后台计算船舶性能详情'),
        "calc_vessel_performance_details_from_wmy": (lambda: CalcVesselPerformanceDetailsFromWmy(), '****Navgreen：从茂源那边获取 mmsi 去计算船舶性能详情'),
        "spider_windy_zoom_storms": (lambda: SpiderWindyZoomStorms(), '****Navgreen：爬取 windy 的气旋和台风数据'),
    }
    return task_dict
