#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.aquabridge.subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo
from tasks.aquabridge.subtasks.handle_wechat_fis_content import HandleWechatFisContent


def get_task_dic():
    task_dict = {
        "spider_jinzheng_pages2mgo": (lambda: SpiderJinzhengPages2mgo(), '从金正爬页面到mgo'),
        "handle_wechat_fis_content": (lambda: HandleWechatFisContent(), '处理微信消息=> FIS: C5TC、P4TC、C5'),
    }
    return task_dict
