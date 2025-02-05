#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.ship.subtasks.spider_ets_prices import SpiderEtsPrices
from tasks.ship.subtasks.spider_marinelink import SpiderMarinelink
from tasks.ship.subtasks.spider_maritime_executive import SpiderMaritimeExecutive
from tasks.ship.subtasks.spider_hyfocus import SpiderHyfocus
from tasks.ship.subtasks.spider_windy_typhoon_json import SpiderWindyTyphoonJson
from tasks.ship.subtasks.spider_weiyun_cargo_agency import SpiderWeiyunCargoAgencies
from tasks.ship.subtasks.spider_weiyun_ship_owners import SpiderWeiyunShipOwners
from tasks.ship.subtasks.spider_sol import SpideSol


def get_task_dic():
    task_dict = {
        "spider_ets_prices": (lambda: SpiderEtsPrices(), '航运数据=> ets_price'),
        "spider_marinelink": (lambda: SpiderMarinelink(), '航运数据=> marinelink https://flo.uri.sh/visualisation/12603037/embed?auto=1'),
        "spider_maritime_executive": (lambda: SpiderMaritimeExecutive(), '航运数据=> maritime_executive https://www.maritime-executive.com/'),
        "spider_hyfocus": (lambda: SpiderHyfocus(), '航运数据=> https://www.hyqfocus.com/m/bunker_index.jsp'),
        "spider_sol": (lambda: SpideSol(), '航运数据=> https://www.hyqfocus.com/m/bunker_index.jsp'),
        "spider_windy_typhoon_json": (lambda: SpiderWindyTyphoonJson(), '航运数据=> https://www.hyqfocus.com/m/bunker_index.jsp'),
        #### 线索 ####
        "spider_weiyun_cargo_agencies": (lambda: SpiderWeiyunCargoAgencies(), '租家线索'),
        # "spider_weiyun_agency_local": (lambda: SpiderWeiyunAgency().run_local(), '租家线索'),
        "spider_weiyun_ship_owners": (lambda: SpiderWeiyunShipOwners().run_once(), '船东线索'),
        #### 线索 ####
        
    }
    return task_dict
