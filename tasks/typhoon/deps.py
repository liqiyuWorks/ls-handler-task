#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pymongo, os
import logging
from scipy.spatial import distance

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
        self.mgo_coll.create_index(self.uniq_idx,
                                   unique=True,
                                   name='{}_uniq_idx'.format(self.collection))
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
                logging.info('insert {} {}'.format(res.raw_result['upserted'],
                                                   data))
            else:
                logging.info('impossible update_one result {}'.format(
                    res.raw_result))
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


class HandleTyphoon:
    def __init__(self, **kwargs):
        self.default_distance = int(os.getenv('DEFAULT_DISTANCE', 100))
        self.MONGO_TYPHOON = "typhoon_real_time_data"
        self._mgo = kwargs.get('mgo')
        self._row = kwargs.get('row')
        self._Lat = self._row.get('Lat')
        self._Lon = self._row.get('Lon')
        self._Basin = self._row.get('Basin')
        self._StormID = self._row.get('StormID')
        self._YEAR = kwargs.get('YEAR')
        self._reporttime_UTC = self._row.get('reporttime_UTC')
        self._LeadTime= self._row.get('LeadTime')
        if len(self._reporttime_UTC) != 19:
            self._reporttime_UTC = self._reporttime_UTC + ' 00:00:00'
        self._StormName = self._row.get('StormName')
        # print("row=",self._row.to_dict())

        reporttime_UTC = datetime.strptime(self._reporttime_UTC, '%Y-%m-%d %H:%M:%S')
        self._forecast_time = (reporttime_UTC + timedelta(hours=self._LeadTime)).strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"{self._StormID}:{self._Basin} 预测时间={self._forecast_time}")


    def query_typhoon(self):
        # query = {"StormID": self._StormID,"StormName": self._StormName,"YEAR":self._YEAR}
        query = {"StormID": self._StormID,"YEAR":self._YEAR}
        res = self._mgo.mgo_coll.find_one(query,{"dataTime":0},sort=[('end_reporttime_UTC', -1)])
        return res

    def query_reporttime_UTC_typhoon(self):
        query = {"StormID": self._StormID,"StormName": self._StormName, "end_reporttime_UTC": self._reporttime_UTC}
        res = self._mgo.mgo_coll.find_one(query)
        return res

    def insert_dataTime2typhoon(self,id):
        dataTime = self._row.to_dict()
        if len(dataTime['reporttime_UTC']) != 19:
            dataTime['reporttime_UTC'] = dataTime['reporttime_UTC'] + ' 00:00:00'
        del dataTime['StormID']
        del dataTime['ModelName']

        aggregate_query = [{"$unwind":"$dataTime"},
                            {
                                "$match":{
                                "_id": id,
                                "dataTime.reporttime_UTC": dataTime['reporttime_UTC'],
                                }
                            },
                            {
                                "$project":{
                                "dataTime" : 1
                                }
                            }]
        res = list(self._mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            logging.info("已有该时刻预测数据，准备更新....")
            r = self._mgo.mgo_coll.update_one({"_id" : id, "dataTime.reporttime_UTC" : dataTime['reporttime_UTC']}, {"$set": {
                "end_reporttime_UTC":dataTime['reporttime_UTC'],
                "Lat":self._Lat,
                "Lon": self._Lon,
                "dataTime.$.Lat": self._row.get('Lat'),
                "dataTime.$.Lon": self._row.get('Lon'),
                "dataTime.$.MinP": self._row.get('MinP'),
                "dataTime.$.MaxSP": self._row.get('MaxSP'),
                "dataTime.$.R7_NE": self._row.get('R7_NE'),
                "dataTime.$.R7_SE": self._row.get('R7_SE'),
                "dataTime.$.R7_SW": self._row.get('R7_SW'),
                "dataTime.$.R7_NW": self._row.get('R7_NW'),
                "dataTime.$.R10_NE": self._row.get('R10_NE'),
                "dataTime.$.R10_SE": self._row.get('R10_SE'),
                "dataTime.$.R10_SW": self._row.get('R10_SW'),
                "dataTime.$.R10_NW": self._row.get('R10_NW'),
                "dataTime.$.R12_NE": self._row.get('R12_NE'),
                "dataTime.$.R12_SE": self._row.get('R12_SE'),
                "dataTime.$.R12_SW": self._row.get('R12_SW'),
                "dataTime.$.R12_NW": self._row.get('R12_NW'),
                "dataTime.$.speed": self._row.get('speed'),
                "dataTime.$.direction": self._row.get('direction'),
                }}, upsert=True)
                
        else:
            r = self._mgo.mgo_coll.update(
            {"_id" : id,},
            {
            "$set": {
                    "end_reporttime_UTC":dataTime['reporttime_UTC'],
                    "Lat":self._Lat,
                    "Lon": self._Lon
                    },
            "$push": {
                "dataTime": dataTime
            }
            })
            print("嵌套数组新增成功res",r)

    def insert_update_gfs(self,id):
        dataTime = self._row.to_dict()
        dataTime['forecast_time'] = self._forecast_time
        del dataTime['reporttime_UTC']
        del dataTime['ModelName']

        aggregate_query = [{"$unwind":"$dataTime"},
                            {
                                "$match":{
                                "_id": id,
                                "dataTime.forecast_time": self._forecast_time,
                                }
                            },
                            {
                                "$project":{
                                "dataTime" : 1
                                }
                            }]
        res = list(self._mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            logging.info("已有该时刻预测数据，准备更新....")
            r = self._mgo.mgo_coll.update_one({"_id" : id, "dataTime.forecast_time" : self._forecast_time}, {"$set": {
                "end_forecast_time":self._forecast_time,
                "Lat":self._Lat,
                "Lon": self._Lon,
                "dataTime.$.Lat": self._row.get('Lat'),
                "dataTime.$.Lon": self._row.get('Lon'),
                "dataTime.$.MinP": self._row.get('MinP'),
                "dataTime.$.MaxSP": self._row.get('MaxSP'),
                "dataTime.$.R7_NE": self._row.get('R7_NE'),
                "dataTime.$.R7_SE": self._row.get('R7_SE'),
                "dataTime.$.R7_SW": self._row.get('R7_SW'),
                "dataTime.$.R7_NW": self._row.get('R7_NW'),
                "dataTime.$.R10_NE": self._row.get('R10_NE'),
                "dataTime.$.R10_SE": self._row.get('R10_SE'),
                "dataTime.$.R10_SW": self._row.get('R10_SW'),
                "dataTime.$.R10_NW": self._row.get('R10_NW'),
                "dataTime.$.R12_NE": self._row.get('R12_NE'),
                "dataTime.$.R12_SE": self._row.get('R12_SE'),
                "dataTime.$.R12_SW": self._row.get('R12_SW'),
                "dataTime.$.R12_NW": self._row.get('R12_NW'),
                "dataTime.$.speed": self._row.get('speed'),
                "dataTime.$.direction": self._row.get('direction'),
                }}, upsert=True)
                
        else:
            r = self._mgo.mgo_coll.update(
            {
                "_id" : id,
            },
            {
            "$set": {
                    "end_forecast_time":self._forecast_time,
                    "Lat":self._Lat,
                    "Lon": self._Lon
                    },
            "$push": {
                "dataTime": dataTime
            }
            })
            
            print("嵌套数组新增成功res",r)

    def save_typhoon_data(self):
        data = {
            "YEAR": self._YEAR,
            "StormID": self._StormID,
            "StormName": self._StormName,
        }
        data['start_reporttime_UTC'] = self._reporttime_UTC
        data['end_reporttime_UTC'] = self._reporttime_UTC
        data['Lat'] = self._row['Lat']
        data['Lon'] = self._row['Lon']

        tythoon = self.query_typhoon()
        if not tythoon:
            dataTime = self._row.to_dict()
            if len(dataTime['reporttime_UTC']) != 19:
                dataTime['reporttime_UTC'] = dataTime['reporttime_UTC'] + ' 00:00:00'
            del dataTime['StormID']
            del dataTime['ModelName']
            data['dataTime'] = [dataTime]
            self._mgo.set(None, data)
        else:
            ## 判断这两个台风是不是同一个台风？？
            id = tythoon.get('_id')
            self.insert_dataTime2typhoon(id)

    def query_gfs_typhoon(self):
        query = {"StormID": self._StormID,"Basin": self._Basin, "year": self._YEAR}
        res = self._mgo.mgo_coll.find_one(query,{"dataTime": 0})

        if res:
            id = res.get('_id')
            self.insert_update_gfs(id)
            print("数据库已存在该台风")
            return False
        return True

    def query_real_time_typhoon(self):
        typhoon_id = None
        reporttime_UTC = datetime.strptime(self._reporttime_UTC, '%Y-%m-%d %H:%M:%S')
        forecast_time = (reporttime_UTC + timedelta(hours=self._LeadTime)).strftime('%Y-%m-%d %H:%M:%S')
        query = {"start_reporttime_UTC": {"$lte": forecast_time}}
        res = self._mgo.mgo_db[self.MONGO_TYPHOON].find(query,sort=[('end_reporttime_UTC', -1)])

        diffs = []
        for item in res:
            end_reporttime_UTC = item.get('end_reporttime_UTC')
            end_reporttime_UTC = datetime.strptime(end_reporttime_UTC, '%Y-%m-%d %H:%M:%S')
            if (reporttime_UTC + timedelta(hours=self._LeadTime) - end_reporttime_UTC).days > 3:
                continue
            dataTime = item.get('dataTime',[])
            if len(dataTime) <= 1 or dataTime is None:
                continue
            id = item.get('_id')
            lat = item.get('Lat')
            lon = item.get('Lon')
            a = (lat, lon)
            temp_diff = distance.euclidean(a, (self._Lat, self._Lon))
            if temp_diff <= self.default_distance:
                diffs.append([temp_diff, id])
        diffs = sorted(diffs, key=lambda x: x[0])
        print("最短距离:",diffs)
        if diffs:
            typhoon_id = diffs[0][1]
            return typhoon_id
        return None

    def save_gfs_data(self):
         # 修改时间
        data = {
            "Basin": self._Basin,
            "StormID": self._StormID,
            "Lat":self._Lat,
            "Lon": self._Lon,
            "year": self._YEAR
         }
        dataTime = self._row.to_dict()
        
        dataTime['forecast_time'] = self._forecast_time
        data['start_forecast_time'] = self._forecast_time
        data['end_forecast_time'] = self._forecast_time
        del dataTime['reporttime_UTC']
        del dataTime['ModelName']
        data['dataTime'] = [dataTime]
        print("data= ",data)
        self._mgo.set(None, data)
        
    def close(self):
        self._mgo.close()
