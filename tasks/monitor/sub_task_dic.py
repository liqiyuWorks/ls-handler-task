#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.monitor.subtasks.monitor_td88_sync import MonitorTD88Sync


def get_task_dic():
    task_dict = {
        "monitor_td88_sync": (lambda: MonitorTD88Sync(), '监控任务=> 监控TDengine88集群的数据库'),
    }
    return task_dict
