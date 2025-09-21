'''
Author: lisheng
Date: 2023-09-03 21:06:16
LastEditTime: 2023-09-04 11:04:25
LastEditors: lisheng
Description: 提供文件操作相关的函数
FilePath: /ls-handler-task/pkg/util/file.py
'''
import os


def check_create_path(file):
    '''
    description: 检查是否存在该文件
    return {*}
    author: liqiyuWorks
    '''
    file_path = os.path.dirname(file)
    if not os.path.exists(file_path):
        os.makedirs(file_path, 0o777)


def traverse_folder(folder_path):
    '''
    description: 遍历文件夹中的所有文件
    return {*}
    author: liqiyuWorks
    '''
    full_path_list = []
    for item in os.listdir(folder_path):
        # 获取每个文件或文件夹的全路径
        full_path = os.path.join(folder_path, item)
        if os.path.isdir(full_path):  # 如果是文件夹，则递归调用自己
            traverse_folder(full_path)
        else:  # 如果是文件，则处理该文件
            full_path_list.append(full_path)

    return full_path_list
