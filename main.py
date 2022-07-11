#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import getopt
import time
import logging
import logging.handlers
import traceback
from pkg.db.redis import RdsQueue
from pkg.public.thread import MultiThread
from tasks.task_dic import get_task_dic

LOG_FILE = "./log/run.log"
SCHEDULER_FLAG = int(os.getenv('SCHEDULER_FLAG', 1))
QUEUE_KEY = os.getenv('QUEUE_KEY', "ls_handler")

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
    TASK_DICT = get_task_dic()
    opts, args = getopt.getopt(sys.argv, "h", ["help"])  # python main.py list
    if len(args) < 2:
        task_type = os.getenv('TASK_TYPE')
    else:
        task_type = args[1]

    if task_type == "list" or task_type is None:
        sys.exit(-1)

    if SCHEDULER_FLAG:
        if "," in task_type:
            task_type_list = task_type.split(",")
            handlers = {}
            for task_type in task_type_list:
                handlers[task_type] = TASK_DICT.get(task_type)
            print(handlers)
            multi_handler = MultiThread(handlers)
            multi_handler.run()
            multi_handler.close()
        else:
            if TASK_DICT.get(task_type):
                TASK_DICT[task_type]()
            else:
                logging.info('还未实现相关功能！')

    else:
        rds = RdsQueue()
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
    

    