#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.handle_redis.subtasks.del_pika_data import DelPikaData

def get_task_dic():
    task_dict = {
        "del_pika_gfs": (lambda: DelPikaData(rds_key="gfs"),'每天定时删除Pika的gfs数据'),
        "del_pika_cams_sfc": (lambda: DelPikaData(rds_key="cams|sfc"),'每天定时删除Pika的cams_sfc数据'),
        "del_pika_cams_pl": (lambda: DelPikaData(rds_key="cams|pl"),'每天定时删除Pika的cams_pl数据')
    }
    return task_dict
