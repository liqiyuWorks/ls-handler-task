#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tasks.aquabridge.subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo
from tasks.aquabridge.subtasks.handle_wechat_fis_content import HandleWechatFisContent
from tasks.aquabridge.subtasks.spider_fis_trade_data import SpiderFisTradeData, SpiderAllFisTradeData, SpiderFisMarketTrades, SpiderFisDailyTradeData, SpiderAllFisDailyTradeData

def get_task_dic():
    task_dict = {
        "spider_jinzheng_pages2mgo": (lambda: SpiderJinzhengPages2mgo(), '从金正爬页面到mgo'),
        # "handle_wechat_fis_content": (lambda: HandleWechatFisContent(), '处理微信消息=> FIS: C5TC、P4TC、C5'),
        
        # FIS交易数据爬取任务 - 分表存储
        # "spider_fis_c5tc_data": (lambda: SpiderFisTradeData("C5TC"), '爬取C5TC交易数据到独立表'),
        # "spider_fis_p4tc_data": (lambda: SpiderFisTradeData("P4TC"), '爬取P4TC交易数据到独立表'),
        # "spider_fis_p5tc_data": (lambda: SpiderFisTradeData("P5TC"), '爬取P5TC交易数据到独立表'),
        
        # 兼容性任务（获取所有产品类型）
        "spider_fis_trade_data": (lambda: SpiderAllFisTradeData(), '爬取所有FIS交易数据（C5TC、P4TC、P5TC）'),
        
        # FIS市场交易数据爬取任务
        "spider_fis_market_trades": (lambda: SpiderFisMarketTrades(), '爬取FIS市场交易数据（已执行交易）'),
        
        
        # 获取fis的逐日交易数据（用于画图）
        "spider_fis_daily_trade_data": (lambda: SpiderAllFisDailyTradeData(), '爬取FIS逐日交易数据（C5TC、P4TC、P5TC）'),
        
        # 单个产品类型的逐日交易数据爬取任务
        # "spider_fis_daily_c5tc": (lambda: SpiderFisDailyTradeData("C5TC"), '爬取FIS C5TC逐日交易数据'),
        # "spider_fis_daily_p4tc": (lambda: SpiderFisDailyTradeData("P4TC"), '爬取FIS P4TC逐日交易数据'),
        # "spider_fis_daily_p5tc": (lambda: SpiderFisDailyTradeData("P5TC"), '爬取FIS P5TC逐日交易数据'),
    }
    return task_dict
