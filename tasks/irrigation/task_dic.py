#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from basic.scheduler import CustomScheduler
from tasks.irrigation.zktj_nc2mgo import ZktjNcMgo
from tasks.irrigation.caiyun_nc2mgo import CaiyunNcMgo

def get_task_dic():
    task_dict = {
        "zktj_sync_mgo": lambda: CustomScheduler(ZktjNcMgo).run(),
        "caiyun_sync_mgo": lambda: CustomScheduler(CaiyunNcMgo).run(),
    }
    return task_dict
