#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pymongo, os
import requests
import logging

def is_none(s):
    if s is None:
        return True
    flag = False
    if isinstance(s, str):
        if len(s.strip()) == 0:
            flag = True
        if s == '-':
            flag = True
    elif isinstance(s, list):
        if len(s) == 0:
            flag = True
    elif isinstance(s, dict):
        flag = True
        for v in s.values():
            if is_none(v):
                continue
            flag = False
            break
    return flag


def get_mgo():
    # 数据库源连接
    mongo_host = os.getenv('MONGO_HOST', '119.3.248.125')
    mongo_port = int(os.getenv('MONGO_PORT', '21617'))
    mongo_db = os.getenv('MONGO_DB', 'cma')

    if mongo_db is None:
        return None, None
    url = 'mongodb://{}:{}/'.format(mongo_host, mongo_port)
    mgo_client = pymongo.MongoClient(url)

    mgo_db = mgo_client[mongo_db]
    mongo_user = os.getenv('MONGO_USER', 'reader')
    mongo_password = os.getenv('MONGO_PASSWORD', 'Read1234')

    if mongo_user is not None:
        mgo_db.authenticate(mongo_user, mongo_password)
    return mgo_client, mgo_db


def read_mgo_data(key, mgo_db):
    response = {}
    try:
        res = mgo_db['nation_station'].find_one(key)
        if res is not None:
            response = res
    except Exception as e:
        print(e)
        return response
    return response

def parse_url(url):
    '''发起请求'''
    try:
        res = requests.get(url) 
        return res
    except Exception as e:
        print('error', e)

def query_all(mgo_db,mgo_coll,fcityname,year_now,month_now,day_now):
    query = {"Year" : year_now, 'Mon':month_now, 'Day':day_now, 'stationName':fcityname}
    res = mgo_db[mgo_coll].find(query,{'_id': 0})
    return res

def query_one_year(mgo_db,mgo_coll,fcityname,year_now):
    query = {"Year" : year_now, 'stationName':fcityname}
    print(query)
    res = mgo_db[mgo_coll].find(query,{'_id': 0})
    return res


def query_one(mgo_db,mgo_coll,**kwargs):
    stationId = kwargs['stationId']
    Mon = kwargs['Mon']
    Day = kwargs['Day']
    Hour = kwargs['Hour']
    Year = kwargs.get('Year', 2022)
    res = mgo_db[mgo_coll].find_one({"stationId": stationId,"Mon": Mon, "Day" : Day, "Hour": Hour, "Year" : Year})
    return res


def update_one(mgo_db,mgo_coll,**kwargs):
    stationId = kwargs['stationId']
    dateTime = kwargs['dateTime']
    Mon = kwargs['Mon']
    Day = kwargs['Day']
    Hour = kwargs['Hour']
    Year = kwargs.get('Year', 2022)
    update_data = kwargs.get('update_data')
    # del_data = kwargs.get('del_data')

    res = mgo_db[mgo_coll].update_one({"stationId": stationId,"Mon": Mon, "Day" : Day, "Hour": Hour, "Year" : Year}, 
    {"$set": update_data})
    # res = mgo_db[mgo_coll].update_one({"stationId": stationId,"dateTime":dateTime}, {'$unset': del_data})
    return res

def write_one(mgo_db,mgo_coll,data):
    # 插入数据
    res = mgo_db[mgo_coll].insert_one(data)
    return res


class MgoStore(object):
    def __init__(self, config):
        self.config = config
        # 连接对象
        self.mgo_client = config['mgo_client']
        self.mgo_db = config['mgo_db']

        # 字符串
        self.collection = config['collection']
        self.mgo_coll = self.mgo_db[self.collection]
        # 唯一索引列
        self.uniq_idx = config['uniq_idx']
        # 常规索引名称和索引列 字典
        self.idx_dic = config.get('idx_dic', {})

        # 检查索引是否创建
        index_dic = self.mgo_coll.index_information()
        self.mgo_coll.create_index(self.uniq_idx, unique=True, name='{}_uniq_idx'.format(self.collection))
        for idx_name, idx in self.idx_dic.items():
            if idx_name in index_dic:
                continue
            self.mgo_coll.create_index(idx, name=idx_name)

    def set(self, key, data, extra=None):
        response = None
        try:
            query = {}
            if is_none(key):
                for field_tuple in self.uniq_idx:
                    field = field_tuple[0]
                    query[field] = data[field]
            else:
                query = key
            if extra is not None and 'op' in extra:
                op = extra['op']
            else:
                op = '$set'
            res = self.mgo_coll.update_one(query, {op: data}, upsert=True)
            if res.raw_result['updatedExisting']:
                if res.raw_result['nModified'] > 0:
                    logging.info('update {}'.format(data))
                else:
                    logging.info('nothing to update for key {}'.format(query))
            elif 'upserted' in res.raw_result:
                logging.info('insert {} {}'.format(res.raw_result['upserted'], data))
            else:
                logging.info('impossible update_one result {}'.format(res.raw_result))
            response = res.raw_result
        except pymongo.errors.DuplicateKeyError:
            # 索引建对了，就不会走到这个分支
            logging.info('duplicate key {}'.format(key))
        except Exception as e:
            logging.error('key {} data {}'.format(key, data))
            logging.error(e)
            return response
        return response


    def get(self, key, extra=None):
        response = {}
        try:
            if isinstance(extra, dict) and 'out_fileds' in extra:
                out_fields = extra['out_fields']
            else:
                out_fields = {'_id': 0}
            res = self.mgo_coll.find_one(key, out_fields)
            if res is not None:
                response = res
        except Exception as e:
            print(e)
            return response
        return response

    def close(self):
        self.mgo_client.close()
