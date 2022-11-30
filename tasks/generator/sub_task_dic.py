#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from tasks.generator.subtasks.gen_gfs_daily import GenGfsDaily
from pkg.public.scheduler import CustomScheduler

def get_task_dic():
    task_dict = {
        # "gen_gfs_daily": (GenGfsDaily,'定时生成GFS的处理文件发送到nc2redis'),
    }
    return task_dict
