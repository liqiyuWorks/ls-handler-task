#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import datetime

def format_time(india_time_str, india_format='%Y-%m-%d %H:%M:%S'):
    india_dt = datetime.datetime.strptime(india_time_str, india_format)
    local_dt = india_dt + datetime.timedelta(hours=8)
    local_format = "%Y-%m-%d %H:%M:%S"
    time_str = local_dt.strftime(local_format)
    return time_str

def time_CST2UTC(india_time_str, india_format='%Y-%m-%d %H:%M:%S'):
    india_dt = datetime.datetime.strptime(india_time_str, india_format)
    local_dt = india_dt + datetime.timedelta(hours=-8)
    local_format = "%Y-%m-%d %H:%M:%S"
    time_str = local_dt.strftime(local_format)
    return time_str


def time2time(ts, fmt, new_fmt, hours=0):
    ts_time = datetime.datetime.strptime(ts, fmt)
    new_time = ts_time + datetime.timedelta(hours=hours)
    return new_time.strftime(new_fmt)


def time2UTCstamp(date, format_string="%Y%m%d%H"):
    date = datetime.strptime(date, format_string) + datetime.timedelta(hours=8)
    date = int(time.mktime(date.timetuple()) * 1000.0 + date.microsecond / 1000.0)
    return date


def check_create_path(file):
    file_path = os.path.dirname(file)
    if not os.path.exists(file_path):
        os.makedirs(file_path, 0o775)