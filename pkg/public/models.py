#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import redis
from pkg.db.mongo import get_mgo, MgoStore
from pkg.db.redis import RdsTaskQueue
from pkg.db.clickhouse import ClickHouseClient


class BaseModel:
    def __init__(self, config=None):
        if config:
            if config.get('handle_db', 'mgo') == 'mgo':
                self.config = config
                if config.get("collection"):
                    self.mgo = self.get_mgo_store()
                else:
                    # 自由mongo模式...
                    self.mgo_client, self.mgo_db = get_mgo()
            if config.get('rds'):
                self.rds = self.get_task_rds()

            if config.get('cache_rds'):
                self.cache_rds = self.get_cache_rds()

            if config.get('ck_client'):
                self.ck_client = ClickHouseClient()

    def get_cache_rds(self):
        host = os.getenv('CACHE_REDIS_HOST', '127.0.0.1')
        port = int(os.getenv('CACHE_REDIS_PORT', '6379'))
        password = os.getenv('CACHE_REDIS_PASSWORD', None)
        return redis.Redis(host=host, port=port, db=0, password=password, decode_responses=True, health_check_interval=30)

    def get_task_rds(self):
        host = os.getenv('REDIS_TASK_HOST', '127.0.0.1')
        port = int(os.getenv('REDIS_TASK_PORT', '6379'))
        password = os.getenv('REDIS_TASK_PASSWORD', None)
        return RdsTaskQueue(redis.Redis(host=host, port=port, db=0, password=password, decode_responses=True, health_check_interval=30))

    def get_mgo_store(self):
        self.mgo_client, self.mgo_db = get_mgo()
        self.config['mgo_client'] = self.mgo_client
        self.config['mgo_db'] = self.mgo_db
        return MgoStore(self.config)  # 初始化

    def close(self):
        """关闭所有数据库连接（支持重复调用）"""
        closed_connections = []
        
        # 关闭 MongoDB 连接
        if hasattr(self, 'mgo_client') and self.mgo_client:
            try:
                self.mgo_client.close()
                closed_connections.append('MongoDB')
            except Exception as e:
                logging.debug(f'关闭MongoDB连接失败: {e}')

        # 关闭 Redis Task Queue
        if hasattr(self, 'rds') and self.rds:
            try:
                self.rds.close()
                closed_connections.append('Redis Queue')
            except Exception as e:
                logging.debug(f'关闭Redis Queue连接失败: {e}')

        # 关闭 Redis Cache
        if hasattr(self, 'cache_rds') and self.cache_rds:
            try:
                self.cache_rds.close()
                closed_connections.append('Redis Cache')
            except Exception as e:
                logging.debug(f'关闭Redis Cache连接失败: {e}')
                
        # 关闭 ClickHouse 连接
        if hasattr(self, 'ck_client') and self.ck_client:
            try:
                self.ck_client.close()
                closed_connections.append('ClickHouse')
            except Exception as e:
                logging.debug(f'关闭ClickHouse连接失败: {e}')

        
        # 如果有关闭的连接，显示信息
        if closed_connections:
            logging.info(f'关闭数据库连接: {", ".join(closed_connections)}')

    def history(self):
        pass

    def run(self):
        pass
