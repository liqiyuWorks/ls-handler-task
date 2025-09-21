#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.testapi.subtasks.run_testapi import RunTestApi

def get_task_dic():
    task_dict = {
        "testapi_ship": (lambda: RunTestApi(testapi_path="tasks/testapi/test_cases/ship"),'自动化测试=> 航运台风'),
        "testapi_meteo": (lambda: RunTestApi(testapi_path="tasks/testapi/test_cases/meteo"),'自动化测试=> 航运气象要素'),
    }
    return task_dict
