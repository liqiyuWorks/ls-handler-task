#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.navgreen.subtasks.spider_hifleet_vessels import SpiderHifleetVessels
from tasks.navgreen.subtasks.calculate_vessels_performance import CalculateVesselPerformance


def get_task_dic():
    task_dict = {
        "spider_hifleet_vessels": (lambda: SpiderHifleetVessels(), 'Navgreen => hifleet的船舶档案'),
        "calculate_vessel_performance": (lambda: CalculateVesselPerformance(), 'Navgreen：消费者 => 后台计算船舶性能（油耗）'),
    }
    return task_dict
