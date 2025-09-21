#!/bin/bash

# 智能航运监控系统启动脚本

echo "🚢 智能航运监控系统"
echo "===================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo "⚠️  正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 显示选项
echo ""
echo "请选择运行模式:"
echo "1. 交互式配置和监控"
echo "2. 使用默认配置直接监控"
echo "3. 运行测试"
echo "4. 查看使用示例"
echo ""

read -p "请输入选择 [1-4]: " choice

case $choice in
    1)
        echo "🚀 启动交互式监控..."
        python3 start_monitoring.py
        ;;
    2)
        echo "🚀 使用默认配置启动监控..."
        python3 vessel_warn.py
        ;;
    3)
        echo "🧪 运行系统测试..."
        python3 test_monitor.py
        ;;
    4)
        echo "📖 显示使用示例..."
        python3 example_usage.py
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac
