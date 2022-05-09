#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests

def parse_url(url):
    '''发起请求'''
    try:
        print('当前请求的url={}'.format(url))
        res = requests.get(url)
        return res
    except Exception as e:
        print('出现问题={}'.format(e))