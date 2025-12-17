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


class UpdateMmsi(BaseModel):
    """更新干散货和杂货船的MMSI，判断是否已更新为最新的"""

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
        super(UpdateMmsi, self).__init__(config)

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

    def _get_vessel_detail_by_mmsi(self, mmsi):
        """通过MMSI调用cosco接口获取船舶档案详情"""
        try:
            url = f"http://8.153.76.2:10010/api/cosco/vessel/detail?mmsi={mmsi}"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            
            # 从返回数据中提取档案数据
            data = res_json.get("data")
            if data and isinstance(data, dict):
                return data
            return None
        except requests.exceptions.RequestException as e:
            print(f"调用cosco接口获取船舶档案异常 (mmsi: {mmsi}): {e}")
            return None
        except Exception as e:
            print(f"解析cosco接口返回异常 (mmsi: {mmsi}): {e}")
            return None

    def _update_vessel_profile(self, imo, mmsi, vessel_data, previous_mmsi=None):
        """更新船舶档案数据
        Args:
            imo: IMO号
            mmsi: MMSI号（新的）
            vessel_data: 从接口获取的船舶档案数据
            previous_mmsi: 前一个MMSI号（可选）
        Returns:
            bool: 是否更新成功
        """
        try:
            if not vessel_data:
                return False
            
            # 标准化返回数据中的IMO和MMSI
            vessel_imo_raw = vessel_data.get("imo")
            vessel_mmsi_raw = vessel_data.get("mmsi") or vessel_data.get("vesselMmsi")
            
            # 如果返回数据中有IMO，验证是否匹配
            if vessel_imo_raw:
                vessel_imo_normalized = self._normalize_int_field(vessel_imo_raw, "vessel_imo")
                # 如果返回的IMO有效且与传入的IMO不匹配，则跳过
                if vessel_imo_normalized and vessel_imo_normalized > 0 and vessel_imo_normalized != imo:
                    print(f"  ⚠ IMO不匹配，跳过更新 - 期望IMO: {imo}, 返回IMO: {vessel_imo_normalized}")
                    return False
            
            # 标准化MMSI
            mmsi_normalized = self._normalize_int_field(vessel_mmsi_raw or mmsi, "mmsi")
            if not mmsi_normalized or mmsi_normalized <= 0:
                print(f"  ⚠ MMSI无效，跳过更新 - mmsi: {mmsi}")
                return False
            
            # 构建更新数据
            update_data = dict(vessel_data)
            
            # 确保关键字段为正确的类型
            # IMO使用传入的值（已验证匹配）
            update_data["imo"] = imo
            # MMSI使用标准化后的值
            update_data["mmsi"] = mmsi_normalized
            
            # 字段映射
            if "grt" in vessel_data and vessel_data["grt"] is not None:
                update_data["GrossTonnage"] = str(vessel_data["grt"])
            if "dwt" in vessel_data and vessel_data["dwt"] is not None:
                update_data["dwt"] = str(vessel_data["dwt"])
            if "buildYear" in vessel_data and vessel_data["buildYear"] is not None:
                update_data["YearOfBuild"] = str(vessel_data["buildYear"])
            if "draught" in vessel_data and vessel_data["draught"] is not None:
                update_data["sjdraught"] = str(vessel_data["draught"])
            
            # 添加更新时间标记
            current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_data["info_update"] = current_time_str
            # 记录前一个MMSI号码
            if previous_mmsi:
                update_data["info_update_desc"] = f"已获取到详情（MMSI更新后：{previous_mmsi} -> {mmsi_normalized}）"
            else:
                update_data["info_update_desc"] = f"已获取到详情（MMSI更新后：{mmsi_normalized}）"
            
            # 更新数据库
            self.mgo_db["global_vessels"].update_one(
                {"imo": imo},
                {"$set": update_data},
                upsert=False  # 不创建新记录，只更新已存在的
            )
            
            return True
        except Exception as e:
            print(f"更新船舶档案数据异常 (imo: {imo}, mmsi: {mmsi}): {e}")
            traceback.print_exc()
            return False

    def _get_latest_mmsi_by_imo(self, imo):
        """通过IMO调用cosco接口获取最新的MMSI"""
        try:
            # 标准化传入的IMO，确保比较时一致
            imo_normalized = self._normalize_int_field(imo, "imo")
            if imo_normalized is None or imo_normalized <= 0:
                print(f"IMO格式异常: {imo}")
                return None
            
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
                # 首先过滤掉IMO不匹配的结果
                matched_items = []
                for item in data_list:
                    item_imo = item.get("imo")
                    if item_imo:
                        # 标准化返回结果中的IMO
                        item_imo_normalized = self._normalize_int_field(item_imo, "item_imo")
                        # 只保留IMO匹配的项
                        if item_imo_normalized == imo_normalized:
                            matched_items.append(item)
                
                if not matched_items:
                    print(f"未找到IMO匹配的结果 - 查询IMO: {imo}, 返回结果数: {len(data_list)}")
                    return None
                
                # 如果有多个匹配结果，选择postime最大的（最新的）
                best_item = None
                best_postime = None
                
                for item in matched_items:
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

    def check_and_update_mmsi(self, imo_mmsi_list):
        """检查并更新MMSI
        Args:
            imo_mmsi_list: list, 包含 (imo, mmsi) 元组的列表
        Returns:
            dict: 统计信息 {"updated": int, "no_change": int, "error": int}
        """
        try:
            updated_count = 0
            no_change_count = 0
            error_count = 0
            total = len(imo_mmsi_list)
            current_time = datetime.datetime.now()
            current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            for idx, (imo, current_mmsi) in enumerate(imo_mmsi_list, 1):
                try:
                    # 每处理100条显示一次进度
                    if idx % 100 == 0 or idx == total:
                        print(f"  进度: {idx}/{total} ({idx*100//total}%)")
                    
                    # 通过imo获取最新mmsi
                    latest_mmsi = self._get_latest_mmsi_by_imo(imo)
                    
                    # 准备更新数据，无论是否更新MMSI，都要更新检查时间
                    update_data = {
                        "mmsi_check_time": current_time_str,
                        "mmsi_check_timestamp": current_time
                    }
                    
                    if latest_mmsi is None:
                        error_count += 1
                        # 即使获取失败，也记录检查时间
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": update_data}
                        )
                        if idx % 10 == 0:  # 每10条错误才打印一次，避免日志过多
                            print(f"  未获取到最新MMSI - imo: {imo}, 当前MMSI: {current_mmsi}")
                        continue
                    
                    # 判断是否需要更新
                    if latest_mmsi != current_mmsi:
                        # 更新数据库中的mmsi和检查时间
                        update_data.update({
                            "mmsi": latest_mmsi,
                            "info_update": current_time_str,
                            "info_update_desc": f"已更新MMSI: {current_mmsi} -> {latest_mmsi}"
                        })
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": update_data}
                        )
                        updated_count += 1
                        print(f"  ✓ 更新MMSI - imo: {imo}, 原MMSI: {current_mmsi}, 新MMSI: {latest_mmsi}")
                        
                        # MMSI更新后，立即获取新的船舶档案数据
                        try:
                            vessel_data = self._get_vessel_detail_by_mmsi(latest_mmsi)
                            if vessel_data:
                                profile_updated = self._update_vessel_profile(imo, latest_mmsi, vessel_data, previous_mmsi=current_mmsi)
                                if profile_updated:
                                    print(f"  ✓ 已更新船舶档案 - imo: {imo}, mmsi: {latest_mmsi}")
                                else:
                                    print(f"  ⚠ 更新船舶档案失败 - imo: {imo}, mmsi: {latest_mmsi}")
                            else:
                                print(f"  ⚠ 未获取到船舶档案数据 - imo: {imo}, mmsi: {latest_mmsi}")
                        except Exception as e:
                            print(f"  ✗ 获取船舶档案异常 - imo: {imo}, mmsi: {latest_mmsi}, 错误: {e}")
                    else:
                        # MMSI已是最新，只更新检查时间
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": update_data}
                        )
                        no_change_count += 1
                        # 只在调试模式下显示无需更新的信息，减少日志输出
                        # print(f"  ○ MMSI已是最新 - imo: {imo}, MMSI: {current_mmsi}")
                        
                except Exception as e:
                    print(f"  ✗ 处理异常 - imo: {imo}, 当前MMSI: {current_mmsi}, 错误: {e}")
                    error_count += 1
                    continue
            
            stats = {
                "updated": updated_count,
                "no_change": no_change_count,
                "error": error_count,
                "total": total
            }
            
            print(f"\n  本批次统计:")
            print(f"    已更新: {updated_count} 条")
            print(f"    无需更新: {no_change_count} 条")
            print(f"    处理异常: {error_count} 条")
            print(f"    总计: {total} 条")
            
            return stats
            
        except Exception as e:
            traceback.print_exc()
            print(f"检查并更新MMSI时发生错误: {e}")
            return {"updated": 0, "no_change": 0, "error": len(imo_mmsi_list), "total": len(imo_mmsi_list)}

    @decorate.exception_capture_close_datebase
    def run(self):
        """主执行方法"""
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("开始检查并更新干散货和杂货船的MMSI:", dataTime)
            
            # 计算30天前的时间
            days_threshold = 30
            threshold_time = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
            threshold_time_str = threshold_time.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"检查时间阈值: {threshold_time_str} (超过{days_threshold}天未检查的记录)")
            
            # 查询干散货和杂货船类型的记录
            # 条件：要么没有 mmsi_check_timestamp 字段，要么检查时间戳超过30天
            query = {
                "type": {"$in": ["散货船"]},
                "imo": {"$exists": True, "$ne": None, "$gt": 0},  # imo 必须存在且大于0
                "mmsi": {"$exists": True, "$ne": None},  # 确保有mmsi字段
                "$or": [
                    # 从未检查过（timestamp字段不存在）
                    {"mmsi_check_timestamp": {"$exists": False}},
                    # 检查时间戳超过30天
                    {"mmsi_check_timestamp": {"$lt": threshold_time}}
                ]
            }
            
            # 获取需要检查的记录
            need_check_list = list(self.mgo_db["global_vessels"].find(
                query,
                {"_id": 0, "imo": 1, "mmsi": 1, "mmsi_check_time": 1}
            ))
            
            print(f"找到需要检查的记录数: {len(need_check_list)}")
            
            if not need_check_list:
                print("没有需要检查的记录，任务结束")
                return
            
            # 过滤掉无效的 imo 和 mmsi，以 imo 为唯一键去重
            valid_imo_mmsi_list = []  # 包含 (imo, mmsi) 元组的列表
            seen_imo = set()  # 用于去重，确保每个 imo 只处理一次
            for item in need_check_list:
                imo = self._normalize_int_field(item.get("imo"), "imo")
                mmsi = self._normalize_int_field(item.get("mmsi"), "mmsi")
                # 排除异常数据：imo 必须大于0，且每个 imo 只处理一次
                if imo is not None and imo > 0 and mmsi is not None and imo not in seen_imo:
                    valid_imo_mmsi_list.append((imo, mmsi))
                    seen_imo.add(imo)
            
            if not valid_imo_mmsi_list:
                print("没有有效的IMO和MMSI，任务结束")
                return
            
            print(f"有效的记录数量: {len(valid_imo_mmsi_list)}")
            
            # 按批次处理
            batch_size = self.batch_size
            batches = [valid_imo_mmsi_list[i:i + batch_size]
                      for i in range(0, len(valid_imo_mmsi_list), batch_size)]
            
            total_batches = len(batches)
            total_stats = {"updated": 0, "no_change": 0, "error": 0, "total": 0}
            
            for idx, batch_list in enumerate(batches, 1):
                print(f"\n处理批次 {idx}/{total_batches}, 本批次数量: {len(batch_list)}")
                batch_stats = self.check_and_update_mmsi(batch_list)
                
                # 累计统计信息
                if batch_stats:
                    total_stats["updated"] += batch_stats.get("updated", 0)
                    total_stats["no_change"] += batch_stats.get("no_change", 0)
                    total_stats["error"] += batch_stats.get("error", 0)
                    total_stats["total"] += batch_stats.get("total", 0)
                
                # 最后一个批次不需要等待
                if idx < total_batches:
                    print(f"等待 {self.time_sleep_seconds} 秒后处理下一批次...")
                    time.sleep(self.time_sleep_seconds)
            
            print(f"\n{'='*60}")
            print(f"任务完成 - 总体统计:")
            print(f"  已更新: {total_stats['updated']} 条")
            print(f"  无需更新: {total_stats['no_change']} 条")
            print(f"  处理异常: {total_stats['error']} 条")
            print(f"  总计: {total_stats['total']} 条")
            print(f"{'='*60}")
            
        except Exception as e:
            traceback.print_exc()
            print(f"执行任务时发生错误: {e}")

