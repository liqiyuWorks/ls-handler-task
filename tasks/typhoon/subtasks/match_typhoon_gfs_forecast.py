#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
from pkg.util.format import distance
import datetime
import pytz
import copy
import logging
import os

class MatchTyphoonGfsForecast(BaseModel):
    START_DELAY_DAY = int(os.getenv("START_DELAY_DAY",103))
    END_DELAY_DAY = int(os.getenv("END_DELAY_DAY",103))
    DEFAULT_MIN_DUP_DISTANCE = int(os.getenv("DEFAULT_MIN_DUP_DISTANCE",2))
    DEFAULT_MIN_FOR_DISTANCE = int(os.getenv("DEFAULT_MIN_FOR_DISTANCE",10))
    DEFAULT_MIN_HIS_DISTANCE = int(os.getenv("DEFAULT_MIN_HIS_DISTANCE",30))
    GFS_DELAY_DAYS = 1
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
                print("    >>>> realtime_data gfs_id update ok,res:",r.matched_count)
            elif realtimesource == "中国":
                r = self.mgo_db["wztfw_data"].update_one(
                        {
                            "_id": typhoon_id
                        }, {
                            "$set": {
                                "gfs_id": gfs_id,
                            }
                        },
                        upsert=True)
                print("    >>>> 温州台风网 gfs_id update ok,res:", r.matched_count)
        
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
                            diff =distance(i['realtime_data'][0]['lat'], i['realtime_data'][0]['lon'],
                                                      wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon'])
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
                    diff =distance(i['datatime'][0]['lat'], i['datatime'][0]['lon'],
                                              wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon'])
                    
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
                    diff =distance(i['datatime'][0]['lat'], i['datatime'][0]['lon'],
                                              wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon'])
                    
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
            print(ori_lon, ori_lat)
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
            end_reporttime = (datetime.datetime.strptime(end_reporttime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=self.GFS_DELAY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
            gfs_query = {"newest_report_time": {'$gte': start_reporttime, "$lte": end_reporttime}}
            # print(">>> gfs_query", gfs_query)
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
                        new_item['_id'] = gfs_id
                        new_item['stormid'] = first_reporttime_item['stormid']
                        new_item['basin'] = first_reporttime_item['basin']
                        diff = distance(ori_lon, ori_lat,first_reporttime_item['lon'], first_reporttime_item['lat'])
                        new_item['diff'] = diff
                        new_item['newest_report_time'] = newest_report_time
                        new_item["embedded"] = res
                        distance_calc_list.append(new_item)

                if distance_calc_list:
                    new_distance_calc_list = sorted(distance_calc_list, key=lambda x: x['diff'])
                    # print(new_distance_calc_list[0])
                    diff = new_distance_calc_list[0].get('diff')
                    gfs_stormid = new_distance_calc_list[0].get('stormid')
                    gfs_basin = new_distance_calc_list[0].get('basin')
                    match_gfs_id = new_distance_calc_list[0].get('_id')

                    if diff <= self.DEFAULT_MIN_FOR_DISTANCE:
                        print(f"  >> {typhoon_id}:{realtimesource}:{stormid}:{stormname} -> choose_gfs {gfs_stormid}:{gfs_basin} -> short_diff {diff} -> {match_gfs_id}")
                        self.update_gfs_id(realtimesource, typhoon_id, match_gfs_id)
    
    
    def query_history_typhoon(self):
        """查询台风历史数据"""
        # 同时查询三个数据源的时间区域台风
        gfs_realtime_query = {"datatime.reporttime": {'$gte': self.start_time, "$lte": self.end_time}}
        wz_realtime_query = {"realtime_data.reporttime": {'$gte': self.start_time, "$lte": self.end_time}}
        gfs_res, wztfw_res = [], []
        if self.mgo_db:
            gfs_res = self.mgo_db["gfs_realtime_data"].find(gfs_realtime_query)
            wztfw_res = self.mgo_db["wztfw_data"].find(wz_realtime_query)

        new_typhoon = []
        new_gfs_res = list(copy.deepcopy(gfs_res))

        # 匹配温州台风源数据
        for wz in wztfw_res:
            stormname = wz.get("stormname")
            if stormname != "TD":
                # 外循环gfs-去除GFS中与温州台风网相同的台风
                for i in gfs_res:
                    diff = distance(i['datatime'][0]['lat'], i['datatime'][0]['lon'],
                                              wz['realtime_data'][0]['lat'], wz['realtime_data'][0]['lon'])
                    if diff < self.DEFAULT_MIN_DUP_DISTANCE or i.get("stormname") == stormname:
                        wz["stormid"] = i["stormid"]
                        wz["year"] = i["year"]
                        new_gfs_res.remove(i)
                wz["realtimesource"] = "中国"
                new_typhoon.append(wz)

        # 匹配 gfs 实时数据
        for g in new_gfs_res:
            g["realtimesource"] = "gfs"
            new_typhoon.append(g)
        for i in new_typhoon:
            print(f">>> src={i['realtimesource']} , stormid = {i['stormid']}")
        return new_typhoon
    
    def query_history_forecast_typhoon(self, typhoons):
        """查询历史的预测数据"""
        for typhoon in typhoons:
            typhoon_id = typhoon.get("_id")
            realtimesource = typhoon.get("realtimesource", "gfs")  # 区分当前台风的来源
            baseInfo = {}
            stormid = typhoon.get('stormid')
            year = int(typhoon.get('year', 0))
            if not year:
                year = int(str(typhoon.get('stormid', ""))[:4])
            stormname = None
            
            # 定位 历史最近的 起报时间 curr_report_time ！！！
            curr_hour = int(self.date_time[11:13])
            pre_hour = curr_hour//6 * 6
            curr_report_time = self.date_time[:10]+f" {pre_hour:02d}:00:00"
            
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
            else:
                baseInfo['stormID'] = f"{year}{stormid}"
                stormname = typhoon.get('stormname')
                datatime = typhoon.get('datatime')
                start_reporttime = typhoon.get('start_reporttime')
                end_reporttime = typhoon.get('end_reporttime')
            
            if datatime == []:
                continue

            # 获取当前的最新的点
            ori_lon = datatime[-1].get("lon")
            ori_lat = datatime[-1].get("lat")

            # gfs 查询gfs符合时间段的所有的台风
            start_reporttime = (datetime.datetime.strptime(start_reporttime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=-self.GFS_DELAY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
            end_reporttime = (datetime.datetime.strptime(end_reporttime, "%Y-%m-%d %H:%M:%S") + datetime.timedelta(days=+self.GFS_DELAY_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
            gfs_query = {"newest_report_time": {'$gte': start_reporttime, "$lte": end_reporttime}}
            
            gfs_res = []
            if self.mgo_db:
                gfs_res = list(self.mgo_db["gfs_forecast_data"].find(gfs_query))
            distance_calc_list = []
            if gfs_res:
                for gfs in gfs_res:
                    newest_report_time = gfs.get('newest_report_time')
                    reporttime = gfs.get("reporttime")
                    gfs_id = gfs.get("_id")
                    if reporttime:
                        new_item = {}
                        first_reporttime_item = reporttime[newest_report_time][0]
                        new_item['_id'] = gfs_id
                        new_item['stormid'] = first_reporttime_item['stormid']
                        new_item['basin'] = first_reporttime_item['basin']
                        diff = distance(ori_lon, ori_lat, first_reporttime_item['lon'], first_reporttime_item['lat'])
                        new_item['diff'] = diff
                        new_item['newest_report_time'] = newest_report_time
                        # 获取所有的嵌入式文档中最符合的起报时间数据map
                        for k,v in reporttime.items():
                            if k > curr_report_time:
                                new_item["embedded"] = v
                                break
                        if not new_item.get("embedded"):
                            new_item["embedded"] = reporttime[newest_report_time]
                        distance_calc_list.append(new_item)

                if distance_calc_list:
                    new_distance_calc_list = sorted(distance_calc_list, key=lambda x: x['diff'])
                    diff = new_distance_calc_list[0].get('diff')
                    gfs_stormid = new_distance_calc_list[0].get('stormid')
                    gfs_basin = new_distance_calc_list[0].get('basin')
                    match_gfs_id = new_distance_calc_list[0].get('_id')

                    if diff <= self.DEFAULT_MIN_HIS_DISTANCE:
                        print(f"  >> {typhoon_id}:{realtimesource}:{stormid}:{stormname} -> choose_gfs {gfs_stormid}:{gfs_basin} -> short_diff {diff} -> {match_gfs_id}")
                        self.update_gfs_id(realtimesource, typhoon_id, match_gfs_id)
    
    @decorate.exception_capture_close_datebase
    def run(self):
        now = datetime.datetime.now(pytz.utc)
        self.start_time = (now + datetime.timedelta(days=-3)).strftime("%Y-%m-%d %H:%M:%S")
        self.end_time = (now + datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        self.date_time = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"> start_time={self.start_time}, end_time={self.end_time}, date_time={self.date_time}")
        typhoons = self.query_real_time_typhoon()
        self.query_forecast_typhoon(typhoons)
        
    @decorate.exception_capture_close_datebase
    def history(self):
        for day in reversed(range(self.START_DELAY_DAY, self.END_DELAY_DAY+1)):
            date_time = datetime.datetime.now(pytz.utc) + datetime.timedelta(days=-day)
            self.start_time = (date_time + datetime.timedelta(days=-2)).strftime("%Y-%m-%d 00:00:00")
            self.end_time = (date_time + datetime.timedelta(days=2)).strftime("%Y-%m-%d 00:00:00")
            self.date_time  = date_time.strftime("%Y-%m-%d 00:00:00")
            print(f"> 当前的delay_days={day}, start_time={self.start_time}, end_time={self.end_time}, history_date_time={self.date_time}")
            typhoons = self.query_history_typhoon()
            self.query_history_forecast_typhoon(typhoons)
            