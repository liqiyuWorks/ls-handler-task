#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.liqiyuWorks.subtasks.spider_weibo import WeiboSpider


def get_task_dic():
    task_dict = {
        "weibo_spider_water": (lambda: WeiboSpider(), '个人业务=> 微博爬虫'),
    }
    return task_dict
