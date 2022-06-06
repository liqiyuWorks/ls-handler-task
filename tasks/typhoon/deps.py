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
    def __init__(self, **kwargs) -> None:
        self.default_distance = int(os.getenv('DEFAULT_DISTANCE', 50))
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
        print("row=",self._row.to_dict())


    def query_typhoon(self):
        query = {"StormID": self._StormID,"StormName": self._StormName,"YEAR":self._YEAR}
        res = self._mgo.mgo_coll.find_one(query)
        return res

    def query_reporttime_UTC_typhoon(self):
        query = {"StormID": self._StormID,"StormName": self._StormName, "dataTime.reporttime_UTC": self._reporttime_UTC}
        res = self._mgo.mgo_coll.find_one(query)
        return res

    def insert_dataTime2typhoon(self):
        dataTime = self._row.to_dict()
        if len(dataTime['reporttime_UTC']) != 19:
            dataTime['reporttime_UTC'] = dataTime['reporttime_UTC'] + ' 00:00:00'
        del dataTime['StormID']
        del dataTime['StormName']
        del dataTime['ModelName']
        res = self._mgo.mgo_coll.update(
            {"StormID" : self._StormID,"StormName" : self._StormName,"YEAR": self._YEAR},
            {
                "$push":{
                    "dataTime": dataTime
                }
            });
        print('更新成功,res=',res)

    def save_typhoon_data(self) -> None:
        data = {
            "YEAR": self._YEAR,
            "StormID": self._StormID,
            "StormName": self._StormName,
        }
        data['start_reporttime_UTC'] = self._reporttime_UTC
        data['Lat'] = self._row['Lat']
        data['Lon'] = self._row['Lon']

        if not self.query_typhoon():
            # 考虑一种特殊情况：台风改名情况！！！！ （首先去看前一个结束时间与该台风的新时间，最后重命名为最新的）
            query = {"StormID": self._StormID,"YEAR":self._YEAR}
            orig_typhoon_list = list(self._mgo.mgo_coll.find(query))
            if orig_typhoon_list:
                if len(orig_typhoon_list) != 1:
                    print('不仅仅有两个台风哦')
                else:
                    ## 判断这两个台风是不是同一个台风？？
                    orig_typhoon = orig_typhoon_list[0]
                    id = orig_typhoon.get('_id')
                    lat = float(orig_typhoon.get('Lat'))
                    lon = float(orig_typhoon.get('Lon'))
                    orig_dataTime = orig_typhoon.get('dataTime')[-1].get('reporttime_UTC')
                    orig_dataTime = datetime.strptime(orig_dataTime, '%Y-%m-%d %H:%M:%S')
                    now_dataTime = datetime.strptime(self._reporttime_UTC, '%Y-%m-%d %H:%M:%S')
                    print(distance.euclidean((lat, lon), (self._Lat, self._Lon)))
                    if (abs((orig_dataTime-now_dataTime).days) < 3) and (distance.euclidean((lat, lon), (self._Lat, self._Lon))<30):
                        ## 此时 可以确定是同一个台风
                        orig_typhoon['StormName'] = self._StormName
                        self._mgo.mgo_coll.update_one({"_id": id}, {"$set": orig_typhoon}, upsert=True)
                    else:
                        # 最后新增新台风
                        self._mgo.set(None, data)
            else:
                self._mgo.set(None, data)

        res = self.query_reporttime_UTC_typhoon()
        if not res:
            # 插入该台风的实时轨迹
            self.insert_dataTime2typhoon()
        else:
            print('该轨迹已存在')

    def query_gfs_typhoon(self):
        typhoon_id = None
        reporttime_UTC = datetime.strptime(self._reporttime_UTC, '%Y-%m-%d %H:%M:%S')
        forecast_time = reporttime_UTC + timedelta(hours=self._LeadTime)

        pipeline = [
            {'$match': {"StormID": self._StormID,"Basin": self._Basin}},
            {'$group': {'_id': "$typhoon_id",
                        '_date_list': {"$push": "$forecast_time"}
                        }}
        ]
        res = self._mgo.mgo_coll.aggregate(pipeline)
        date_list = []
        
        for re in res:
            id = re.get("_id")
            if id == None:
                continue
            orig_date = re.get('_date_list')[0]
            if orig_date < forecast_time.strftime('%Y-%m-%d %H:%M:%S'):
                continue
            
            r = self._mgo.mgo_db[self.MONGO_TYPHOON].find_one({"_id":id})
            date = r.get('dataTime',[])[-1].get('reporttime_UTC')
            date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            if abs((date-forecast_time).days) < 3:
                StormID = r.get('StormID')
                StormName = r.get('StormName')
                date_list.append((date, id, StormID, StormName))
        if date_list:
            date_list = sorted(date_list, key=lambda d: d[0], reverse=True)
            exist_tuple = date_list[0]
            data = self._row.to_dict()
            data['typhoon_id'] = exist_tuple[1]
            data['typhoon_StormID'] = exist_tuple[2]
            data['typhoon_StormName'] = exist_tuple[3]
            data['forecast_time'] = forecast_time.strftime('%Y-%m-%d %H:%M:%S')
            del data['reporttime_UTC']
            self._mgo.set(None, data)
            print("数据库已存在该台风")
            return False
        return True


    def query_real_time_typhoon(self):
        typhoon_id = None
        query = {"dataTime": {"$elemMatch":{ "reporttime_UTC": self._reporttime_UTC}}}
        res = self._mgo.mgo_db[self.MONGO_TYPHOON].find(query,{'dataTime.$': 1},sort=[('start_reporttime_UTC', -1)])

        diffs = []
        for item in res:
            id = item.get('_id')
            print(id)
            lat = item.get('dataTime',[])[-1].get('Lat')
            lon = item.get('dataTime',[])[-1].get('Lon')
            if (lat > 0 and self._Lat>0) or (lat < 0 and self._Lat<0):
                if (lon > 0 and self._Lon>0) or (lon < 0 and self._Lon<0):
                    a = (lat, lon)
                    temp_diff = distance.euclidean(a, (self._Lat, self._Lon))
                    if temp_diff <= self.default_distance:
                        diffs.append([temp_diff, id])
        diffs = sorted(diffs, key=lambda x: x[0])
        # print("最短距离:",diffs)
        if diffs:
            typhoon_id = diffs[0][1]
            return typhoon_id

        return None

    def save_gfs_data(self,typhoon_id):
        ## 确定该轨迹属于 某个台风
        query = {"_id": typhoon_id}
        typhoon = self._mgo.mgo_db[self.MONGO_TYPHOON].find_one(query)
        typhoon = typhoon if typhoon else {}
        # 修改时间
        reporttime_UTC = datetime.strptime(self._reporttime_UTC, '%Y-%m-%d %H:%M:%S')
        forecast_time = (reporttime_UTC + timedelta(hours=self._LeadTime)).strftime('%Y-%m-%d %H:%M:%S')
        data = self._row.to_dict()
        data['typhoon_id'] = typhoon_id
        data['typhoon_StormName'] = typhoon.get('StormName')
        data['typhoon_StormID'] = typhoon.get('StormID')
        
        data['forecast_time'] = forecast_time
        del data['reporttime_UTC']
        if typhoon:
            lat = float(typhoon.get('Lat'))
            lon = float(typhoon.get('Lon'))
            a = (lat, lon)
            temp_diff = distance.euclidean(a, (self._Lat, self._Lon))
            print(f"最短距离= {temp_diff}----real_point=({a}), gfs_point=({self._Lat}, {self._Lon})")
        res = self._mgo.set(None, data)
        
        

    def close(self):
        self._mgo.close()
