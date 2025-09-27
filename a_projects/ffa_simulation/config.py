#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统配置文件
"""

# 交易配置
TRADING_CONFIG = {
    "initial_equity": 1000000,  # 初始权益
    "commission_rate": 0.001,   # 佣金比例 0.1%
    "clearing_fee": 20,         # 清算费
    "min_trade_volume": 1,      # 最小交易手数
    "max_trade_volume": 10000,  # 最大交易手数
}

# FFA合约配置
CONTRACT_CONFIG = {
    "PMX": {
        "name": "PMX",
        "description": "PMX航线",
        "multiplier": 100,  # 合约乘数
        "min_price_tick": 1,  # 最小价格变动
    },
    "C5TC": {
        "name": "C5TC",
        "description": "C5TC航线",
        "multiplier": 100,  # 合约乘数
        "min_price_tick": 1,  # 最小价格变动
    },
    "P4TC": {
        "name": "P4TC", 
        "description": "P4TC航线",
        "multiplier": 100,
        "min_price_tick": 1,
    },
    "S5TC": {
        "name": "S5TC",
        "description": "S5TC航线", 
        "multiplier": 100,
        "min_price_tick": 1,
    }
}

# 数据库配置
DATABASE_CONFIG = {
    "url": "sqlite:///./ffa_simulation.db"
}

# 交易策略配置
STRATEGY_CONFIG = {
    # 新策略类型
    "Future": {"action": "trade", "position_type": "future"},
    "Call": {"action": "trade", "position_type": "call_option"},
    "Put": {"action": "trade", "position_type": "put_option"},
    
    # 兼容性策略
    "开多": {"action": "buy", "position_type": "long"},
    "开空": {"action": "sell", "position_type": "short"},
    "平多": {"action": "sell", "position_type": "close_long"},
    "平空": {"action": "buy", "position_type": "close_short"},
}

# 月份配置
MONTH_CONFIG = {
    "1月": 1, "2月": 2, "3月": 3, "4月": 4,
    "5月": 5, "6月": 6, "7月": 7, "8月": 8,
    "9月": 9, "10月": 10, "11月": 11, "12月": 12
}
