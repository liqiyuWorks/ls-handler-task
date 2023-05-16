#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.monitor.subtasks.monitor_td88_sync import MonitorTD88Sync
from tasks.monitor.subtasks.monitor_zjbcw_api import MonitorBCWApis


def get_task_dic():
    task_dict = {
        "monitor_td88_sync": (lambda: MonitorTD88Sync(), '监控任务=> 监控TDengine88集群的数据库'),
        "monitor_zjbcw_api": (lambda: MonitorBCWApis(), '监控任务=> 监控中交宝船网的服务'),
    }
    return task_dict
