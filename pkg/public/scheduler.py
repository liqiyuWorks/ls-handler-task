#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from apscheduler.schedulers.blocking import BlockingScheduler
import os
from datetime import datetime

class CustomScheduler:
    def __init__(self, obj, **kwargs):
        self.obj = obj(**kwargs)
        self.sched = BlockingScheduler()

    def get_scheduler_param(self, scheduler_mode):
        param_dic = {'cron': {
        'year': os.getenv('CRON_YEAR'),
        'month': os.getenv('CRON_MONTH'),
        'day_of_week': os.getenv('CRON_WEEK'),
        'day': os.getenv('CRON_DAY'),
        'hour': os.getenv('CRON_HOUR'),
        'minute': os.getenv('CRON_MINUTE'),
    }, 'interval': {
        'weeks': os.getenv('INTERVAL_WEEK'),
        'days': os.getenv('INTERVAL_DAY'),
        'hours': os.getenv('INTERVAL_HOUR'),
        'minutes': os.getenv('INTERVAL_MINUTE'),
        'seconds': os.getenv('INTERVAL_SECOND'),
        'start_date': self._validate_start_date(os.getenv('INTERVAL_START_TIME')),
    }}

        return param_dic[scheduler_mode]
    
    def _validate_start_date(self, start_date_str):
        """验证并格式化start_date字符串"""
        if not start_date_str:
            return None
        
        try:
            # 尝试解析日期字符串
            if 'T' in start_date_str:
                # ISO格式: 2025-10-15T00:00:00
                return datetime.fromisoformat(start_date_str)
            elif ' ' in start_date_str:
                # 空格格式: 2025-10-15 00:00:00
                return datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S')
            else:
                # 其他格式直接尝试解析
                return datetime.fromisoformat(start_date_str)
        except ValueError as e:
            print(f"警告: 无效的日期格式 '{start_date_str}': {e}")
            print("使用当前时间作为start_date")
            return datetime.now()

    def add_job(self):
        scheduler_mode = os.getenv('SCHEDULER_MODE', 'cron')
        dic = self.get_scheduler_param(scheduler_mode)
        for key in list(dic.keys()):
            if not dic.get(key):
                del dic[key]
            elif key == 'start_date':
                pass
            else:
                dic[key] = int(dic[key])
        self.sched.add_job(self.obj.run, scheduler_mode, **dic)

    def run(self):
        self.add_job()
        self.sched.start()



