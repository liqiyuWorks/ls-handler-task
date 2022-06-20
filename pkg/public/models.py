#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import os
from tkinter.messagebox import NO
import redis
from pkg.db.mongo import get_mgo, MgoStore
from pkg.db.redis import RdsTaskQueue


class BaseModel:
    def __init__(self, config=None):
        if config:
            if config.get('handle_db','mgo') == 'mgo':
                self.config = config
                self.mgo = self.get_mgo()
            if config.get('rds'):
                self.rds = self.get_task_rds()

    def get_task_rds(self):
        host = os.getenv('REDIS_TASK_HOST', '127.0.0.1')
        port = int(os.getenv('REDIS_TASK_PORT', '6379'))
        password = os.getenv('REDIS_TASK_PASSWORD', None)
        return RdsTaskQueue(redis.Redis(host=host, port=port, db=0, password=password, decode_responses=True))
                
            
    def get_mgo(self):
        mgo_client, mgo_db = get_mgo()
        self.config['mgo_client'] = mgo_client
        self.config['mgo_db'] = mgo_db
        return MgoStore(self.config)  # 初始化

    def close(self):
        if hasattr(self,'mgo'):
            self.mgo.close()
            logging.info('close mgo databases ok!')

        if hasattr(self,'rds'):
            self.rds.close()
            logging.info('close rds databases ok!')

    def history(self):
        pass
         
    def run(self):
        pass
