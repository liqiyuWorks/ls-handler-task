#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.scheduler import CustomScheduler
from tasks.irrigation.subtasks.zktj_nc2mgo import ZktjNcMgo
from tasks.irrigation.subtasks.caiyun_nc2mgo import CaiyunNcMgo

def get_task_dic():
    task_dict = {
        "zktj_sync_mgo": (lambda: CustomScheduler(ZktjNcMgo).run(),'数据同步=> zktj的数据到mongo'),
        "caiyun_sync_mgo": (lambda: CustomScheduler(CaiyunNcMgo).run(),'数据同步=> 彩云数据到mongo'),
    }
    return task_dict
