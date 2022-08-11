#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.crontabs.subtasks.clean_bosch_caiyun_png import CleanBoschCaiyunPng
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "clean_bosch_caiyun_png": (lambda: CustomScheduler(CleanBoschCaiyunPng).run(),'定时生成GFS的处理文件发送到nc2redis'),
    }
    return task_dict
