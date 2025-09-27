#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FFA模拟交易系统生产环境配置
"""

import os
from pathlib import Path

# 基础配置
BASE_DIR = Path(__file__).parent
DEBUG = False
HOST = "0.0.0.0"
PORT = 8000

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/data/ffa_simulation.db")

# 安全配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "logs" / "app.log"

# 静态文件配置
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# 数据目录
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# 创建必要的目录
for directory in [STATIC_DIR, TEMPLATES_DIR, DATA_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# 应用配置
APP_NAME = "FFA模拟交易系统"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "FFA (Forward Freight Agreement) 模拟交易系统"

# 交易配置
DEFAULT_ACCOUNT_ID = 1
DEFAULT_INITIAL_EQUITY = 1000000.0

# 风险控制配置
MAX_POSITION_SIZE = 1000  # 最大持仓手数
MAX_DAILY_TRADES = 100    # 每日最大交易次数
RISK_WARNING_THRESHOLD = 0.1  # 风险警告阈值（10%）

# 性能配置
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
KEEPALIVE_TIMEOUT = int(os.getenv("KEEPALIVE_TIMEOUT", "5"))
