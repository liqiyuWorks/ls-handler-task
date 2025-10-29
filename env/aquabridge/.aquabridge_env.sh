#!/usr/bin/env bash
# Aquabridge环境配置

# MongoDB配置
export MONGO_HOST=153.35.96.86
export MONGO_PORT=27017
export MONGO_DB=aquabridge
export MONGO_PASSWORD=Aquabridge#2025
export MONGO_USER=aquabridge

# Redis缓存配置
export CACHE_REDIS_HOST=153.35.96.86
export CACHE_REDIS_PORT=6379
export CACHE_REDIS_PASSWORD=5S4Zt7wCCktYJnpAQPHZ

# Redis任务队列配置
export REDIS_HOST=153.35.96.86
export REDIS_PORT=6379
export REDIS_PASSWORD=5S4Zt7wCCktYJnpAQPHZ

# 任务配置
export SELECTED_DIRECTORY=aquabridge
export RUN_ONCE=1
export IS_OPEN_RDS=0
