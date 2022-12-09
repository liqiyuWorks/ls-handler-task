#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from scipy.spatial import distance
import datetime
import pytz
import copy
import logging

class MatchTyphoonGfsForecast(BaseModel):
    DEFAULT_MIN_DUP_DISTANCE = 2
    DEFAULT_MIN_FOR_DISTANCE = 10
    GFS_DELAY_DAYS = 3
    def __init__(self, config=None):
        config = {'handle_db': 'mgo'}
        super().__init__(config)
        
    def update_gfs_id(self, realtimesource, typhoon_id, gfs_id):
        if self.mgo_db:
            if realtimesource == "gfs":
                r = self.mgo_db["gfs_realtime_data"].update_one(
                        {
                            "_id": typhoon_id
                        }, {
                            "$set": {
                                "gfs_id": gfs_id,
                            }
                        },
                        upsert=True)
                print(">>>> realtime_data gfs_id update ok,res:",r.matched_count)
        
    def query_real_time_typhoon(self):
        new_typhoon = []
        gfs_realtime_query = {"datatime.reporttime": {'$gte': self.start_time, "$lte": self.end_time}}
        wz_realtime_query = {"realtime_data.reporttime": {'$gte': self.start_time, "$lte": self.end_time}}
        gfs_res,ssec_res,wztfw_res = [],[],[]
        if self.mgo_db:
            gfs_res = list(self.mgo_db["gfs_realtime_data"].find(gfs_realtime_query))
            ssec_res = list(self.mgo_db["ssec_realtime_data"].find(gfs_realtime_query))
            wztfw_res = list(self.mgo_db["wztfw_data"].find(wz_realtime_query))
        gfs_storm_list = [gfs.get("stormid") for gfs in gfs_res]  # 用于过滤 SSEC

        
        new_gfs_res = list(copy.deepcopy(gfs_res))
        # 匹配 ssec 源数据
        new_ssec = []
        for ssec in ssec_res:
            stormid = ssec.get("stormid")
            if stormid not in gfs_storm_list:
                ssec["realtimesource"] = "ssec"
                new_ssec.append(ssec)

        # 匹配 温州台风 源数据
        for wz in wztfw_res:
            stormname = wz.get("stormname")
            if stormname == "TD":
                # 内循环 - 去除 与台风 重复的TD， 有台风有TD
                for i in wztfw_res:
                    if i.get("stormname") != stormname:
                        try:
                            diff = distance.euclidean((i['realtime_data'][0]['lat'], i['realtime_data'][0]['lon']),
                                                      (wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon']))
                            if diff > self.DEFAULT_MIN_DUP_DISTANCE:
                                wz["realtimesource"] = "中国"
                                new_typhoon.append(wz)
                                print(f">> TD:WZTF append {stormname}")
                        except Exception as e:
                            logging.error(f"温州台风计算错误")
                            break
            else:
                # 外循环gfs - 去除GFS中与温州台风网相同的台风
                for i in gfs_res:
                    # print(f"i['stormid']={i['stormid']},i['stormname']={i['stormname']},stormname={stormname}")
                    diff = distance.euclidean((i['datatime'][0]['lat'], i['datatime'][0]['lon']),
                                              (wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon']))
                    
                    if i.get("stormname") == stormname:
                        wz["stormid"] = i["stormid"]
                        wz["year"] = i["year"]
                        new_gfs_res.remove(i)
                    else:
                        if diff < self.DEFAULT_MIN_DUP_DISTANCE:
                            wz["stormid"] = i["stormid"]
                            wz["year"] = i["year"]
                            new_gfs_res.remove(i)
                            
                for i in new_ssec:
                    diff = distance.euclidean((i['datatime'][0]['lat'], i['datatime'][0]['lon']),
                                              (wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon']))
                    
                    if i.get("stormname") == stormname:
                        wz["stormid"] = i["stormid"]
                        wz["year"] = i["year"]
                        new_ssec.remove(i)
                    else:
                        if diff < self.DEFAULT_MIN_DUP_DISTANCE:
                            wz["stormid"] = i["stormid"]
                            wz["year"] = i["year"]
                            new_ssec.remove(i)
                wz["realtimesource"] = "中国"
                new_typhoon.append(wz)
        wztfw_name = [tf.get("stormname") for tf in new_typhoon]

        for g in gfs_res:
            if g["stormname"] in wztfw_name:
                continue
            g["realtimesource"] = "gfs"
            new_typhoon.append(g)
            
        for s in new_ssec:
            s["realtimesource"] = "ssec"
            new_typhoon.append(s)
        for i in new_typhoon:
            print(f">> src={i['realtimesource']} , stormid = {i['stormid']}-{i.get('stormname')}")
        
        return new_typhoon
    
    def query_forecast_typhoon(self, typhoons):
        """根据gfs实时数据源去匹配"""
        for typhoon in typhoons:
            typhoon_id = typhoon.get("_id")
            realtimesource = typhoon.get("realtimesource", "gfs")  # 区分当前台风的来源
            baseInfo = {}
            # 获取 不同数据源的 相同变量 -> 统一
            stormid = typhoon.get('stormid')
            year = int(typhoon.get('year', 0))
            ori_lon = typhoon.get('lon')
            ori_lat = typhoon.get('lat')
            stormname = None
            if realtimesource == "中国":
                if len(stormid) > 4:
                    baseInfo['stormID'] = f"{stormid}"
                else:
                    baseInfo['stormID'] = f"{year}{stormid}"
                stormname = typhoon.get('stormname')
                datatime = typhoon.get('realtime_data')
                if datatime:
                    start_reporttime = datatime[0]['reporttime']
                    end_reporttime = datatime[-1].get('reporttime')
                else:
                    start_reporttime = typhoon.get['begin_time']
                    end_reporttime = typhoon.get('newest_report_time')
            elif realtimesource == "ssec":
                if len(stormid) > 4:
                    baseInfo['stormID'] = f"{stormid}"
                else:
                    baseInfo['stormID'] = f"{year}{stormid}"
                datatime = typhoon.get('datatime')
                start_reporttime = datatime[0]['reporttime']
                end_reporttime = typhoon.get('end_reporttime')
            else:
                baseInfo['stormID'] = f"{year}{stormid}"
                stormname = typhoon.get('stormname')
                datatime = typhoon.get('datatime')
                start_reporttime = typhoon.get('start_reporttime')
                end_reporttime = typhoon.get('end_reporttime')
            if not start_reporttime or not end_reporttime:
                print(f"start_reporttime & end_reporttime 缺失 -> pass")
                continue
            

            # gfs 查询gfs符合时间段的所有的台风
            start_reporttime = (datetime.datetime.strptime(start_reporttime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=-self.GFS_DELAY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
            gfs_query = {"newest_report_time": {'$gte': start_reporttime, "$lte": end_reporttime}}
            print(">>> gfs_query",gfs_query)
            if self.mgo_db:
                gfs_res = list(self.mgo_db["gfs_forecast_data"].find(gfs_query, {"reporttime": 0}))
            else:
                gfs_res = []
            distance_calc_list = []
            if gfs_res:
                for gfs in gfs_res:
                    gfs_id = gfs.get('_id')
                    newest_report_time = gfs.get("newest_report_time")
                    gfs_query = [
                        {
                            "$unwind": f"$reporttime.{newest_report_time}"
                        },
                        {"$sort": {f"reporttime.{newest_report_time}.forecast_time": 1}},
                        {
                            "$match": {
                                f"_id": gfs_id
                            }
                        },
                        {
                            "$project": {
                                "_id": 1,
                                "stormid": 1,
                                "basin": 1,
                                f"reporttime.{newest_report_time}": 1
                            }
                        }
                    ]
                    if self.mgo_db:
                        res = list(self.mgo_db["gfs_forecast_data"].aggregate(gfs_query))
                    else:
                        res = []
                    if res:
                        new_item = {}
                        first_reporttime_item = res[0]['reporttime'][newest_report_time]
                        new_item['stormid'] = first_reporttime_item['stormid']
                        new_item['basin'] = first_reporttime_item['basin']
                        diff = distance.euclidean((ori_lon, ori_lat),(first_reporttime_item['lon'], first_reporttime_item['lat']))
                        new_item['diff'] = diff
                        new_item['newest_report_time'] = newest_report_time
                        new_item["embedded"] = res
                        distance_calc_list.append(new_item)

                if distance_calc_list:
                    new_distance_calc_list = sorted(distance_calc_list, key=lambda x: x['diff'])
                    diff = new_distance_calc_list[0].get('diff')
                    gfs_stormid = new_distance_calc_list[0].get('stormid')
                    gfs_basin = new_distance_calc_list[0].get('basin')

                    if diff <= self.DEFAULT_MIN_FOR_DISTANCE:
                        print(f">>>> {typhoon_id}:{realtimesource}:{stormid}:{stormname} -> choose_gfs {gfs_stormid}:{gfs_basin} -> short_diff {diff} -> {gfs_id}")
                        self.update_gfs_id(realtimesource, typhoon_id, gfs_id)
    
    @decorate.exception_capture_close_datebase
    def run(self):
        now = datetime.datetime.now(pytz.utc)
        self.start_time = (now + datetime.timedelta(days=-3)).strftime("%Y-%m-%d %H:%M:%S")
        self.end_time = (now + datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        self.date_time = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"> start_time={self.start_time}, end_time={self.end_time}, date_time={self.date_time}")
        typhoons = self.query_real_time_typhoon()
        self.query_forecast_typhoon(typhoons)