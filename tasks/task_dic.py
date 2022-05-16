#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os,sys
import importlib.util
from basic.util import load_dic

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
        load_dic(task_dic, module_function.get_task_dic())
        print(f'[{index+1}] {dir}')
        for k,v in task_dic.items():
            print(f' ** TASK_TYPE = {k}')
    print('===任务列表end===\n')
    return task_dic