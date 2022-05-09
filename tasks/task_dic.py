#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import imp
import os
from tasks.typhoon.task_dic import get_task_dic as get_typhoon_dic
from basic.util import load_dic

def get_task_dic():
    task_dic = {}
    run_mode = os.getenv('RUN_MODE', '*')
    if run_mode == '*' or run_mode.find('forecast') >= 0:
        load_dic(task_dic, get_typhoon_dic())
    return task_dic