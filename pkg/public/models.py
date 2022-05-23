#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
from pkg.db.mongo import get_mgo, MgoStore

class BaseModel:
    def __init__(self, config=None):
        if config:
            if config.get('handle_db','mgo') == 'mgo':
                self.config = config
                self.mgo = self.get_mgo()
            
    def get_mgo(self):
        mgo_client, mgo_db = get_mgo()
        self.config['mgo_client'] = mgo_client
        self.config['mgo_db'] = mgo_db
        return MgoStore(self.config)  # 初始化

    def close(self):
        if hasattr(self,'mgo'):
            self.mgo.close()
            logging.info('close databases ok!')

    def history(self):
        pass
         
    def run(self):
        pass
