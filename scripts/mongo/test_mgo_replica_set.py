#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, pymongo
import urllib.parse

def get_mgo():
    # 数据库源连接
    mongo_host = os.getenv('MONGO_HOST', '124.70.86.179')
    _59mongo_host = os.getenv('MONGO_HOST', '121.36.28.59')
    mongo_port = int(os.getenv('MONGO_PORT', '21617'))
    mongo_db = os.getenv('MONGO_DB', 'base_data')
    mongo_user = os.getenv('MONGO_USER', 'root')
    mongo_password = os.getenv('MONGO_PASSWORD', 'Jiufang1234')
    # mgo_client = pymongo.MongoReplicaSetClient(f"{mongo_host}:21617,{_59mongo_host}:21617", replicaSet="rs",read_preference=pymongo.ReadPreference.SECONDARY,authSource='base_data')
    mgo_client = pymongo.MongoReplicaSetClient(f"{mongo_host}:21617,{_59mongo_host}:21617", replicaSet="rs")
    print(mgo_client.test_database)
    return mgo_client


mgo_client = get_mgo()
mgo_db = mgo_client['base_data']
print(mgo_client, mgo_db)
data = mgo_db['users'].find({})
for d in data:
    print(d)