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

    def _parse_postime(self, postime):
        """解析postime字段，转换为datetime对象用于比较
        例如: "2025-12-17 22:31:08" -> datetime对象
        """
        if not postime:
            return None
        
        try:
            # 解析时间字符串格式: "2025-12-17 22:31:08"
            time_str = str(postime).strip()
            if not time_str or time_str == "-" or time_str.lower() == "null":
                return None
            
            # 尝试解析时间字符串
            time_format = "%Y-%m-%d %H:%M:%S"
            return datetime.datetime.strptime(time_str, time_format)
        except ValueError:
            # 如果格式不匹配，尝试其他常见格式
            try:
                time_format = "%Y-%m-%d %H:%M:%S.%f"
                return datetime.datetime.strptime(time_str, time_format)
            except ValueError:
                print(f"无法解析postime格式 ({postime})")
                return None
        except Exception as e:
            print(f"解析postime异常 ({postime}): {e}")
            return None

    def _get_latest_mmsi_by_imo(self, imo):
        """通过IMO调用cosco接口获取最新的MMSI"""
        try:
            url = "http://8.153.76.2:10010/api/cosco/vessel/fuzzy"
            
            payload = json.dumps({
                "kw": str(imo),
                "search_gb": 1,
                "include_fish": False,
                "cascade_type": 0,
                "ignore_no_dynamics": False,
                "ignore_retired": False,
                "ignore_pinyin": False
            })
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            
            # 从返回数据中提取mmsi
            data_list = res_json.get("data", [])
            if data_list and isinstance(data_list, list) and len(data_list) > 0:
                # 如果有多个结果，选择postime最大的（最新的）
                best_item = None
                best_postime = None
                
                for item in data_list:
                    mmsi = item.get("mmsi") or item.get("vesselMmsi")
                    if not mmsi:
                        continue
                    
                    postime = item.get("postime")
                    postime_dt = self._parse_postime(postime)
                    
                    # 选择时间最大的（最新的）
                    if postime_dt is not None:
                        if best_postime is None or postime_dt > best_postime:
                            best_postime = postime_dt
                            best_item = item
                    elif best_postime is None:
                        # 如果当前项没有有效时间，但还没有找到任何有效时间的项，则使用它作为备选
                        best_item = item
                
                if best_item:
                    mmsi = best_item.get("mmsi") or best_item.get("vesselMmsi")
                    if mmsi:
                        mmsi = self._normalize_int_field(mmsi, "mmsi")
                        if mmsi and mmsi > 0:
                            return mmsi
            return None
        except requests.exceptions.RequestException as e:
            print(f"调用cosco接口获取MMSI异常 (imo: {imo}): {e}")
            return None
        except Exception as e:
            print(f"解析cosco接口返回异常 (imo: {imo}): {e}")
            return None

    def _build_update_data(self, item):
        """构建更新数据"""
        update_data = {}
        
        # 标准化 imo 和 mmsi
        imo = self._normalize_int_field(item.get("imo"), "imo")
        mmsi = self._normalize_int_field(item.get("mmsi"), "mmsi")
        
        # 排除异常数据：imo 不能为 None、0 或负数
        if imo is None or imo <= 0:
            return None, None, None
        
        if mmsi is None:
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

    def update_year_of_build(self, mmsi_imo_map):
        """批量更新YearOfBuild字段
        Args:
            mmsi_imo_map: dict, key为mmsi，value为imo，用于跟踪mmsi和imo的对应关系
        """
        try:
            mmsi_list = list(mmsi_imo_map.keys())
            res = request_wmy_detail(mmsi_list)
            
            if not res:
                # 接口返回空，尝试通过imo获取最新mmsi
                print("接口返回空，尝试通过IMO获取最新MMSI...")
                for mmsi_str, imo in mmsi_imo_map.items():
                    mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                    if mmsi is None or imo is None:
                        continue
                    
                    # 通过imo获取最新mmsi
                    latest_mmsi = self._get_latest_mmsi_by_imo(imo)
                    if latest_mmsi and latest_mmsi != mmsi:
                        print(f"通过IMO {imo} 获取到新MMSI: {latest_mmsi} (原MMSI: {mmsi})")
                        # 更新数据库中的mmsi
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": {"mmsi": latest_mmsi, "info_update_desc": f"已更新MMSI: {mmsi} -> {latest_mmsi}"}}
                        )
                        # 用新mmsi再次获取档案
                        new_res = request_wmy_detail([latest_mmsi])
                        if new_res:
                            for item in new_res:
                                item_imo, item_mmsi, update_data = self._build_update_data(item)
                                if item_imo == imo and item_mmsi == latest_mmsi and update_data and "YearOfBuild" in update_data:
                                    self.mgo_db["global_vessels"].update_one(
                                        {"imo": imo},
                                        {"$set": update_data}
                                    )
                                    print(f"使用新MMSI更新成功 - imo: {imo}, mmsi: {latest_mmsi}, YearOfBuild: {update_data.get('YearOfBuild')}")
                    else:
                        self.mgo_db["global_vessels"].update_one(
                            {"mmsi": mmsi},
                            {"$set": {"info_update_desc": "未获取到详情"}}
                        )
                        print(f"接口全空且未获取到新MMSI: mmsi: {mmsi}, imo: {imo}")
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
            
            # 记录未返回的数据，尝试通过imo获取最新mmsi
            missing_mmsi_list = []
            for mmsi_str in mmsi_list:
                mmsi = self._normalize_int_field(mmsi_str, "mmsi")
                if mmsi is None:
                    continue
                if mmsi not in returned_mmsi_set:
                    missing_mmsi_list.append(mmsi)
                    imo = mmsi_imo_map.get(mmsi_str)
                    
                    # 通过imo获取最新mmsi
                    latest_mmsi = self._get_latest_mmsi_by_imo(imo) if imo else None
                    if latest_mmsi and latest_mmsi != mmsi:
                        print(f"未获取到数据，通过IMO {imo} 获取到新MMSI: {latest_mmsi} (原MMSI: {mmsi})")
                        # 更新数据库中的mmsi
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": {"mmsi": latest_mmsi, "info_update_desc": f"已更新MMSI: {mmsi} -> {latest_mmsi}"}}
                        )
                        # 用新mmsi再次获取档案
                        new_res = request_wmy_detail([latest_mmsi])
                        if new_res:
                            for item in new_res:
                                item_imo, item_mmsi, update_data = self._build_update_data(item)
                                if item_imo == imo and item_mmsi == latest_mmsi and update_data and "YearOfBuild" in update_data:
                                    self.mgo_db["global_vessels"].update_one(
                                        {"imo": imo},
                                        {"$set": update_data}
                                    )
                                    print(f"使用新MMSI更新成功 - imo: {imo}, mmsi: {latest_mmsi}, YearOfBuild: {update_data.get('YearOfBuild')}")
                                    # 从missing列表中移除，因为已经成功更新
                                    if mmsi in missing_mmsi_list:
                                        missing_mmsi_list.remove(mmsi)
                        else:
                            self.mgo_db["global_vessels"].update_one(
                                {"imo": imo},
                                {"$set": {"info_update_desc": f"已更新MMSI但未获取到详情: {mmsi} -> {latest_mmsi}"}}
                            )
                    else:
                        self.mgo_db["global_vessels"].update_one(
                            {"mmsi": mmsi},
                            {"$set": {"info_update_desc": "未获取到详情"}}
                        )
            
            if missing_mmsi_list:
                print(f"最终未获取到数据的MMSI数量: {len(missing_mmsi_list)}")
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
            
            # 查询 YearOfBuild 为 ****** 的记录，以 imo 为唯一键，排除异常数据
            query = {
                "YearOfBuild": "******",
                "imo": {"$exists": True, "$ne": None, "$gt": 0},  # imo 必须存在且大于0
                "mmsi": {"$exists": True, "$ne": None},  # 确保有mmsi字段
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
                self.update_year_of_build(batch_mmsi_imo_map)
                
                # 最后一个批次不需要等待
                if idx < total_batches:
                    print(f"等待 {self.time_sleep_seconds} 秒后处理下一批次...")
                    time.sleep(self.time_sleep_seconds)
            
            print("\n更新YearOfBuild字段任务完成!")
            
        except Exception as e:
            traceback.print_exc()
            print(f"执行任务时发生错误: {e}")

