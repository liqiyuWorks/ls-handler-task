#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
import redis
from pkg.db.mongo import get_mgo, MgoStore
from pkg.db.redis import RdsTaskQueue


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
        if hasattr(self, 'mgo_client'):
            if self.mgo_client:
                self.mgo_client.close()
            logging.info('close mgo databases ok!')

        if hasattr(self, 'rds'):
            self.rds.close()
            logging.info('close rds databases ok!')

    def history(self):
        pass

    def run(self):
        pass
