#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import pymongo
import requests
import datetime
from pkg.public.models import BaseModel
import traceback
import time
import os
import json


def request_wmy_detail(mmsi_list):
    """请求船视宝API获取船舶详情"""
    url = "http://8.153.76.2:10010/api/cosco/vessel/details"
    payload = json.dumps({
        "mmsi_list": mmsi_list
    })
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response.raise_for_status()
        res_json = response.json()
        return res_json.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"接口请求异常: {e}")
        return []
    except Exception as e:
        print(f"接口返回异常: {e}, 响应内容: {response.text if 'response' in locals() else 'N/A'}")
        return []


class UpdateYearOfBuild(BaseModel):
    """更新YearOfBuild字段为******的船舶记录"""

    def __init__(self):
        self.batch_size = int(os.getenv('BATCH_SIZE', 1000))
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', 20))
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'global_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING)
            ]
        }
        super(UpdateYearOfBuild, self).__init__(config)

    def _normalize_int_field(self, value, field_name):
        """标准化整数字段"""
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            print(f"{field_name} 字段格式异常: {value}")
            return None

    def _build_update_data(self, item):
        """构建更新数据"""
        update_data = {}
        
        # 标准化 imo 和 mmsi
        imo = self._normalize_int_field(item.get("imo"), "imo")
        mmsi = self._normalize_int_field(item.get("mmsi"), "mmsi")
        
        if imo is None or mmsi is None:
            return None, None, None
        
        # 字段映射 - 重点关注 YearOfBuild
        if "buildYear" in item and item["buildYear"] is not None:
            build_year = str(item["buildYear"]).strip()
            if build_year and build_year != "******":
                update_data["YearOfBuild"] = build_year
        
        # 同时更新其他相关字段（可选，保持数据完整性）
        if "grt" in item and item["grt"] is not None:
            update_data["GrossTonnage"] = str(item["grt"])
        if "dwt" in item and item["dwt"] is not None:
            update_data["dwt"] = str(item["dwt"])
        if "draught" in item and item["draught"] is not None:
            update_data["sjdraught"] = str(item["draught"])
        
        # 添加更新时间标记
        update_data["info_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_data["info_update_desc"] = "已更新YearOfBuild"
        
        return imo, mmsi, update_data

    def update_year_of_build(self, mmsi_list):
        """批量更新YearOfBuild字段"""
        try:
            res = request_wmy_detail(mmsi_list)
            
            if not res:
                # 接口返回空，标记未获取到详情
                for mmsi_str in mmsi_list:
                    mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                    if mmsi is None:
                        continue
                    self.mgo_db["global_vessels"].update_one(
                        {"mmsi": mmsi},
                        {"$set": {"info_update_desc": "未获取到详情"}}
                    )
                    print(f"接口全空: mmsi: {mmsi}")
                return
            
            print(f"接口返回数据条数: {len(res)}")
            
            returned_mmsi_set = set()
            updated_count = 0
            
            for item in res:
                imo, mmsi, update_data = self._build_update_data(item)
                
                if imo is None or mmsi is None or not update_data:
                    continue
                
                # 只更新 YearOfBuild 字段（如果API返回了有效的buildYear）
                if "YearOfBuild" in update_data:
                    self.mgo_db["global_vessels"].update_one(
                        {"imo": imo},
                        {"$set": update_data},
                        upsert=False  # 不创建新记录，只更新已存在的
                    )
                    updated_count += 1
                    print(f"更新成功 - imo: {imo}, mmsi: {mmsi}, YearOfBuild: {update_data.get('YearOfBuild')}")
                
                returned_mmsi_set.add(mmsi)
            
            # 记录未返回的数据
            missing_mmsi_list = []
            for mmsi_str in mmsi_list:
                mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                if mmsi is None:
                    continue
                if mmsi not in returned_mmsi_set:
                    missing_mmsi_list.append(mmsi)
                    self.mgo_db["global_vessels"].update_one(
                        {"mmsi": mmsi},
                        {"$set": {"info_update_desc": "未获取到详情"}}
                    )
            
            if missing_mmsi_list:
                print(f"未获取到数据的MMSI数量: {len(missing_mmsi_list)}")
                print(f"示例MMSI: {missing_mmsi_list[:10]}")
            
            print(f"本次批量更新成功: {updated_count} 条记录")
            
        except Exception as e:
            traceback.print_exc()
            print(f"更新YearOfBuild时发生错误: {e}")

    @decorate.exception_capture_close_datebase
    def run(self):
        """主执行方法"""
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("开始更新YearOfBuild字段:", dataTime)
            
            # 查询 YearOfBuild 为 ****** 的记录
            query = {
                "YearOfBuild": "******",
                "mmsi": {"$exists": True, "$ne": None}  # 确保有mmsi字段
            }
            
            # 获取需要更新的记录
            need_update_list = list(self.mgo_db["global_vessels"].find(
                query,
                {"_id": 0, "imo": 1, "mmsi": 1}
            ))
            
            print(f"找到需要更新的记录数: {len(need_update_list)}")
            
            if not need_update_list:
                print("没有需要更新的记录，任务结束")
                return
            
            # 过滤掉无效的mmsi
            valid_mmsi_list = []
            for item in need_update_list:
                mmsi = self._normalize_int_field(item.get("mmsi"), "mmsi")
                if mmsi is not None:
                    valid_mmsi_list.append(mmsi)
            
            if not valid_mmsi_list:
                print("没有有效的MMSI，任务结束")
                return
            
            print(f"有效的MMSI数量: {len(valid_mmsi_list)}")
            
            # 按批次处理
            batch_size = self.batch_size
            batches = [valid_mmsi_list[i:i + batch_size]
                      for i in range(0, len(valid_mmsi_list), batch_size)]
            
            total_batches = len(batches)
            for idx, batch in enumerate(batches, 1):
                print(f"\n处理批次 {idx}/{total_batches}, 本批次数量: {len(batch)}")
                self.update_year_of_build(batch)
                
                # 最后一个批次不需要等待
                if idx < total_batches:
                    print(f"等待 {self.time_sleep_seconds} 秒后处理下一批次...")
                    time.sleep(self.time_sleep_seconds)
            
            print("\n更新YearOfBuild字段任务完成!")
            
        except Exception as e:
            traceback.print_exc()
            print(f"执行任务时发生错误: {e}")

