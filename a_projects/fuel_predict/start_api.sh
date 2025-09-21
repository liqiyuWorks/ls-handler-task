#!/bin/bash
# 船舶油耗预测API启动脚本 - 简化版

echo "🚀 启动船舶油耗预测FastAPI服务器 (V3.0简化版)..."
echo "📅 启动时间: $(date)"
echo "📁 工作目录: $(pwd)"
echo ""

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "❌ Python未安装或不在PATH中"
    exit 1
fi

# 检查依赖包
echo "🔍 检查依赖包..."
python -c "import fastapi, uvicorn, pydantic, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️ 缺少依赖包，正在安装..."
    pip install -r requirements.txt
fi

# 检查核心模块
if [ ! -f "api/enhanced_fuel_api_v3.py" ]; then
    echo "❌ 核心模块文件不存在: api/enhanced_fuel_api_v3.py"
    exit 1
fi

# 检查模型文件
if [ ! -f "models/enhanced_fuel_model_v3_"*.pkl ]; then
    echo "⚠️ 模型文件不存在，将使用规则预测模式"
fi

echo "✅ 环境检查完成"
echo ""
echo "🚀 服务即将启动..."
echo "============================================"
echo "🌐 服务地址: http://localhost:8080"
echo "📖 Swagger文档: http://localhost:8080/docs"
echo "📋 ReDoc文档: http://localhost:8080/redoc"
echo "🏠 欢迎页面: http://localhost:8080"
echo "❤️ 健康检查: http://localhost:8080/health"
echo "============================================"
echo ""
echo "💡 使用提示:"
echo "   • 推荐使用Swagger UI (http://localhost:8080/docs) 进行API测试"
echo "   • 基础预测: GET /predict?ship_type=Bulk Carrier&speed=12.0"
echo "   • 增强预测: POST /predict (JSON数据)"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "============================================"

# 启动服务器
cd api && python fastapi_server.py
