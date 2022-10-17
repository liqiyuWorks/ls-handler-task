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
from pkg.public.scheduler import CustomScheduler

LOG_FILE = "./log/run.log"
QUEUE_PREFIX = os.getenv('QUEUE_PREFIX', "handler")
RUN_ONCE= int(os.getenv('RUN_ONCE', 0))

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
 
def rds_distributed_sys(task_dict,task_type):
    # print(f"任务列表: {task_dict}")
    rds = RdsQueue()
    try:
        while True:
            try:
                # 从队列获取任务'
                task_rds_key = f"{QUEUE_PREFIX}_{task_type}"
                # print(f"> {task_rds_key}")
                task = rds.pop(task_rds_key)
                if task is None:
                    time.sleep(1)
                    continue
                logging.info(task)
            except Exception as e:
                logging.error(e)
                logging.error(traceback.format_exc())
                break

            run_task_type = task.get('task_type')
            if task_dict.get(run_task_type):
                print(f">> start rds function {run_task_type} <<")
                task_dict[run_task_type]().run()
                print(f">> end rds function {run_task_type} <<")
            else:
                logging.info('还未实现相关功能！')
    except Exception as e:
        print("出现错误：",str(e))
    finally:
        rds.close()
        print("close rds ok!")

def main():
    TASK_DICT = get_task_dic()
    opts, args = getopt.getopt(sys.argv, "h", ["help"])  # python main.py list
    if len(args) < 2:
        task_type = os.getenv('TASK_TYPE')
    else:
        task_type = args[1]

    if task_type == "list" or task_type is None:
        sys.exit(-1)

    if "," in task_type:
        task_type_list = task_type.split(",")
        handlers = {}
        for task_type in task_type_list:
            handlers[task_type] = CustomScheduler(TASK_DICT[task_type]).run
        multi_handler = MultiThread(handlers)
        multi_handler.run()
        # 加入 分布式 redis读取任务的 线程
        for task_type in task_type_list:
            multi_handler.run_arg_handler(rds_distributed_sys, TASK_DICT, task_type)
        multi_handler.close()
    else:
        if TASK_DICT.get(task_type):
            multi_handler = MultiThread()
            if RUN_ONCE:
                TASK_DICT[task_type]().run()
            else:
                # 加入 分布式 redis读取任务的 线程
                multi_handler.run_handler(CustomScheduler(TASK_DICT[task_type]).run)  # 加入 定时器

            multi_handler.run_arg_handler(rds_distributed_sys, TASK_DICT,task_type)
            multi_handler.close()
        else:
            logging.info('还未实现相关功能！')
    

if __name__ == '__main__':
    init_log()
    main()
    

    