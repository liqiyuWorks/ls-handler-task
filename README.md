[toc]

## 1. 查看任务
```shell
python main.py list
```

## 2. 环境变量
```shell
#!/usr/bin/env bash
export MONGO_HOST=xxx
export MONGO_PORT=xxx
export MONGO_DB=xxx
export MONGO_PASSWORD=xxx
export MONGO_USER=xxx
export SCHEDULER_MODE=cron
export CRON_HOUR=1
export SCHEDULER_FLAG=1
export INTERVAL_START_TIME="2022-05-05 10:50:00"
export RUN_ONCE=1
```

## 3. 运行任务（两种方法）
### 环境变量(支持多任务)
```shell
export TASK_TYPE=任务A # 单任务
export TASK_TYPE=任务A,任务B # 多任务
```

### 命令行参数(支持多任务)
```shell
python main.py [任务A]  # 单任务
python main.py [任务A,任务B]  # 多任务
```

