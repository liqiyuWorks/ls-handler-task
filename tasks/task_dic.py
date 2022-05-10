#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from tasks.typhoon.task_dic import get_task_dic as get_typhoon_dic
from tasks.irrigation.task_dic import get_task_dic as get_irrigation_dic
from basic.util import load_dic

def get_task_dic():
    task_dic = {}
    load_dic(task_dic, get_typhoon_dic())
    load_dic(task_dic, get_irrigation_dic())
    print('\n===任务列表start===')
    for k,v in task_dic.items():
        print(f'{k} - {v}')
    print('===任务列表over===\n')
    return task_dic