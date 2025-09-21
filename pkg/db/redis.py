#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import redis
import json
import logging
import logging.handlers
import traceback
from redis.connection import ConnectionPool


class RdsQueue:
    _pool = None  # 类变量，共享连接池

    def __init__(self):

        host = os.getenv('REDIS_HOST', None)
        port = int(os.getenv('REDIS_PORT', '6379'))
        password = os.getenv('REDIS_PASSWORD', None)
        if host:
            if RdsQueue._pool is None:
                # 初始化全局连接池（仅第一次实例化时执行）
                RdsQueue._pool = ConnectionPool(
                    host=host,
                    port=port,
                    db=0,
                    password=password,
                    max_connections=10,  # 根据实际情况调整
                    decode_responses=True,
                    health_check_interval=30
                )
            self.rds = redis.Redis(connection_pool=RdsQueue._pool)

            # old
            # self.rds = redis.Redis(host=host, port=port, db=0, password=password,
            #                        decode_responses=True, health_check_interval=30)
            logging.info('=> {} connected'.format(self.rds))
        else:
            self.rds = None
            logging.info('rds connect failed...')

    # data 为dict或者list类型， 需要json序列化

    def push(self, queue_name, data, extra=None):
        result = None
        try:
            if isinstance(data, dict) or isinstance(data, list):
                result = self.rds.rpush(queue_name, json.dumps(data))
            else:
                result = self.rds.rpush(queue_name, data)
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
        return result

    def pop(self, queue_name, extra=None):
        result = None
        try:
            result = self.rds.lpop(queue_name)
            if result is not None:
                result = json.loads(result)
        except json.decoder.JSONDecodeError:
            return result
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
        return result

    @classmethod
    def close_pool(cls):
        if cls._pool:
            cls._pool.disconnect()
            logging.info('close RdsQueue engine ok!')

    def close(self):
        if self.rds:
            self.rds.close()


# 采用redis队列
class RdsTaskQueue:
    def __init__(self, rds):
        self.rds = rds

    # data 为dict或者list类型， 需要json序列化
    def push(self, queue_name, data, extra=None):
        result = None
        try:
            if isinstance(data, dict) or isinstance(data, list):
                result = self.rds.rpush(queue_name, json.dumps(data))
            else:
                result = self.rds.rpush(queue_name, data)
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
        return result

    def pop(self, queue_name, extra=None):
        result = None
        try:
            result = self.rds.lpop(queue_name)
            if result is not None:
                result = json.loads(result)
        except json.decoder.JSONDecodeError:
            return result
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
        return result

    def close(self):
        try:
            self.rds.close()
        except Exception as e:
            logging.error(e)
