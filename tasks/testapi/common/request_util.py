'''
Author: lisheng
Date: 2022-11-01 21:34:01
LastEditTime: 2023-01-04 09:54:23
LastEditors: lisheng
Description: 
FilePath: /ls-handler-task/tasks/testapi/common/request_util.py
'''
import subprocess
import logging
import logging.handlers
import json
import requests
from common.logger_util import logger



class WrkBenchmarkUtil:
    def __init__(self, method="GET", threads=8, call_nums=1000, req_url="",body={}):
        self._req_url = req_url
        self._method = method
        self._threads = threads
        self._call_nums = call_nums
        self._body = json.dumps(body)

    def exe_cmd(self, cmd):
        logger.info(f"cmd={cmd}")
        res = subprocess.getoutput(cmd)
        logger.info(f"BENCHMARK Result:\n{res}\n\n")

    def get(self, url):
        cmd = f'go-wrk -t={self._threads} -n={self._call_nums} -m="GET" "{url}"'
        self.exe_cmd(cmd)

    def post(self, url):
        cmd = f'go-wrk -t={self._threads} -n={self._call_nums} -m="POST" -b="{self._body}"  "{url}"'
        self.exe_cmd(cmd)
        
    def run(self):
        if self._method == "GET":
            self.get(self._req_url)
        elif self._method == "POST":
            self.post(self._req_url)
            
            
def request_handler(method, url, data={}, headers={}):
    """
    :param headers: 请求头
    :param method: 方法字符串，'GET'，'POST'
    :param url: 请求地址
    :param data: 要传递的参数
    :return: 返回响应的数据
    """
    try:
        if not headers:
            headers = {}
        method = method.upper()
        if method == "GET" or method == "DELETE":
            return requests.request(method=method, url=url, params=data, timeout=5).json()
        elif method == "POST" or method == "PUT":
                return requests.request(method=method, url=url, headers=headers, json=data, timeout=5).json()
        else:
            logging.debug(f"=====大兄弟===暂不支持{method}呢====你快点补充吧====")
            return None
    except Exception as e:
        raise e