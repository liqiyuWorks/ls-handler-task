#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import os
import logging


class HandleTyphoon:
    def __init__(self, **kwargs):
        self._mgo = kwargs.get('mgo')
        self._row = kwargs.get('row')
        self._row_dict = {k.lower(): v for k, v in self._row.to_dict().items()}
        self._row_dict.update({"reporttime": self._row_dict.pop("reporttime_utc",None)})
        self.default_distance = int(os.getenv('DEFAULT_DISTANCE', 50))
        self.MONGO_TYPHOON = "typhoon_real_time_data"  # 实时数据库
        self._lat = self._row_dict.get('lat')
        self._lon = self._row_dict.get('lon')
        self._basin = self._row_dict.get('basin')
        self._stormid = self._row_dict.get('stormid')
        self._year = int(kwargs.get('year',2022))
        self._reporttime_utc = self._row_dict.get('reporttime')
        self._leadtime = self._row_dict.get('leadtime')
        if len(self._reporttime_utc) != 19:
            self._reporttime_utc = self._reporttime_utc + ' 00:00:00'
            self._row_dict['reporttime'] = self._reporttime_utc
        self._stormname = self._row_dict.get('stormname')

        reporttime_utc = datetime.strptime(self._reporttime_utc,
                                           '%Y-%m-%d %H:%M:%S')
        self._forecast_time = (
            reporttime_utc +
            timedelta(hours=self._leadtime)).strftime('%Y-%m-%d %H:%M:%S')
        logging.info(
            f"{self._stormid}:{self._stormname}:{self._basin}-{self._forecast_time}"
        )

    def query_typhoon(self):
        query = {"stormid": self._stormid, "year": self._year}
        res = self._mgo.mgo_coll.find_one(query, {"datatime": 0},
                                          sort=[('end_reporttime', -1)])
        return res

    def insert_dataTime2typhoon(self, id):
        datatime = self._row_dict
        del datatime['stormid']
        del datatime['modelname']

        aggregate_query = [{
            "$unwind": "$datatime"
        }, {
            "$match": {
                "_id": id,
                "datatime.reporttime": self._reporttime_utc,
            }
        }, {
            "$project": {
                "datatime": 1
            }
        }]
        res = list(self._mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            logging.info("已有该时刻预测数据，准备更新....")
            r = self._mgo.mgo_coll.update_one(
                {
                    "_id": id,
                    "datatime.reporttime": self._reporttime_utc
                }, {
                    "$set": {
                        "end_reporttime": self._reporttime_utc,
                        "stormname": datatime['stormname'],
                        "lat": self._lat,
                        "lon": self._lon,
                        "datatime.$.stormname":
                        self._row_dict.get('stormname'),
                        "datatime.$.lat": self._row_dict.get('lat'),
                        "datatime.$.lon": self._row_dict.get('lon'),
                        "datatime.$.minp": self._row_dict.get('minp'),
                        "datatime.$.maxsp": self._row_dict.get('maxsp'),
                        "datatime.$.r7_ne": self._row_dict.get('r7_ne'),
                        "datatime.$.r7_se": self._row_dict.get('r7_se'),
                        "datatime.$.r7_sw": self._row_dict.get('r7_sw'),
                        "datatime.$.r7_nw": self._row_dict.get('r7_nw'),
                        "datatime.$.r10_ne": self._row_dict.get('r10_ne'),
                        "datatime.$.r10_se": self._row_dict.get('r10_se'),
                        "datatime.$.r10_sw": self._row_dict.get('r10_sw'),
                        "datatime.$.r10_nw": self._row_dict.get('r10_nw'),
                        "datatime.$.r12_ne": self._row_dict.get('r12_ne'),
                        "datatime.$.r12_se": self._row_dict.get('r12_se'),
                        "datatime.$.r12_sw": self._row_dict.get('r12_sw'),
                        "datatime.$.r12_nw": self._row_dict.get('r12_nw'),
                        "datatime.$.speed": self._row_dict.get('speed'),
                        "datatime.$.direction":
                        self._row_dict.get('direction'),
                    }
                },
                upsert=True)

        else:
            del datatime['leadtime']
            r = self._mgo.mgo_coll.update({
                "_id": id,
            }, {
                "$set": {
                    "end_reporttime": self._reporttime_utc,
                    "lat": self._lat,
                    "lon": self._lon,
                    "stormname": self._stormname
                },
                "$push": {
                    "datatime": datatime
                }
            })
            print("嵌套数组新增成功res", r)

    def insert_update_gfs(self, id):
        dataTime = self._row_dict
        dataTime['forecast_time'] = self._forecast_time
        del dataTime['reporttime_utc']
        del dataTime['modelname']

        aggregate_query = [{
            "$unwind": "$datatime"
        }, {
            "$match": {
                "_id": id,
                "datatime.forecast_time": self._forecast_time,
            }
        }, {
            "$project": {
                "datatime": 1
            }
        }]
        res = list(self._mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            logging.info("已有该时刻预测数据，准备更新....")
            r = self._mgo.mgo_coll.update_one(
                {
                    "_id": id,
                    "datatime.forecast_time": self._forecast_time
                }, {
                    "$set": {
                        "end_forecast_time": self._forecast_time,
                        "lat": self._lat,
                        "lon": self._lon,
                        "datatime.$.lat": self._row_dict.get('lat'),
                        "datatime.$.lon": self._row_dict.get('lon'),
                        "datatime.$.minp": self._row_dict.get('minp'),
                        "datatime.$.maxsp": self._row_dict.get('maxsp'),
                        "datatime.$.r7_ne": self._row_dict.get('r7_ne'),
                        "datatime.$.r7_se": self._row_dict.get('r7_se'),
                        "datatime.$.r7_sw": self._row_dict.get('r7_sw'),
                        "datatime.$.r7_nw": self._row_dict.get('r7_nw'),
                        "datatime.$.r10_ne": self._row_dict.get('r10_ne'),
                        "datatime.$.r10_se": self._row_dict.get('r10_se'),
                        "datatime.$.r10_sw": self._row_dict.get('r10_sw'),
                        "datatime.$.r10_nw": self._row_dict.get('r10_nw'),
                        "datatime.$.r12_ne": self._row_dict.get('r12_ne'),
                        "datatime.$.r12_se": self._row_dict.get('r12_se'),
                        "datatime.$.r12_sw": self._row_dict.get('r12_sw'),
                        "datatime.$.r12_nw": self._row_dict.get('r12_nw'),
                        "datatime.$.speed": self._row_dict.get('speed'),
                        "datatime.$.direction":
                        self._row_dict.get('direction'),
                    }
                },
                upsert=True)

        else:
            r = self._mgo.mgo_coll.update({
                "_id": id,
            }, {
                "$set": {
                    "end_forecast_time": self._forecast_time,
                    "lat": self._lat,
                    "lon": self._lon
                },
                "$push": {
                    "datatime": dataTime
                }
            })

            print("嵌套数组新增成功res", r)

    def insert_gfs_reporttime(self, id):
        datatime = self._row_dict
        datatime['forecast_time'] = self._forecast_time
        del datatime['reporttime']
        del datatime['modelname']

        aggregate_query = [{
            "$unwind": f"$reporttime.{self._reporttime_utc}"
        }, {
            "$match": {
                "_id":
                id,
                f"reporttime.{self._reporttime_utc}.forecast_time":
                self._forecast_time,
            }
        }, {
            "$project": {
                f"reporttime.{self._reporttime_utc}": 1
            }
        }]
        print(aggregate_query)
        res = list(self._mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            logging.info("已有该时刻预测数据，准备更新....")
            r = self._mgo.mgo_coll.update_one(
                {
                    "_id":
                    id,
                    f"reporttime.{self._reporttime_utc}.forecast_time":
                    self._forecast_time
                }, {
                    "$set": {
                        "end_forecast_time":
                        self._forecast_time,
                        "newest_report_time":
                        self._reporttime_utc,
                        "lat":
                        self._lat,
                        "lon":
                        self._lon,
                        f"reporttime.{self._reporttime_utc}.$.lat":
                        self._row_dict.get('lat'),
                        f"reporttime.{self._reporttime_utc}.$.lon":
                        self._row_dict.get('lon'),
                        f"reporttime.{self._reporttime_utc}.$.minp":
                        self._row_dict.get('minp'),
                        f"reporttime.{self._reporttime_utc}.$.maxsp":
                        self._row_dict.get('maxsp'),
                        f"reporttime.{self._reporttime_utc}.$.r7_ne":
                        self._row_dict.get('r7_ne'),
                        f"reporttime.{self._reporttime_utc}.$.r7_se":
                        self._row_dict.get('r7_se'),
                        f"reporttime.{self._reporttime_utc}.$.r7_sw":
                        self._row_dict.get('r7_sw'),
                        f"reporttime.{self._reporttime_utc}.$.r7_nw":
                        self._row_dict.get('r7_nw'),
                        f"reporttime.{self._reporttime_utc}.$.r10_ne":
                        self._row_dict.get('r10_ne'),
                        f"reporttime.{self._reporttime_utc}.$.r10_se":
                        self._row_dict.get('r10_se'),
                        f"reporttime.{self._reporttime_utc}.$.r10_sw":
                        self._row_dict.get('r10_sw'),
                        f"reporttime.{self._reporttime_utc}.$.r10_nw":
                        self._row_dict.get('r10_nw'),
                        f"reporttime.{self._reporttime_utc}.$.r12_ne":
                        self._row_dict.get('r12_ne'),
                        f"reporttime.{self._reporttime_utc}.$.r12_se":
                        self._row_dict.get('r12_se'),
                        f"reporttime.{self._reporttime_utc}.$.r12_sw":
                        self._row_dict.get('r12_sw'),
                        f"reporttime.{self._reporttime_utc}.$.r12_nw":
                        self._row_dict.get('r12_nw'),
                        f"reporttime.{self._reporttime_utc}.$.speed":
                        self._row_dict.get('speed'),
                        f"reporttime.{self._reporttime_utc}.$.direction":
                        self._row_dict.get('direction'),
                    }
                },
                upsert=True)
        else:
            r = self._mgo.mgo_coll.update({
                "_id": id,
            }, {
                "$set": {
                    "end_forecast_time": self._forecast_time,
                    "newest_report_time": self._reporttime_utc,
                    "lat": self._lat,
                    "lon": self._lon
                },
                "$push": {
                    f"reporttime.{self._reporttime_utc}": datatime
                }
            })

            print("嵌套数组新增成功res", r)

    def save_typhoon_data(self):
        data = {
            "year": self._year,
            "stormid": self._stormid,
            "stormname": self._stormname,
        }
        data['start_reporttime'] = self._reporttime_utc
        data['end_reporttime'] = self._reporttime_utc
        data['lat'] = self._row_dict['lat']
        data['lon'] = self._row_dict['lon']

        tythoon = self.query_typhoon()
        if not tythoon:
            datatime = self._row_dict
            del datatime['stormid']
            del datatime['modelname']
            del datatime['leadtime']
            data['datatime'] = [datatime]
            self._mgo.set(None, data)
        else:
            id = tythoon.get('_id')
            self.insert_dataTime2typhoon(id)

    def query_gfs_typhoon(self):
        query = {
            "stormid": self._stormid,
            "basin": self._basin,
            "year": self._year
        }
        res = self._mgo.mgo_coll.find_one(query, {"reporttime": 0})

        if res:
            id = res.get('_id')
            self.insert_gfs_reporttime(id)
            return False
        return True

    def save_gfs_data(self):
        # 修改时间
        data = {
            "basin": self._basin,
            "stormid": self._stormid,
            "lat": self._lat,
            "lon": self._lon,
            "year": self._year
        }
        dataTime = self._row_dict

        dataTime['forecast_time'] = self._forecast_time
        data['start_forecast_time'] = self._forecast_time
        data['end_forecast_time'] = self._forecast_time
        data['newest_report_time'] = self._reporttime_utc
        del dataTime['reporttime']
        del dataTime['modelname']
        print("data= ", data)
        self._mgo.set(None, data)

    def close(self):
        self._mgo.close()


class WzTyphoon:
    def __init__(self, mgo, typhoon):
        self._mgo = mgo
        self._insert_data = typhoon
        self._insert_data.update(
            {
                "stormid": self._insert_data.pop("tfbh", None),
                "stormname": self._insert_data.pop("ename", None),
                "cn_stormname": self._insert_data.pop("name", None),
                "lon": None,
                "lat": None,
            })
        self._points = typhoon.get("points")
        self._real_time = None
        self._insert_data["realtime_data"] = []  # 实时数据
        self._insert_data["forecast_data"] = {}  # 预测数据

        self.handle_real_time()
        # logging.info(self._insert_data)
        

    def handle_real_time(self):
        for point in self._points:
            if point.get("forecast"):
                self.handle_forecast_data(point["forecast"])
            
            point.pop("forecast",None)
            point.update({"lon": point.pop("lng")})
            self._insert_data['lon']=point["lon"]
            self._insert_data['lat']=point["lat"]
            self._insert_data['end_time']=point["time"]
            self._insert_data["realtime_data"].append(point)

    def handle_forecast_data(self, forecasts):
        for forecast in forecasts:
            source,points = forecast['sets'],forecast['points']
            # print(f"此时源是{source}，data={points}\n")
            new_points = []
            for point in points:
                point.update({"lon": point.pop("lng")})
                new_points.append(point)
            self._insert_data["forecast_data"][source] = new_points

    def query_wz_exist(self):
        query = {"stormid": self._insert_data["stormid"], "stormname": self._insert_data['stormname']}
        res = self._mgo.mgo_coll.find_one(query, {"realtime_data": 0, "forecast_data":0,"points":0,"land":0})
        return res

    def update_mgo(self, wz_id):
        for point in self._insert_data["realtime_data"]:
            aggregate_query = [{
                "$unwind": "$realtime_data"
            }, {
                "$match": {
                    "_id": wz_id,
                    "realtime_data.time": point['time'],
                }
            }, {
                "$project": {
                    "realtime_data": 1,
                    "end_time":1
                }
            }]
            res = list(self._mgo.mgo_coll.aggregate(aggregate_query))

            if res:
                logging.info("已有该时刻预测数据，准备更新....")
                r = self._mgo.mgo_coll.update_one(
                    {
                        "_id": wz_id,
                        "realtime_data.time": point['time']
                    }, {
                        "$set": {
                            "realtime_data.$.lat": point.get('lat'),
                            "realtime_data.$.lon": point.get('lon'),
                            "realtime_data.$.strong": point.get('strong'),
                            "realtime_data.$.power": point.get('power'),
                            "realtime_data.$.speed": point.get('speed'),
                            "realtime_data.$.move_dir": point.get('move_dir'),
                            "realtime_data.$.move_speed": point.get('move_speed'),
                            "realtime_data.$.pressure": point.get('pressure'),
                            "realtime_data.$.radius7": point.get('radius7'),
                            "realtime_data.$.radius10": point.get('radius10'),
                            "realtime_data.$.radius12": point.get('radius12'),
                            "realtime_data.$.radius7_quad": point.get('radius7_quad'),
                            "realtime_data.$.radius10_quad": point.get('radius10_quad'),
                            "realtime_data.$.radius12_quad": point.get('radius12_quad'),
                            "realtime_data.$.remark": point.get('remark'),
                        }
                    },
                    upsert=True)

            else:
                r = self._mgo.mgo_coll.update({
                    "_id": wz_id,
                }, {
                    "$set": {
                        "end_time": point['time'],
                        "lat": point.get('lat'),
                        "lon": point.get('lon'),
                    },
                    "$push": {
                        "realtime_data": point
                    }
                })

                print("嵌套数组新增成功res", r)


    def save_mgo(self):
        '''如果数据库没有该条数据，则增加该条数据'''
        self._insert_data.pop("points", None)
        self._mgo.set(None, self._insert_data)