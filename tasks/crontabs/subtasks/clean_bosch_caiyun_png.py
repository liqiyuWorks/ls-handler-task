#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from cmath import log
import logging
import os
import datetime
import subprocess


class CleanBoschCaiyunPng:
    def run(self):
        DAY = int(os.getenv('DAY', 60))
        INPUT_PATH = os.getenv(
            'INPUT_PATH',  "/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/input/test/")
        last_mon = (datetime.datetime.now() +
                    datetime.timedelta(days=-DAY)).strftime("%Y%m%d")
        logging.info(f"目前查看的日期是：{last_mon}")
        res = subprocess.getoutput(f"ls {INPUT_PATH} -a |grep ^{last_mon}")
        # res = subprocess.getoutput(f"ls {INPUT_PATH} |grep ^20220702")
        res_list = res.split('\n')

        for res in res_list:
            if res:
                dir_path = INPUT_PATH + res
                logging.info(dir_path)
                subprocess.call(['rm', '-rf'] + [dir_path])
