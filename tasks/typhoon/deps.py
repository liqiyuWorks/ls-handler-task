#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from time import sleep
from pkg.util.format import time_CST2UTC
import os
import logging

COEFFICIENT_KT_MS = 0.51444  # 统一kt
NAUTICAL_MILE_KM = 1.852    # 统一nautical mile
# 1kts=1.85 km/h
# speed是 km/h => kts = speed/NAUTICAL_MILE_KM
# max_speed m/s => kt = max_speed/COEFFICIENT_KT_MS

### 将错就错  温州台风网  speed是 km/h => kts = speed/COEFFICIENT_KT_MS

class HandleGFSTyphoon:
    def __init__(self, **kwargs):
        self._mgo = kwargs.get('mgo')
        self._row = kwargs.get('row')
        self._row_dict = {k.lower(): v for k, v in self._row.to_dict().items()}
        self._row_dict.update({
            "reporttime": self._row_dict.pop("reporttime_utc",None),
            # 统一单位
            "r34_ne": round(float(self._row_dict.pop("r7_ne", 0))/NAUTICAL_MILE_KM,2),
            "r34_se": round(float(self._row_dict.pop("r7_se", 0))/NAUTICAL_MILE_KM,2),
            "r34_sw": round(float(self._row_dict.pop("r7_sw", 0))/NAUTICAL_MILE_KM,2),
            "r34_nw": round(float(self._row_dict.pop("r7_nw", 0))/NAUTICAL_MILE_KM,2),
            "r50_ne": round(float(self._row_dict.pop("r10_ne", 0))/NAUTICAL_MILE_KM,2),
            "r50_se": round(float(self._row_dict.pop("r10_se", 0))/NAUTICAL_MILE_KM,2),
            "r50_sw": round(float(self._row_dict.pop("r10_sw", 0))/NAUTICAL_MILE_KM,2),
            "r50_nw": round(float(self._row_dict.pop("r10_nw", 0))/NAUTICAL_MILE_KM,2),
            "r64_ne": round(float(self._row_dict.pop("r12_ne", 0))/NAUTICAL_MILE_KM,2),
            "r64_se": round(float(self._row_dict.pop("r12_se", 0))/NAUTICAL_MILE_KM,2),
            "r64_sw": round(float(self._row_dict.pop("r12_sw", 0))/NAUTICAL_MILE_KM,2),
            "r64_nw": round(float(self._row_dict.pop("r12_nw", 0))/NAUTICAL_MILE_KM,2),
            "maxsp": round(float(self._row_dict.pop("maxsp", 0))/COEFFICIENT_KT_MS,0),
            "speed": round(float(self._row_dict.pop("speed", 0))/COEFFICIENT_KT_MS,0),
            "direction": round(float(self._row_dict.pop("direction", 0)),0),
            })
        print(self._row_dict)
        self.default_distance = int(os.getenv('DEFAULT_DISTANCE', 50))
        self._lat = self._row_dict.get('lat')
        self._lon = self._row_dict.get('lon')
        self._basin = self._row_dict.get('basin')
        self._stormid = self._row_dict.get('stormid')
        
        self._reporttime_utc = self._row_dict.get('reporttime')
        self._leadtime = self._row_dict.get('leadtime')
        if len(self._reporttime_utc) != 19:
            self._reporttime_utc = self._reporttime_utc + ' 00:00:00'
            self._row_dict['reporttime'] = self._reporttime_utc
        self._stormname = self._row_dict.get('stormname')
        # self._year = int(kwargs.get('year',2022))
        self._year = int(self._reporttime_utc[:4])

        reporttime_utc = datetime.strptime(self._reporttime_utc,
                                           '%Y-%m-%d %H:%M:%S')
        self._forecast_time = (
            reporttime_utc +
            timedelta(hours=self._leadtime)).strftime('%Y-%m-%d %H:%M:%S')
        logging.info(
            f"{self._stormid}:{self._stormname}:{self._basin}-{self._forecast_time}"
        )

    def query_realtime_typhoon(self):
        query = {"stormid": self._stormid, "year": self._year}
        # query = {"stormid": self._stormid}
        res = self._mgo.mgo_coll.find_one(query, {"datatime": 0},
                                          sort=[('end_reporttime', -1)])
        return res

    def insert_realtime_datatime(self, id):
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
            logging.info("已有该时刻实测数据，准备更新....")
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
                        "datatime.$.stormname": self._row_dict.get('stormname'),
                        "datatime.$.lat": self._row_dict.get('lat'),
                        "datatime.$.lon": self._row_dict.get('lon'),
                        "datatime.$.minp": self._row_dict.get('minp'),
                        "datatime.$.maxsp": self._row_dict.get('maxsp'),
                        "datatime.$.r34_ne": self._row_dict.get("r34_ne", None),
                        "datatime.$.r34_se": self._row_dict.get("r34_se", None),
                        "datatime.$.r34_sw": self._row_dict.get("r34_sw", None),
                        "datatime.$.r34_nw": self._row_dict.get("r34_nw", None),
                        "datatime.$.r50_ne": self._row_dict.get("r50_ne", None),
                        "datatime.$.r50_se": self._row_dict.get("r50_se", None),
                        "datatime.$.r50_sw": self._row_dict.get("r50_sw", None),
                        "datatime.$.r50_nw": self._row_dict.get("r50_nw", None),
                        "datatime.$.r64_ne": self._row_dict.get("r64_ne", None),
                        "datatime.$.r64_se": self._row_dict.get("r64_se", None),
                        "datatime.$.r64_sw": self._row_dict.get("r64_sw", None),
                        "datatime.$.r64_nw": self._row_dict.get("r64_nw", None),
                        "datatime.$.speed": self._row_dict.get('speed'),
                        "datatime.$.direction": self._row_dict.get('direction'),
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
            print("实测数据嵌套新增成功res", r)

    def insert_forecast_reporttime(self, id):
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
                # f"reporttime.{self._reporttime_utc}": 1
                "_id":1
            }
        }]
        print(aggregate_query)
        res = list(self._mgo.mgo_coll.aggregate(aggregate_query))
        if res:
            logging.info("已有该时刻预测数据，准备更新....")
            r = self._mgo.mgo_coll.update_one(
                {
                    "_id": id,
                    f"reporttime.{self._reporttime_utc}.forecast_time": self._forecast_time
                }, {
                    "$set": {
                        "end_forecast_time": self._forecast_time,
                        "newest_report_time": self._reporttime_utc,
                        "lat": self._lat,
                        "lon": self._lon,
                        f"reporttime.{self._reporttime_utc}.$.lat": self._row_dict.get('lat'),
                        f"reporttime.{self._reporttime_utc}.$.lon": self._row_dict.get('lon'),
                        f"reporttime.{self._reporttime_utc}.$.minp": self._row_dict.get('minp'),
                        f"reporttime.{self._reporttime_utc}.$.maxsp": self._row_dict.get('maxsp'),
                        f"reporttime.{self._reporttime_utc}.$.r34_ne": self._row_dict.get("r34_ne", None),
                        f"reporttime.{self._reporttime_utc}.$.r34_se": self._row_dict.get("r34_se", None),
                        f"reporttime.{self._reporttime_utc}.$.r34_sw": self._row_dict.get("r34_sw", None),
                        f"reporttime.{self._reporttime_utc}.$.r34_nw": self._row_dict.get("r34_nw", None),
                        f"reporttime.{self._reporttime_utc}.$.r50_ne": self._row_dict.get("r50_ne", None),
                        f"reporttime.{self._reporttime_utc}.$.r50_se": self._row_dict.get("r50_se", None),
                        f"reporttime.{self._reporttime_utc}.$.r50_sw": self._row_dict.get("r50_sw", None),
                        f"reporttime.{self._reporttime_utc}.$.r50_nw": self._row_dict.get("r50_nw", None),
                        f"reporttime.{self._reporttime_utc}.$.r64_ne": self._row_dict.get("r64_ne", None),
                        f"reporttime.{self._reporttime_utc}.$.r64_se": self._row_dict.get("r64_se", None),
                        f"reporttime.{self._reporttime_utc}.$.r64_sw": self._row_dict.get("r64_sw", None),
                        f"reporttime.{self._reporttime_utc}.$.r64_nw": self._row_dict.get("r64_nw", None),
                        f"reporttime.{self._reporttime_utc}.$.speed": self._row_dict.get('speed'),
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

            print("预测嵌套新增成功res", r)

    def save_realtime_data(self):
        data = {
            "year": self._year,
            "stormid": self._stormid,
            "stormname": self._stormname,
        }
        data['start_reporttime'] = self._reporttime_utc
        data['end_reporttime'] = self._reporttime_utc
        data['lat'] = self._row_dict['lat']
        data['lon'] = self._row_dict['lon']

        tythoon = self.query_realtime_typhoon()
        if not tythoon:
            datatime = self._row_dict
            del datatime['stormid']
            del datatime['modelname']
            del datatime['leadtime']
            data['datatime'] = [datatime]
            self._mgo.set(None, data)
        else:
            id = tythoon.get('_id')
            self.insert_realtime_datatime(id)

    def query_gfs_typhoon(self):
        query = {
            "stormid": self._stormid,
            "basin": self._basin,
            "year": self._year
        }
        res = self._mgo.mgo_coll.find_one(query, {"reporttime": 0})

        if res:
            id = res.get('_id')
            self.insert_forecast_reporttime(id)
            return False
        return True

    def save_forecast_data(self):
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
                "stormname": str(self._insert_data.pop("ename", None)).upper(),
                "cn_stormname": self._insert_data.pop("name", None),
                "lon": None,
                "lat": None,
            })
        self.stormname = self._insert_data["stormname"]
        self.cn_stormname = self._insert_data["cn_stormname"]
        self._points = typhoon.get("points")
        self._insert_data["begin_time"] = time_CST2UTC(str(typhoon.get('begin_time')).replace("T", ' ')) # 实时数据
        self._insert_data["realtime_data"] = []  # 实时数据
        self._insert_data["forecast_data"] = {}  # 预测数据
        self._forecast_sources = []
        self.handle_real_time()
        

    def handle_real_time(self):
        for point in self._points:
            new_point = {}
            for k,v in point.items():
                if v is not None:
                    new_point[k] = v
                    if isinstance(v, dict):
                        new_sub = {}
                        for sk,sv in v.items():
                            if sv is not None:
                                new_sub[sk] = sv
                        new_point[k] = new_sub

            point = new_point
            end_time = time_CST2UTC(str(point.pop("time").replace("T", ' ')))
            # print(f">>> 当前时间是 {end_time}")
            point.update({
                "lon": point.pop("lng"),
                "reporttime": end_time,
                "minp": point.get('pressure',0),
                "maxsp": round(float(point.get("speed",0))/COEFFICIENT_KT_MS,0),  # 最大速度18
                "speed": round(float(point.get('move_speed',0))/COEFFICIENT_KT_MS,0),   # 移动速度8公里/h
                "direction": point.get('move_dir',0),

                "radius34": round(float(point.get('radius7',0))/NAUTICAL_MILE_KM,2),
                "radius50": round(float(point.get('radius10',0))/NAUTICAL_MILE_KM,2),
                "radius64": round(float(point.get('radius12',0))/NAUTICAL_MILE_KM,2),

                "r34_ne": round(float(point.get('radius7_quad',{}).get('ne',0))/NAUTICAL_MILE_KM,2),
                "r34_se": round(float(point.get('radius7_quad',{}).get('se',0))/NAUTICAL_MILE_KM,2),
                "r34_sw": round(float(point.get('radius7_quad',{}).get('sw',0))/NAUTICAL_MILE_KM,2),
                "r34_nw": round(float(point.get('radius7_quad',{}).get('nw',0))/NAUTICAL_MILE_KM,2),
                "r50_ne": round(float(point.get('radius10_quad',{}).get('ne',0))/NAUTICAL_MILE_KM,2),
                "r50_se": round(float(point.get('radius10_quad',{}).get('se',0))/NAUTICAL_MILE_KM,2),
                "r50_sw": round(float(point.get('radius10_quad',{}).get('sw',0))/NAUTICAL_MILE_KM,2),
                "r50_nw": round(float(point.get('radius10_quad',{}).get('nw',0))/NAUTICAL_MILE_KM,2),
                "r64_ne": round(float(point.get('radius12_quad',{}).get('ne',0))/NAUTICAL_MILE_KM,2),
                "r64_se": round(float(point.get('radius12_quad',{}).get('se',0))/NAUTICAL_MILE_KM,2),
                "r64_sw": round(float(point.get('radius12_quad',{}).get('sw',0))/NAUTICAL_MILE_KM,2),
                "r64_nw": round(float(point.get('radius12_quad',{}).get('nw',0))/NAUTICAL_MILE_KM,2),
            })
            point.pop("move_speed", None)
            point.pop("move_dir", None)
            point.pop("radius7", None)
            point.pop("radius10", None)
            point.pop("radius12", None)
            point.pop("radius7_quad", None)
            point.pop("radius10_quad", None)
            point.pop("radius12_quad", None)
            if point.get("forecast"):
                self.handle_forecast_data(point["reporttime"],point["forecast"])
                self._newest_report_time = point["reporttime"]
                self._insert_data.update({"newest_report_time":self._newest_report_time})
            
            point.pop("forecast",None)
            self._insert_data['lon']=point["lon"]
            self._insert_data['lat']=point["lat"]
            self._insert_data['end_time']=end_time
            self._insert_data["realtime_data"].append(point)

    def handle_forecast_data(self, reporttime, forecasts):
        for forecast in forecasts:
            source, points = forecast['sets'],forecast['points']
            self._forecast_sources.append(source)
            new_points = []
            for point in points:
                new_point = {}
                for k,v in point.items():
                    if v is not None:
                        new_point[k] = v
                        if isinstance(v, dict):
                            new_sub = {}
                            for sk,sv in v.items():
                                if sv is not None:
                                    new_sub[sk] = sv
                            new_point[k] = new_sub

                point = new_point
                point.update({
                    "lon": point.pop("lng"),
                    "minp": point.get('pressure',0),
                    "maxsp": round(float(point.get("speed",0))/COEFFICIENT_KT_MS,0),
                    "speed": round(float(point.get('move_speed',0))/COEFFICIENT_KT_MS,0),
                    "direction": point.get('move_dir',0),
                    "radius34": round(float(point.get('radius7',0))/NAUTICAL_MILE_KM,2),
                    "radius50": round(float(point.get('radius10',0))/NAUTICAL_MILE_KM,2),
                    "forecast_time": time_CST2UTC(str(point.pop("time").replace("T", ' ')))
                    })
                point.pop("radius7", None)
                point.pop("radius10", None)
                point.pop("move_speed", None)
                point.pop("move_dir", None)
                new_points.append(point)
            self._insert_data["forecast_data"].setdefault(source, {}).setdefault(reporttime, new_points)


    def query_wz_exist(self):
        query = {"stormid": self._insert_data["stormid"]}
        res = self._mgo.mgo_coll.find_one(query, {"realtime_data": 0, "forecast_data":0,"points":0,"land":0})
        return res

    def update_real_time_mgo(self, wz_id):
        for point in self._insert_data["realtime_data"]:
            aggregate_query = [{
                "$unwind": "$realtime_data"
            }, {
                "$match": {
                    "_id": wz_id,
                    "realtime_data.reporttime": point['reporttime'],
                }
            }, {
                "$project": {
                    "realtime_data": 1,
                    "end_time":1
                }
            }]
            res = list(self._mgo.mgo_coll.aggregate(aggregate_query))

            if res:
                # logging.info("实测-已有该时刻数据....")
                r = self._mgo.mgo_coll.update_one(
                    {
                        "_id": wz_id,
                        "realtime_data.reporttime": point['reporttime']
                    }, {
                        "$set": {
                            "realtime_data.$.lat": point.get('lat'),
                            "realtime_data.$.lon": point.get('lon'),
                            "realtime_data.$.strong": point.get('strong'),
                            "realtime_data.$.power": point.get('power'),
                            "realtime_data.$.speed": point.get('speed'),
                            "realtime_data.$.direction": point.get('direction'),
                            "realtime_data.$.maxsp": point.get('maxsp'),
                            "realtime_data.$.minp": point.get('minp'),
                            "realtime_data.$.radius34": point.get('radius34'),
                            "realtime_data.$.radius50": point.get('radius50'),
                            "realtime_data.$.radius64": point.get('radius64'),
                            "realtime_data.$.r34_ne": point.get("r34_ne"),
                            "realtime_data.$.r34_se": point.get("r34_se"),
                            "realtime_data.$.r34_sw": point.get("r34_sw"),
                            "realtime_data.$.r34_nw": point.get("r34_nw"),
                            "realtime_data.$.r50_ne": point.get("r50_ne"),
                            "realtime_data.$.r50_se": point.get("r50_se"),
                            "realtime_data.$.r50_sw": point.get("r50_sw"),
                            "realtime_data.$.r50_nw": point.get("r50_nw"),
                            "realtime_data.$.r64_ne": point.get("r64_ne"),
                            "realtime_data.$.r64_se": point.get("r64_se"),
                            "realtime_data.$.r64_sw": point.get("r64_sw"),
                            "realtime_data.$.r64_nw": point.get("r64_nw"),
                            "realtime_data.$.remark": point.get('remark'),
                        }
                    },
                    upsert=True)
            else:
                r = self._mgo.mgo_coll.update({
                    "_id": wz_id,
                }, {
                    "$set": {
                        "stormname": self.stormname,
                        "cn_stormname": self.cn_stormname,
                        "begin_time": self._insert_data["begin_time"],
                        "end_time": point['reporttime'],
                        "lat": point.get('lat'),
                        "lon": point.get('lon'),
                    },
                    "$push": {
                        "realtime_data": point
                    }
                })
                print("wztfw实测-嵌套新增成功: ", r)

    def update_forecast_mgo(self,wz_id):
        for source, reporttime_points in self._insert_data["forecast_data"].items():
            for reporttime, points in reporttime_points.items():
                for point in points:
                    aggregate_query = [{
                        "$unwind": f"$forecast_data.{source}.{reporttime}"
                    }, {
                        "$match": {
                            "_id": wz_id,
                            f"forecast_data.{source}.{reporttime}.forecast_time": point['forecast_time'],
                        }
                    }, {
                        "$project": {
                            "_id":1
                        }
                    }]
                    res = list(self._mgo.mgo_coll.aggregate(aggregate_query))

                    if res:
                        # logging.info("预测-已有该时刻数据...")
                        r = self._mgo.mgo_coll.update_one(
                            {
                                "_id": wz_id,
                                f"forecast_data.{source}.{reporttime}.forecast_time": point['forecast_time']
                            }, {
                                "$set": {
                                    "newest_report_time": self._newest_report_time,
                                    f"forecast_data.{source}.{reporttime}.$.lat": point.get('lat'),
                                    f"forecast_data.{source}.{reporttime}.$.lon": point.get('lon'),
                                    f"forecast_data.{source}.{reporttime}.$.strong": point.get('strong'),
                                    f"forecast_data.{source}.{reporttime}.$.power": point.get('power'),
                                    f"forecast_data.{source}.{reporttime}.$.speed": point.get('speed'),
                                    f"forecast_data.{source}.{reporttime}.$.direction": point.get('direction'),
                                    f"forecast_data.{source}.{reporttime}.$.maxsp": point.get('maxsp'),
                                    f"forecast_data.{source}.{reporttime}.$.minp": point.get('minp'),
                                    f"forecast_data.{source}.{reporttime}.$.radius34": point.get('radius34'),
                                    f"forecast_data.{source}.{reporttime}.$.radius50": point.get('radius50'),
                                    f"forecast_data.{source}.{reporttime}.$.remark": point.get('remark'),
                                }
                            },
                            upsert=True)
                    else:
                        r = self._mgo.mgo_coll.update({
                            "_id": wz_id,
                        }, {
                            "$set": {
                                "forecast_sources": self._forecast_sources,
                                "newest_report_time": self._newest_report_time,
                                # "end_time": point['forecast_time'],
                                # "lat": point.get('lat'),
                                # "lon": point.get('lon'),
                            },
                            "$push": {
                                f"forecast_data.{source}.{reporttime}": point
                            }
                        })
                        print("预测-嵌套新增成功: ", r)


    def save_mgo(self):
        '''如果数据库没有该条数据，则增加该条数据'''
        self._insert_data.pop("points", None)
        self._insert_data["forecast_sources"] = self._forecast_sources
        self._mgo.set(None, self._insert_data)