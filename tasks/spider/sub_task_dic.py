#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.spider.subtasks.down_q_weather import DownQWeather
from tasks.spider.subtasks.down_wushikj_radar import DownWushikjRadar
from tasks.spider.subtasks.down_wushikj_cloud_imagery import DownWushikjCloudImagery
from tasks.spider.subtasks.down_caiyun_radar import DownCaiyunRadar
from tasks.spider.subtasks.down_zjwater_cloud_imagery import DownZjwaterCloudImagery
# from tasks.spider.subtasks.down_tf121_cloud_imagery import DownTf121CloudImagery


def get_task_dic():
    task_dict = {
        "down_q_weather": (lambda: DownQWeather(), '支撑环保=> 下载q-weather历史数据'),

        "down_wushikj_radar": (lambda: DownWushikjRadar(), '雷达数据=> 下载Down Wushikj Radar'),
        "down_caiyun_radar": (lambda: DownCaiyunRadar(), '温州台风网雷达=> 下载Radar到本地保存'),
        # "down_wushikj_cloud_imagery": (lambda: DownWushikjCloudImagery(), '云图数据=> 下载 Wushikj cloud imagery'),
        "down_zjwater_cloud_imagery": (lambda: DownZjwaterCloudImagery(), '温州台风网云图=> 下载 cloud imagery'),
        # "down_tf121_cloud_imagery": (lambda: DownTf121CloudImagery(), '深圳台风网云图=> 下载 cloud imagery'),
    }
    return task_dict
