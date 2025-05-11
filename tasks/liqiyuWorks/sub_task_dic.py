#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.liqiyuWorks.subtasks.push_gold_price2wechat import JDGoldPushWechat
from tasks.liqiyuWorks.subtasks.spider_weibo import WeiboSpider


def get_task_dic():
    task_dict = {
        "push_gold_price2wechat": (lambda: JDGoldPushWechat(), '个人业务=> 推送黄金实时价格到微信'),
        "weibo_spider": (lambda: WeiboSpider(), '个人业务=> 微博爬虫'),
    }
    return task_dict
