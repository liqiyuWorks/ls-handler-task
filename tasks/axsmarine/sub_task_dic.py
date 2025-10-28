#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.axsmarine.subtasks.spider_live_bunkers_prices import SpiderLiveBunkersPrices


def get_task_dic():
    task_dict = {
        "spider_live_bunkers_prices": (lambda: SpiderLiveBunkersPrices(), 'Axsmarine=> 实时燃油价格')
    }
    return task_dict
