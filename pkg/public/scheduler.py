#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from apscheduler.schedulers.blocking import BlockingScheduler
import os

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
        'start_date': os.getenv('INTERVAL_START_TIME'),
    }}

        return param_dic[scheduler_mode]

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



