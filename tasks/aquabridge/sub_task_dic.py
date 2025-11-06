#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.aquabridge.subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo
from tasks.aquabridge.subtasks.handle_wechat_fis_content import HandleWechatFisContent
from tasks.aquabridge.subtasks.spider_fis_trade_data import SpiderFisTradeData, SpiderAllFisTradeData, SpiderFisMarketTrades, SpiderFisDailyTradeData, SpiderAllFisDailyTradeData
from tasks.aquabridge.subtasks.get_fis_cookie import GetFisCookie
from tasks.aquabridge.subtasks.receive_data_aquabridge_email import ReceiveDataAquabridgeEmail

def get_task_dic():
    task_dict = {
        "spider_jinzheng_pages2mgo": (lambda: SpiderJinzhengPages2mgo(), '从金正爬页面到mgo'),
        # "handle_wechat_fis_content": (lambda: HandleWechatFisContent(), '处理微信消息=> FIS: C5TC、P4TC、C5'),
        
        # FIS市场交易数据爬取任务
        "spider_fis_market_trades": (lambda: SpiderFisMarketTrades(), '爬取FIS市场交易数据（已执行交易）'),
        
        # 兼容性任务（获取所有产品类型）
        "spider_fis_trade_data": (lambda: SpiderAllFisTradeData(), '爬取所有FIS交易数据（C5TC、P4TC、P5TC、C5、S10TC、HS7TC）'),
        
        # 获取fis的逐日交易数据（用于画图）
        "spider_fis_daily_trade_data": (lambda: SpiderAllFisDailyTradeData(), '爬取FIS逐日交易数据（C5TC、P4TC、P5TC、C5、S10TC、HS7TC）'),
        
        # 获取fis网站的 token
        "get_fis_cookie": (lambda: GetFisCookie(), '获取fis网站的 token'),
        
        # data.aquabridge.com 的邮件接收
        "receive_BEI_history_data_from_aquabridge_email": (lambda: ReceiveDataAquabridgeEmail(), '接收data.aquabridge.com 的邮件'),
    }
    return task_dict
