#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.ship.subtasks.spider_ets_prices import SpiderEtsPrices
from tasks.ship.subtasks.spider_marinelink import SpiderMarinelink


def get_task_dic():
    task_dict = {
        "spider_ets_prices": (lambda: SpiderEtsPrices(), '航运数据=> 爬取ets_price'),
        "spider_marinelink": (lambda: SpiderMarinelink(), '航运数据=> 爬取航运新闻marinelink https://flo.uri.sh/visualisation/12603037/embed?auto=1'),
    }
    return task_dict
