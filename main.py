#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import time
import logging
import logging.handlers
import traceback
from basic.database import RdsQueue
from basic.thread import MultiThread
from tasks.task_dic import get_task_dic

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
        TASK_DICT = get_task_dic()
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
        TASK_DICT = get_task_dic()
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
    

    