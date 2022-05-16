#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import logging
import importlib.util

# 递归遍历目录
def get_current_dirs(path):
    dirs = []
    for dir in os.listdir(path):
        dir = os.path.join(path, dir)
        # 判断当前目录是否为文件夹
        if os.path.isdir(dir) and "__pycache__" not in dir:
            dirs.append(dir)
    return dirs

def get_task_dic():
    print('\n ===任务列表start===')
    task_dic = {}
    base_path =  os.path.dirname(os.path.abspath(__file__))
    dirs_list = get_current_dirs(base_path)
    for index, dir in enumerate(dirs_list):
        sub_task_path = os.path.join(dir, 'sub_task_dic.py')
        spec_function = importlib.util.spec_from_file_location('get_task_dic', sub_task_path) 
        module_function = importlib.util.module_from_spec(spec_function) 
        spec_function.loader.exec_module(module_function) 
        print(f'[{index+1}] {dir}')
        for key, value in module_function.get_task_dic().items():
            if key in task_dic:
                logging.error('duplicate tasc_dic key {}'.format(key))
            else:
                print(' ** TASK_TYPE = {} \t\t| Desc:"{}"'.format(key, value[1]))
                task_dic[key] = value[0]
        
    print('===任务列表end===\n')
    return task_dic