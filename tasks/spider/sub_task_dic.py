#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.spider.subtasks.down_q_weather import DownQWeather
from tasks.spider.subtasks.down_wushikj_radar import DownWushikjRadar
from tasks.spider.subtasks.down_wushikj_cloud_imagery import DownWushikjCloudImagery


def get_task_dic():
    task_dict = {
        "down_q_weather": (lambda: DownQWeather(), '支撑环保=> 下载q-weather历史数据'),
        "down_wushikj_radar": (lambda: DownWushikjRadar(), '雷达数据=> 下载Down Wushikj Radar'),
        "down_wushikj_cloud_imagery": (lambda: DownWushikjCloudImagery(), '云图数据=> 下载Down Wushikj cloud imagery'),
    }
    return task_dict
