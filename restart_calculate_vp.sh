#!/bin/bash

# 定义Python程序命令和日志文件路径
PYTHON_CMD="python3 -u main.py calculate_vessel_performance"
LOG_FILE="handler_calculate_vessel_performance.log"

# 函数：终止正在运行的Python进程
stop_process() {
    echo "正在停止现有进程..."
    pkill -f "$PYTHON_CMD"
    sleep 2  # 等待进程完全终止
}

# 函数：启动Python程序并重定向日志
start_process() {
    echo "正在启动新进程..."
    nohup $PYTHON_CMD > $LOG_FILE 2>&1 &
    echo "日志输出到: $LOG_FILE"
    echo "使用以下命令查看实时日志:"
    echo "tail -f $LOG_FILE"
}

# 函数：重启进程
restart_process() {
    stop_process
    start_process
}

# 主逻辑
case "$1" in
    start)
        start_process
        ;;
    stop)
        stop_process
        ;;
    restart)
        restart_process
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart}"
        exit 1
        ;;
esac

exit 0