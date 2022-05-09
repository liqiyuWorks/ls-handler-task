#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging


def load_dic(task_dic, dest_dic):
    for key, value in dest_dic.items():
        if key in task_dic:
            logging.error('duplicate tasc_dic key {}'.format(key))
        else:
            task_dic[key] = value