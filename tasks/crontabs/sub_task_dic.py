#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.crontabs.subtasks.clean_bosch_caiyun_png import CleanBoschCaiyunPng
from tasks.crontabs.subtasks.HEU_typhoon2Josn import HeuGenTyphoonJson
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        "clean_bosch_caiyun_png": (lambda:CleanBoschCaiyunPng(),'定时任务=> 删除给博世生成的彩云图片'),
        "heu_typhoon2json": (lambda: HeuGenTyphoonJson(),'定时任务=> 生成哈工程台风json文件'),
    }
    return task_dict
