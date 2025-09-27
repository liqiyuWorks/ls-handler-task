#!/bin/bash

# FFA模拟交易系统启动脚本

set -e

echo "🚀 启动FFA模拟交易系统..."

# 检查Python版本
python3 --version

# 创建必要的目录
mkdir -p data logs static templates

# 设置环境变量
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# 初始化数据库
echo "📊 初始化数据库..."
python3 -c "
from database import create_tables
create_tables()
print('数据库初始化完成')
"

# 启动应用
echo "🌟 启动FastAPI应用..."
exec python3 main.py
