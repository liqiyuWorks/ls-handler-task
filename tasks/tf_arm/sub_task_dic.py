#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.tf_arm.subtasks.calculate_vessels_performance import CalculateVesselPerformanceCK


def get_task_dic():
    task_dict = {
        # "calculate_vessel_performance": (lambda: CalculateVesselPerformance(), 'Navgreen：消费者 => 后台计算船舶性能（油耗）'),
        "calculate_vessel_performance_ck": (lambda: CalculateVesselPerformanceCK(), 'Navgreen：消费者 => CK 后台计算船舶性能（油耗）'),
    }
    return task_dict
