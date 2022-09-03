#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.handle_redis.subtasks.del_pika_data import DelPikaData
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "del_pika_gfs": (lambda: CustomScheduler(DelPikaData,rds_key="gfs").run(),'每天定时删除Pika的gfs数据'),
        "del_pika_cams_sfc": (lambda: CustomScheduler(DelPikaData,rds_key="cams|sfc").run(),'每天定时删除Pika的cams_sfc数据'),
        "del_pika_cams_pl": (lambda: CustomScheduler(DelPikaData,rds_key="cams|pl").run(),'每天定时删除Pika的cams_pl数据')
    }
    return task_dict
