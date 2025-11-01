#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.axsmarine.subtasks.spider_live_bunkers_prices import SpiderLiveBunkersPrices
from tasks.axsmarine.subtasks.sync_ships_fuel_from_axs import SyncShipsFuelFromAxs

def get_task_dic():
    task_dict = {
        "spider_live_bunkers_prices": (lambda: SpiderLiveBunkersPrices(), 'Axsmarine=> 实时燃油价格'),
        "sync_ships_fuel_from_axs": (lambda: SyncShipsFuelFromAxs(), 'Axsmarine=> 同步船舶燃油价格到mgo'),
        "sync_search_vessels_fuel_from_axs": (lambda: SyncShipsFuelFromAxs().run_search_vessels_by_query(), 'Axsmarine=> 从搜索历史船舶燃油价格到mgo')
    }
    return task_dict
