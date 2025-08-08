#!/bin/bash

# Docker 构建脚本 - Playwright 优化版本

set -e

echo "=== 构建车辆报告修改系统 Docker 镜像 ==="

# 设置变量
IMAGE_NAME="car-report-modifier"
TAG=$(date +"%Y%m%d%H%M%S")
FULL_IMAGE_NAME="${IMAGE_NAME}:${TAG}"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "错误: Docker 未运行"
    exit 1
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p static/screenshots
mkdir -p templates
mkdir -p logs

# 设置权限
chmod -R 755 static/screenshots
chmod -R 755 templates

# 构建镜像
echo "构建 Docker 镜像: ${FULL_IMAGE_NAME}"
docker build -t "${FULL_IMAGE_NAME}" .

# 检查构建是否成功
if [ $? -eq 0 ]; then
    echo "✅ Docker 镜像构建成功: ${FULL_IMAGE_NAME}"
    
    # 显示镜像信息
    echo "镜像信息:"
    docker images | grep "${IMAGE_NAME}"
    
    # 创建最新标签
    docker tag "${FULL_IMAGE_NAME}" "${IMAGE_NAME}:latest"
    echo "✅ 已创建 latest 标签"
    
    # 显示使用说明
    echo ""
    echo "=== 使用说明 ==="
    echo "1. 运行容器:"
    echo "   docker run -d -p 8090:8090 --name car-report-modifier ${FULL_IMAGE_NAME}"
    echo ""
    echo "2. 使用 Docker Compose 运行:"
    echo "   docker-compose up -d"
    echo ""
    echo "3. 查看日志:"
    echo "   docker logs car-report-modifier"
    echo ""
    echo "4. 停止容器:"
    echo "   docker stop car-report-modifier"
    echo ""
    echo "5. 删除容器:"
    echo "   docker rm car-report-modifier"
    echo ""
    echo "访问地址: http://localhost:8090"
    
else
    echo "❌ Docker 镜像构建失败"
    exit 1
fi 