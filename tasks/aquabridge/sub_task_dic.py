#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.aquabridge.subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo


def get_task_dic():
    task_dict = {
        "spider_jinzheng_pages2mgo": (lambda: SpiderJinzhengPages2mgo(), '从金正爬页面到mgo'),
    }
    return task_dict
