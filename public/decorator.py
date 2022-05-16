#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import traceback
from apscheduler.schedulers.blocking import BlockingScheduler
RUN_ONCE= int(os.getenv('RUN_ONCE', 0))

class BaseDecorate:
    def exception_capture(self,func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as e:
                logging.error('run error {}'.format(e))
                logging.error(traceback.format_exc())
        return wrapper

    def exception_capture_close_datebase(self,func):
        def wrapper(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            except Exception as e:
                logging.error('run error {}'.format(e))
                logging.error(traceback.format_exc())
            finally:
                self.close()
                logging.info('close databases ok!')
        return wrapper


class CustomScheduler:
    def __init__(self):
        pass

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

    @classmethod
    def add_job(cls, FUNC):
        scheduler_mode = os.getenv('SCHEDULER_MODE', 'cron')
        dic = cls.get_scheduler_param(cls,scheduler_mode)
        for key in list(dic.keys()):
            if not dic.get(key):
                del dic[key]
            elif key == 'start_date':
                pass
            else:
                dic[key] = int(dic[key])
        cls.sched = BlockingScheduler()
        cls.sched.add_job(FUNC, scheduler_mode, **dic)
        cls.sched.start()

    @classmethod
    def run(cls,func):
        def wrapper(*args, **kwargs):
            try:
                print ('func name:{},args:{}'.format(func.__name__,args))
                # func(self, *args, **kwargs)
                if RUN_ONCE:
                    func(*args, **kwargs)
                else:
                    cls.add_job(func)
                    
            except Exception as e:
                logging.error('run error {}'.format(e))
                logging.error(traceback.format_exc())
        return wrapper


decorate=BaseDecorate()
# custom_scheduler = CustomScheduler()
