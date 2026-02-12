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
        # 请求延迟配置（秒）
        self.request_delay_seconds = float(os.getenv('REQUEST_DELAY_SECONDS', 0.5))  # 默认0.5秒
        # 船舶类型配置，支持多个类型，用逗号分隔，例如："散货船,杂货船"
        vessel_types_env = os.getenv('VESSEL_TYPES', '杂货船')
        self.vessel_types = [t.strip() for t in vessel_types_env.split(',') if t.strip()]
        if not self.vessel_types:
            self.vessel_types = ['散货船']  # 如果环境变量为空，使用默认值
        # 可选：指定只更新某几个 IMO，逗号分隔，例如 IMO_LIST=9738521,9123456；不设则按类型+检查时间筛选
        self.specified_imos = None
        imo_list_env = os.getenv('IMO_LIST') or os.getenv('UPDATE_IMO_LIST', '').strip()
        if imo_list_env:
            specified = []
            for s in imo_list_env.split(','):
                s = s.strip()
                if not s:
                    continue
                try:
                    n = int(s)
                    if n > 0 and n not in specified:
                        specified.append(n)
                except ValueError:
                    pass
            if specified:
                self.specified_imos = specified
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

    def _parse_info_update(self, info_update):
        """解析详情接口返回的 info_update 等时间字段，用于比较哪个 MMSI 是当前在用"""
        if not info_update:
            return None
        return self._parse_postime(info_update)

    def _get_item_vessel_type(self, item):
        """从 fuzzy 接口返回的 item 中提取船舶类型（如 散、集、散货船 等）"""
        if not item or not isinstance(item, dict):
            return None
        for key in ('type', 'vesselType', 'shipType', 'typeName', 'typeNameCn'):
            val = item.get(key)
            if val is not None and str(val).strip():
                return str(val).strip()
        return None

    def _get_item_vessel_type_name_en(self, item):
        """从 item 中提取英文船型 vesselTypeNameEn（如 Container、Dry Bulk）"""
        if not item or not isinstance(item, dict):
            return None
        val = item.get('vesselTypeNameEn')
        if val is not None and str(val).strip():
            return str(val).strip()
        return None

    def _is_preferred_vessel_type_by_en(self, vessel_type_name_en):
        """根据 vesselTypeNameEn 判断是否优先：Dry Bulk 优先，Container 不优先。
        返回 True=优先(Dry Bulk)，False=不优先(Container)，None=未知则交给中文类型逻辑。
        """
        if not vessel_type_name_en:
            return None
        s = (vessel_type_name_en if isinstance(vessel_type_name_en, str) else str(vessel_type_name_en)).strip()
        if not s:
            return None
        lower = s.lower()
        if 'container' in lower or lower == 'container':
            return False
        if 'dry bulk' in lower or 'bulk carrier' in lower or lower == 'bulk':
            return True
        return None

    def _is_preferred_vessel_type(self, type_str):
        """判断是否为优先选择的船舶类型（散货船/杂货船等，与 self.vessel_types 一致）"""
        if not type_str:
            return False
        s = (type_str if isinstance(type_str, str) else str(type_str)).strip()
        if not s:
            return False
        # 与配置的类型完全匹配
        if s in self.vessel_types:
            return True
        # 界面常用简称：散 -> 散货船
        if s == '散' and any('散' in vt for vt in self.vessel_types):
            return True
        if s == '杂' and any('杂' in vt for vt in self.vessel_types):
            return True
        # 类型名包含配置中的关键字（如 "散货船" 包含 "散"）
        for vt in self.vessel_types:
            if vt in s or (len(vt) > 0 and vt[0] in s):
                return True
        return False

    def _get_vessel_detail_by_mmsi(self, mmsi):
        """通过MMSI调用cosco接口获取船舶档案详情"""
        try:
            # 请求前延迟
            if self.request_delay_seconds > 0:
                time.sleep(self.request_delay_seconds)
            
            url = f"http://47.84.73.224:10010/api/cosco/vessel/detail?mmsi={mmsi}"
            
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
            update_data["info_update_desc"] = "已获取到详情"
            # 单独记录MMSI变更信息
            if previous_mmsi:
                update_data["mmsi_update_info"] = f"MMSI更新：{previous_mmsi} -> {mmsi_normalized}"
            else:
                update_data["mmsi_update_info"] = f"MMSI更新：{mmsi_normalized}"
            
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

    def _get_latest_mmsi_by_imo(self, imo, current_mmsi=None):
        """通过 IMO 调用 cosco 接口获取最新的 MMSI。

        当同一 IMO 对应多个 MMSI（如旧号 441176000 与新号 677089700）时，仅用 fuzzy 的 postime 可能
        把已停用的旧 MMSI 误判为“最新”。因此对多个候选 MMSI 会再请求船舶详情接口，以详情返回的
        mmsi 为权威（canonical），并结合详情中的 info_update 与 fuzzy 的 postime 判断哪个是当前在用。
        """
        try:
            # 请求前延迟
            if self.request_delay_seconds > 0:
                time.sleep(self.request_delay_seconds)
            
            imo_normalized = self._normalize_int_field(imo, "imo")
            if imo_normalized is None or imo_normalized <= 0:
                print(f"IMO格式异常: {imo}")
                return None
            
            url = "http://47.84.73.224:10010/api/cosco/vessel/fuzzy"
            payload = json.dumps({
                "kw": str(imo),
                "search_gb": 1,
                "include_fish": False,
                "cascade_type": 0,
                "ignore_no_dynamics": False,
                "ignore_retired": False,
                "ignore_pinyin": False
            })
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            res_json = response.json()
            
            data_list = res_json.get("data", [])
            if not data_list or not isinstance(data_list, list) or len(data_list) == 0:
                return None
            
            matched_items = []
            for item in data_list:
                item_imo = item.get("imo")
                if not item_imo:
                    continue
                item_imo_n = self._normalize_int_field(item_imo, "item_imo")
                if item_imo_n == imo_normalized:
                    matched_items.append(item)
            
            if not matched_items:
                print(f"未找到IMO匹配的结果 - 查询IMO: {imo}, 返回结果数: {len(data_list)}")
                return None
            
            # 按 MMSI 聚合，每个 MMSI 保留其最大 postime 的项及对应的船舶类型、vesselTypeNameEn（用于后续优先选 Dry Bulk）
            mmsi_to_postime = {}
            mmsi_to_type = {}
            mmsi_to_type_name_en = {}
            for item in matched_items:
                mmsi_raw = item.get("mmsi") or item.get("vesselMmsi")
                if not mmsi_raw:
                    continue
                mmsi_n = self._normalize_int_field(mmsi_raw, "mmsi")
                if not mmsi_n or mmsi_n <= 0:
                    continue
                pt = self._parse_postime(item.get("postime"))
                item_type = self._get_item_vessel_type(item)
                item_type_en = self._get_item_vessel_type_name_en(item)
                if mmsi_n not in mmsi_to_postime or (pt and (mmsi_to_postime[mmsi_n] is None or pt > mmsi_to_postime[mmsi_n])):
                    mmsi_to_postime[mmsi_n] = pt
                    if item_type is not None:
                        mmsi_to_type[mmsi_n] = item_type
                    if item_type_en is not None:
                        mmsi_to_type_name_en[mmsi_n] = item_type_en
            
            distinct_mmsis = list(mmsi_to_postime.keys())
            if not distinct_mmsis:
                return None
            
            # 只有一个候选 MMSI：直接返回，不额外调详情
            if len(distinct_mmsis) == 1:
                return distinct_mmsis[0]
            
            # 多个候选 MMSI：用船舶详情接口判断哪个是“当前在用”（以详情返回的 mmsi 为权威）
            # 同时优先选择与配置类型一致的船舶（如散货船），同一 IMO 对应多船时选“散”不选“集”
            candidates = []  # (canonical_mmsi, detail_update_dt, postime_dt, is_preferred_type)
            for mmsi in distinct_mmsis:
                if self.request_delay_seconds > 0:
                    time.sleep(self.request_delay_seconds)
                detail = self._get_vessel_detail_by_mmsi(mmsi)
                # 优先用 vesselTypeNameEn 判断：Dry Bulk 优先，Container 不优先；否则用中文类型
                type_name_en = None
                if detail:
                    type_name_en = self._get_item_vessel_type_name_en(detail)
                if type_name_en is None:
                    type_name_en = mmsi_to_type_name_en.get(mmsi)
                prefer_by_en = self._is_preferred_vessel_type_by_en(type_name_en)
                if prefer_by_en is not None:
                    is_preferred = prefer_by_en
                else:
                    fuzzy_type = mmsi_to_type.get(mmsi)
                    if detail:
                        detail_type = self._get_item_vessel_type(detail)
                        type_for_prefer = detail_type or fuzzy_type
                    else:
                        type_for_prefer = fuzzy_type
                    is_preferred = self._is_preferred_vessel_type(type_for_prefer)
                if not detail:
                    candidates.append((mmsi, None, mmsi_to_postime.get(mmsi), is_preferred))
                    continue
                detail_imo_raw = detail.get("imo")
                if detail_imo_raw:
                    detail_imo_n = self._normalize_int_field(detail_imo_raw, "detail_imo")
                    if detail_imo_n and detail_imo_n != imo_normalized:
                        continue  # IMO 不一致，排除
                canonical_raw = detail.get("mmsi") or detail.get("vesselMmsi")
                canonical = self._normalize_int_field(canonical_raw or mmsi, "canonical_mmsi")
                if not canonical or canonical <= 0:
                    canonical = mmsi
                detail_update = self._parse_info_update(detail.get("info_update"))
                candidates.append((canonical, detail_update, mmsi_to_postime.get(mmsi), is_preferred))
            
            if not candidates:
                return None
            
            # 排序：先按是否为目标类型（如散货船）优先，再按详情更新时间、postime 倒序
            def sort_key(c):
                canon, d_update, post, is_pref = c
                return (
                    is_pref,
                    d_update is not None,
                    d_update or datetime.datetime.min,
                    post is not None,
                    post or datetime.datetime.min,
                )
            candidates.sort(key=sort_key, reverse=True)
            best_canonical = candidates[0][0]
            best_is_preferred = candidates[0][3]
            if len(distinct_mmsis) > 1 and current_mmsi is not None:
                msg = f"  [IMO {imo}] 多 MMSI 候选: {distinct_mmsis}, 当前库: {current_mmsi}, 选用: {best_canonical}"
                if best_is_preferred:
                    msg += " (优先目标类型如散货船)"
                print(msg)
            return best_canonical
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
                    
                    # 通过 imo 获取最新 mmsi（多候选时结合详情接口判断新旧，方法内部已包含延迟）
                    latest_mmsi = self._get_latest_mmsi_by_imo(imo, current_mmsi=current_mmsi)
                    
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
                        # 请求失败后也需要延迟
                        if self.request_delay_seconds > 0 and idx < total:
                            time.sleep(self.request_delay_seconds)
                        continue
                    
                    # 判断是否需要更新
                    if latest_mmsi != current_mmsi:
                        # 更新数据库中的mmsi和检查时间
                        update_data.update({
                            "mmsi": latest_mmsi,
                            "info_update": current_time_str,
                            "mmsi_update_info": f"MMSI更新：{current_mmsi} -> {latest_mmsi}"
                        })
                        self.mgo_db["global_vessels"].update_one(
                            {"imo": imo},
                            {"$set": update_data}
                        )
                        updated_count += 1
                        print(f"  ✓ 更新MMSI - imo: {imo}, 原MMSI: {current_mmsi}, 新MMSI: {latest_mmsi}")
                        
                        # MMSI更新后，立即获取新的船舶档案数据（方法内部已包含延迟）
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
                    
                    # 每个请求后额外延迟，防止请求过快
                    if self.request_delay_seconds > 0 and idx < total:
                        time.sleep(self.request_delay_seconds)
                        
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
            vessel_types_str = ', '.join(self.vessel_types)
            print(f"开始检查并更新{vessel_types_str}的MMSI:", dataTime)
            
            # 计算30天前的时间
            days_threshold = 30
            threshold_time = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
            threshold_time_str = threshold_time.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"检查时间阈值: {threshold_time_str} (超过{days_threshold}天未检查的记录)")
            print(f"船舶类型配置: {', '.join(self.vessel_types)}")
            
            if self.specified_imos:
                # 指定 IMO 模式：只更新环境变量 IMO_LIST 中的 IMO，不限制类型和检查时间
                query = {
                    "imo": {"$in": self.specified_imos},
                    "mmsi": {"$exists": True, "$ne": None}
                }
                print(f"指定 IMO 模式: 仅更新 IMO_LIST={self.specified_imos}")
            else:
                # 默认：按船舶类型 + 检查时间筛选
                query = {
                    "type": {"$in": self.vessel_types},
                    "imo": {"$exists": True, "$ne": None, "$gt": 0},
                    "mmsi": {"$exists": True, "$ne": None},
                    "$or": [
                        {"mmsi_check_timestamp": {"$exists": False}},
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

