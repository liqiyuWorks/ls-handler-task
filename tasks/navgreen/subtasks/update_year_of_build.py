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
    """通过档案查询接口丰富散货船和杂货船的详细数据"""

    def __init__(self):
        self.batch_size = int(os.getenv('BATCH_SIZE', 1000))
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', 20))
        self.api_key = os.getenv('API_KEY', "266102ea-ca32-4ad8-8292-17c952a81a56")
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
        """构建更新数据，丰富所有详细字段"""
        # 标准化 imo 和 mmsi
        imo = self._normalize_int_field(item.get("imo"), "imo")
        mmsi = self._normalize_int_field(item.get("mmsi"), "mmsi")
        
        # 排除异常数据：imo 不能为 None、0 或负数
        if imo is None or imo <= 0:
            return None, None, None
        
        if mmsi is None:
            return None, None, None
        
        # 复制所有字段作为更新数据
        update_data = dict(item)
        
        # 确保关键字段为正确的类型
        update_data["imo"] = imo
        update_data["mmsi"] = mmsi
        
        # 字段映射 - 将API返回的字段映射到数据库字段
        if "grt" in item and item["grt"] is not None:
            update_data["GrossTonnage"] = str(item["grt"])
        if "dwt" in item and item["dwt"] is not None:
            update_data["dwt"] = str(item["dwt"])
        if "buildYear" in item and item["buildYear"] is not None:
            build_year = str(item["buildYear"]).strip()
            # 只有当buildYear有效且不是******时才更新
            if build_year and build_year != "******":
                update_data["YearOfBuild"] = build_year
        if "draught" in item and item["draught"] is not None:
            update_data["sjdraught"] = str(item["draught"])
        
        # 添加更新时间标记
        update_data["info_update"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_data["info_update_desc"] = "已获取到详情（通过档案接口更新）"
        
        return imo, mmsi, update_data

    def update_vessel_details(self, mmsi_imo_map):
        """批量更新船舶详细数据（通过档案查询接口）
        Args:
            mmsi_imo_map: dict, key为mmsi(str)，value为imo(int)，用于跟踪mmsi和imo的对应关系
        """
        try:
            # 构建有效的MMSI列表
            mmsi_list = []
            for mmsi_str in mmsi_imo_map.keys():
                mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                if mmsi and mmsi > 0:
                    mmsi_list.append(mmsi)
            
            if not mmsi_list:
                print("没有有效的MMSI列表")
                return
            
            res = request_wmy_detail(mmsi_list)
            
            if not res:
                print("接口返回空，未获取到任何数据")
                # 标记未获取到数据的记录
                for mmsi_str, imo in mmsi_imo_map.items():
                    mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                    if mmsi:
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": {"info_update_desc": "未获取到详情"}}
                        )
                return
            
            print(f"接口返回数据条数: {len(res)}")
            
            returned_mmsi_set = set()
            updated_count = 0
            
            # 处理接口返回的数据
            for item in res:
                imo, mmsi, update_data = self._build_update_data(item)
                
                if imo is None or mmsi is None or not update_data:
                    continue
                
                # 验证返回的IMO是否在预期列表中
                expected_imo = mmsi_imo_map.get(str(mmsi))
                if expected_imo and imo != expected_imo:
                    print(f"⚠ IMO不匹配，跳过 - 期望IMO: {expected_imo}, 返回IMO: {imo}, MMSI: {mmsi}")
                    continue
                
                # 更新数据库（全量更新所有字段）
                self.mgo_db["global_vessels"].update_one(
                    {"imo": imo},
                    {"$set": update_data},
                    upsert=False  # 不创建新记录，只更新已存在的
                )
                updated_count += 1
                
                # 输出更新信息
                year_of_build = update_data.get("YearOfBuild", "未更新")
                print(f"更新成功 - imo: {imo}, mmsi: {mmsi}, YearOfBuild: {year_of_build}")
                
                returned_mmsi_set.add(mmsi)
            
            # 记录未返回数据的MMSI
            missing_count = 0
            for mmsi_str in mmsi_imo_map.keys():
                mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                if mmsi and mmsi not in returned_mmsi_set:
                    imo = mmsi_imo_map.get(mmsi_str)
                    if imo:
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": {"info_update_desc": "未获取到详情"}}
                        )
                        missing_count += 1
            
            if missing_count > 0:
                print(f"未获取到数据的记录数: {missing_count}")
            
            print(f"本次批量更新成功: {updated_count} 条记录")
            
        except Exception as e:
            traceback.print_exc()
            print(f"更新船舶详细数据时发生错误: {e}")

    @decorate.exception_capture_close_datebase
    def run(self):
        """主执行方法"""
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("开始通过档案接口丰富散货船和杂货船的详细数据:", dataTime)
            print("筛选条件: 船型=散货船/杂货船")
            
            # 全量查询散货船和杂货船
            query = {
                "imo": {"$exists": True, "$ne": None, "$gt": 0},  # imo 必须存在且大于0
                "mmsi": {"$exists": True, "$ne": None, "$gt": 0},  # mmsi 必须存在且大于0
                "type": {"$in": ["散货船", "杂货船"]}  # 只查询散货船和杂货船类型
            }
            
            # 获取需要更新的记录（以 imo 为唯一键）
            need_update_list = list(self.mgo_db["global_vessels"].find(
                query,
                {"_id": 0, "imo": 1, "mmsi": 1}
            ))
            
            print(f"找到需要更新的记录数: {len(need_update_list)}")
            
            if not need_update_list:
                print("没有需要更新的记录，任务结束")
                return
            
            # 过滤掉无效的 imo 和 mmsi，以 imo 为唯一键去重，建立mmsi和imo的映射关系
            valid_mmsi_imo_map = {}  # key为mmsi(str)，value为imo(int)
            seen_imo = set()  # 用于去重，确保每个 imo 只处理一次
            for item in need_update_list:
                imo = self._normalize_int_field(item.get("imo"), "imo")
                mmsi = self._normalize_int_field(item.get("mmsi"), "mmsi")
                # 排除异常数据：imo 必须大于0，且每个 imo 只处理一次
                if imo is not None and imo > 0 and mmsi is not None and imo not in seen_imo:
                    valid_mmsi_imo_map[str(mmsi)] = imo
                    seen_imo.add(imo)
            
            if not valid_mmsi_imo_map:
                print("没有有效的MMSI，任务结束")
                return
            
            print(f"有效的MMSI数量: {len(valid_mmsi_imo_map)}")
            
            # 按批次处理
            batch_size = self.batch_size
            mmsi_list = list(valid_mmsi_imo_map.keys())
            batches = [mmsi_list[i:i + batch_size]
                      for i in range(0, len(mmsi_list), batch_size)]
            
            total_batches = len(batches)
            for idx, batch_mmsi_list in enumerate(batches, 1):
                print(f"\n处理批次 {idx}/{total_batches}, 本批次数量: {len(batch_mmsi_list)}")
                # 构建当前批次的mmsi-imo映射
                batch_mmsi_imo_map = {mmsi: valid_mmsi_imo_map[mmsi] for mmsi in batch_mmsi_list}
                self.update_vessel_details(batch_mmsi_imo_map)
                
                # 最后一个批次不需要等待
                if idx < total_batches:
                    print(f"等待 {self.time_sleep_seconds} 秒后处理下一批次...")
                    time.sleep(self.time_sleep_seconds)
            
            print("\n更新YearOfBuild字段任务完成!")
            
        except Exception as e:
            traceback.print_exc()
            print(f"执行任务时发生错误: {e}")

