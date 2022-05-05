#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import redis
import json
import logging
import logging.handlers
import traceback
from basic.database import RdsQueue
from basic.scheduler import CustomScheduler
from basic.thread import MultiThread
from task.test_task import test_func_a, test_func_b, test_func_c
from task.noaa_sync_mgo import noaa_sync_mgo

LOG_FILE = "./log/run.log"
SCHEDULER_FLAG = int(os.getenv('SCHEDULER_FLAG', 1))
QUEUE_KEY = os.getenv('QUEUE_KEY', "test")
TASK_TYPE = os.getenv('TASK_TYPE', "test")

def init_log():
    logger = logging.getLogger()
    formatter = logging.Formatter('%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')
    sh = logging.StreamHandler()  # 往屏幕上输出
    sh.setFormatter(formatter)  # 设置屏幕上显示的格式
    th = logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='H', interval=1, backupCount=40)
    th.setFormatter(formatter)
    logger.addHandler(sh)
    logger.addHandler(th)
    logger.setLevel(logging.INFO)
 

def main():
    rds = RdsQueue()
    if SCHEDULER_FLAG:
        TASK_DICT = {
        # "test_func_a": lambda: CustomScheduler(test_func_a).run(),
        # "test_func_b": lambda: CustomScheduler(test_func_b).run(),
        # "test_func_c": lambda: CustomScheduler(test_func_c).run(),
        "noaa_sync_mgo": lambda: CustomScheduler(noaa_sync_mgo).run(),
        }
        if "," in TASK_TYPE:
            task_type_list = TASK_TYPE.split(",")
            handlers = {}
            for task_type in task_type_list:
                handlers[task_type] = TASK_DICT.get(task_type)
            print(handlers)
            multi_handler = MultiThread(handlers)
            multi_handler.run()
            multi_handler.close()
        else:
            if TASK_DICT.get(TASK_TYPE):
                TASK_DICT[TASK_TYPE]()
            else:
                logging.info('还未实现相关功能！')

    else:
        TASK_DICT = {
            "test": lambda: test_func()
        }
        while True:
            try:
                # 从队列获取任务
                task = rds.pop(QUEUE_KEY)
                if task is None:
                    time.sleep(1)
                    continue
                logging.info(task)
            except Exception as e:
                logging.error(e)
                logging.error(traceback.format_exc())
                break

            task_type = task.get('task_type')
            if TASK_DICT.get(task_type):
                TASK_DICT[task_type]()
            else:
                logging.info('还未实现相关功能！')

    

if __name__ == '__main__':
    init_log()
    main()
    

    