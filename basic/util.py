#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import datetime

def load_dic(task_dic, dest_dic):
    for key, value in dest_dic.items():
        if key in task_dic:
            logging.error('duplicate tasc_dic key {}'.format(key))
        else:
            task_dic[key] = value

def format_time(india_time_str, india_format='%Y-%m-%d %H:%M:%S'):
    india_dt = datetime.datetime.strptime(india_time_str, india_format)
    local_dt = india_dt + datetime.timedelta(hours=8)
    local_format = "%Y-%m-%d %H:%M:%S"
    time_str = local_dt.strftime(local_format)
    return time_str