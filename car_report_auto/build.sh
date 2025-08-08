#!/bin/bash

# 汽车报告修改器 Docker 构建脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
}

# 检查Docker是否运行
check_docker_running() {
    if ! docker info &> /dev/null; then
        print_error "Docker 未运行，请启动 Docker"
        exit 1
    fi
}

# 清理旧的镜像和容器
cleanup() {
    print_message "清理旧的镜像和容器..."
    docker system prune -f
    docker image prune -f
}

# 构建镜像
build_image() {
    local dockerfile=${1:-"Dockerfile"}
    local tag=${2:-"car-report-modifier:latest"}
    
    print_message "使用 $dockerfile 构建镜像..."
    docker build -f "$dockerfile" -t "$tag" .
    
    if [ $? -eq 0 ]; then
        print_message "镜像构建成功: $tag"
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

# 运行容器
run_container() {
    local image=${1:-"car-report-modifier:latest"}
    local port=${2:-"8090"}
    
    print_message "启动容器..."
    docker run -d \
        --name car-report-modifier \
        -p "$port:8090" \
        -e TZ=Asia/Shanghai \
        -e RELEASE_MODE=1 \
        -v "$(pwd)/static:/app/static" \
        -v "$(pwd)/templates:/app/templates" \
        -v "$(pwd)/screenshots:/app/screenshots" \
        --restart unless-stopped \
        "$image"
    
    if [ $? -eq 0 ]; then
        print_message "容器启动成功，访问地址: http://localhost:$port"
    else
        print_error "容器启动失败"
        exit 1
    fi
}

# 停止并删除容器
stop_container() {
    print_message "停止并删除容器..."
    docker stop car-report-modifier 2>/dev/null || true
    docker rm car-report-modifier 2>/dev/null || true
}

# 显示使用帮助
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  build [dockerfile] [tag]    构建镜像 (默认: Dockerfile, car-report-modifier:latest)"
    echo "  run [image] [port]          运行容器 (默认: car-report-modifier:latest, 5000)"
    echo "  stop                         停止并删除容器"
    echo "  cleanup                      清理Docker缓存"
    echo "  all                          执行完整流程: cleanup -> build -> run"
    echo "  help                         显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 build Dockerfile.optimized my-app:v1.0"
    echo "  $0 run my-app:v1.0 8080"
    echo "  $0 all"
}

# 主函数
main() {
    check_docker
    check_docker_running
    
    case "${1:-help}" in
        "build")
            build_image "$2" "$3"
            ;;
        "run")
            run_container "$2" "$3"
            ;;
        "stop")
            stop_container
            ;;
        "cleanup")
            cleanup
            ;;
        "all")
            cleanup
            build_image
            run_container
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@" 