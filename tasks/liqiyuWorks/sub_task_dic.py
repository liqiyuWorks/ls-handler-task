#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.liqiyuWorks.subtasks.spider_weibo import WeiboSpider, WeiboSpiderDroughtHeatSandstorm, WeiboSpiderGeographyEducation


def get_task_dic():
    task_dict = {
        "weibo_spider_water": (lambda: WeiboSpider(), '个人业务=> 微博爬虫'),
        "weibo_spider_drought_heat_sandstorm": (lambda: WeiboSpiderDroughtHeatSandstorm(), '个人业务=> 微博爬虫-干旱热浪沙尘暴'),
        "weibo_spider_geography_education": (lambda: WeiboSpiderGeographyEducation(), '个人业务=> 微博爬虫-地理教育'),
    }
    return task_dict
