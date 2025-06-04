#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import logging
import importlib.util


### 环境遍历过滤任务和目录
EXCLUDE_DIRECTORY = os.getenv('EXCLUDE_DIRECTORY', "")
SELECTED_DIRECTORY = os.getenv('SELECTED_DIRECTORY', "")
EXCLUDE_DIRECTORY_LIST = list(map(str.strip, EXCLUDE_DIRECTORY.split(',')))
SELECTED_DIRECTORY_LIST = list(map(str.strip, SELECTED_DIRECTORY.split(',')))


def get_current_dirs(path):
    dirs = []
    for dir in os.listdir(path):
        dir = os.path.join(path, dir)
        # 判断当前目录是否为文件夹
        if os.path.isdir(dir) and "__pycache__" not in dir:
            dirs.append(dir)
    return dirs


def get_task_dic():
    print("任务列表".center(100, '='))
    task_dic = {}
    base_path = os.path.dirname(os.path.abspath(__file__))
    dirs_list = get_current_dirs(base_path)
    for index, dir in enumerate(dirs_list):
        # Skip directories in EXCLUDE_DIRECTORY_LIST
        if EXCLUDE_DIRECTORY:
            if any(exclude_dir in dir for exclude_dir in EXCLUDE_DIRECTORY_LIST):
                continue
        if SELECTED_DIRECTORY_LIST and not any(selected_dir in dir for selected_dir in SELECTED_DIRECTORY_LIST):
            continue
        print(index, dir)
        sub_task_path = os.path.join(dir, 'sub_task_dic.py')
        spec_function = importlib.util.spec_from_file_location(
            'get_task_dic', sub_task_path)
        module_function = importlib.util.module_from_spec(spec_function)
        spec_function.loader.exec_module(module_function)
        print(f'[{index+1}] {dir}')
        for key, value in module_function.get_task_dic().items():
            if key in task_dic:
                logging.error('duplicate tasc_dic key {}'.format(key))
            else:
                print(
                    ' ** TASK_TYPE={:38s} \t\t| Desc: "{}"'.format(key, value[1]))
                task_dic[key] = value[0]

    # print(' ===任务列表=== \n')
    print("任务列表".center(100, '=')+"\n")
    return task_dic
