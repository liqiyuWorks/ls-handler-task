#!/bin/bash
# 启动名片智能体服务

cd "$(dirname "$0")"

echo "🚀 正在启动名片智能体服务..."
echo ""

# 检查 Flask 是否安装
if ! python3 -c "import flask" 2>/dev/null; then
    echo "⚠️  Flask 未安装，正在安装..."
    pip3 install flask
fi

# 启动服务
python3 app.py

