#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.axsmarine.subtasks.spider_live_bunkers_prices import SpiderLiveBunkersPrices
from tasks.axsmarine.subtasks.sync_ships_fuel_from_axs import SyncShipsFuelFromAxs, SyncGlobalVesselsFuelFromAxs, SyncNioVesselsFuelFromAxs

def get_task_dic():
    task_dict = {
        "spider_live_bunkers_prices": (lambda: SpiderLiveBunkersPrices(), 'Axsmarine=> 实时燃油价格'),
        "sync_ships_fuel_from_axs": (lambda: SyncShipsFuelFromAxs(), 'Axsmarine=> 同步船舶燃油价格到mgo'),
        "sync_global_vessels_fuel_from_axs": (lambda: SyncGlobalVesselsFuelFromAxs(), 'Axsmarine=> 从global_vessels的imo获取船舶燃油价格到mgo'),
        # "sync_nio_vessels_fuel_from_axs": (lambda: SyncNioVesselsFuelFromAxs(), 'Axsmarine=> 从nio船舶的imo获取船舶燃油价格到mgo')
    }
    return task_dict
