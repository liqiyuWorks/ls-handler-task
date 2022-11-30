#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.crontabs.subtasks.clean_bosch_caiyun_png import CleanBoschCaiyunPng
from tasks.crontabs.subtasks.HEU_typhoon2Josn import HeuGenTyphoonJson
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "clean_bosch_caiyun_png": (lambda:CleanBoschCaiyunPng(),'定时生成GFS的处理文件发送到nc2redis'),
        "heu_typhoon2json": (lambda: HeuGenTyphoonJson(),'定时生成哈工程所需的台风json文件'),
    }
    return task_dict
