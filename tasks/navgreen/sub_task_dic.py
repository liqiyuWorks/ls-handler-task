#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.navgreen.subtasks.spider_hifleet_vessels import SpiderHifleetVessels
from tasks.navgreen.subtasks.calculate_vessels_performance import CalculateVesselPerformance, CalculateVesselPerformanceCK
from tasks.navgreen.subtasks.gen_vessel_performance import GenVesselPerformance, GenVesselPerformanceFromRDS


def get_task_dic():
    task_dict = {
        "spider_hifleet_vessels": (lambda: SpiderHifleetVessels(), 'Navgreen => hifleet的船舶档案'),
        "calculate_vessel_performance": (lambda: CalculateVesselPerformance(), 'Navgreen：消费者 => 后台计算船舶性能（油耗）'),
        "calculate_vessel_performance_ck": (lambda: CalculateVesselPerformanceCK(), 'Navgreen：消费者 => CK 后台计算船舶性能（油耗）'),
        "gen_vessel_performance": (lambda: GenVesselPerformance(), 'Navgreen：生产者 => 从 mgo 获取船舶档案，后台计算船舶性能（油耗）'),
        "gen_vessel_performance_from_rds": (lambda: GenVesselPerformanceFromRDS(), 'Navgreen：生产者 => 从缓存 rds 后台计算船舶性能（油耗）'),
    }
    return task_dict
