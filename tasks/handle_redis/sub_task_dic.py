#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.handle_redis.subtasks.del_pika_gfs import DelPikaGfs
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "del_pika_gfs": (lambda: CustomScheduler(DelPikaGfs).run(),'每天定时删除Pika的gfs数据')
    }
    return task_dict
