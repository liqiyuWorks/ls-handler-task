#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, pymongo
import time

def get_mgo():
    # 数据库源连接
    mongo_host = os.getenv('MONGO_HOST', '124.70.86.179')
    _59mongo_host = os.getenv('MONGO_HOST', '121.36.28.59')
    mongo_port = int(os.getenv('MONGO_PORT', '21617'))
    mongo_db = os.getenv('MONGO_DB', 'base_data')
    mongo_user = os.getenv('MONGO_USER', 'root')
    mongo_password = os.getenv('MONGO_PASSWORD', 'Jiufang1234')
    dburl = f'mongodb://{mongo_host}:{mongo_port},{_59mongo_host}:{mongo_port}/?replicaSet=rs&readPreference=secondaryPreferred&connectTimeoutMS=300000'

    database = mongo_db
    mgo_client = pymongo.MongoClient(dburl)
    mgo_db=mgo_client[database]
    # if mongo_user is not None:
    #     mgo_db.authenticate(mongo_user, mongo_password)
    tmp_collect = mgo_db['test']
    print(tmp_collect.find_one({}))
    print("开始插入")
    count = 0
    while count < 100:
        mgo_db['test'].insert({"name": count})
        print(f"插入{count}成功...")
        time.sleep(2)

    mgo_client.close()

get_mgo()