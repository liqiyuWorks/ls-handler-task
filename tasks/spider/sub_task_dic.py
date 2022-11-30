#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.spider.subtasks.down_q_weather import DownQWeather

def get_task_dic():
    task_dict = {
        "down_q_weather": (lambda: DownQWeather(),'环保：下载q-weather历史数据'),
    }
    return task_dict
