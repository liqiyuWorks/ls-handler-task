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
from pymongo import UpdateOne


def request_wmy_detail(mmsi_list):
    import json
    url = "http://8.153.76.2:10010/api/cosco/vessel/details"
    payload = json.dumps({
        "mmsi_list": mmsi_list
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, headers=headers, data=payload)
    try:
        res_json = response.json()
        return res_json.get("data", [])
    except Exception:
        print("接口返回异常:", response.text)
        return []


class RichHifleetVesselsInfo(BaseModel):
    HIFLEET_VESSELS_LIST_URL = "https://www.hifleet.com/particulars/getShipDatav3"

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
        super(RichHifleetVesselsInfo, self).__init__(config)

    def update_hifleet_vessels(self, mmsi_list):
        try:
            res = request_wmy_detail(mmsi_list)
            if res is None:
                res = []

            print("接口返回数据条数:", len(res))
            if len(res) == 0:
                for m in mmsi_list:
                    try:
                        mmsi_int = int(m)
                    except Exception:
                        continue
                    info = self.mgo_db["global_vessels"].find_one(
                        {"mmsi": mmsi_int}, {"imo": 1, "mmsi": 1, "_id": 0})
                    missing_imo = info.get("imo") if info else None
                    print(f"接口全空: imo: {missing_imo}, mmsi: {mmsi_int}")
                    self.mgo_db["global_vessels"].update_one(
                        {"mmsi": mmsi_int},
                        {"$set": {"info_update_desc": "未获取到详情"}}
                    )
                return
            returned_mmsi_set = set()
            returned_imo_map = {}
            for item in res:
                # 强制 imo/mmsi 均为 int 类型
                imo_raw = item.get("imo")
                mmsi_raw = item.get("mmsi")
                if imo_raw is None or imo_raw == "" or mmsi_raw is None:
                    continue
                try:
                    imo = int(imo_raw)
                except Exception:
                    print(f"imo 字段格式异常: {imo_raw}")
                    continue
                try:
                    mmsi = int(mmsi_raw)
                except Exception:
                    print(f"mmsi 字段格式异常: {mmsi_raw}")
                    continue
                item["imo"] = imo
                item["mmsi"] = mmsi
                returned_mmsi_set.add(mmsi)
                returned_imo_map[mmsi] = imo
                # 字段映射梳理
                update_data = dict(item)
                if "grt" in item:
                    update_data["GrossTonnage"] = str(
                        item["grt"]) if item["grt"] is not None else ""
                if "dwt" in item:
                    update_data["dwt"] = str(
                        item["dwt"]) if item["dwt"] is not None else ""
                if "buildYear" in item:
                    update_data["YearOfBuild"] = str(
                        item["buildYear"]) if item["buildYear"] is not None else ""
                if "draught" in item:
                    update_data["sjdraught"] = str(
                        item["draught"]) if item["draught"] is not None else ""
                # 加入 info_update 字段（当前时间字符串）
                update_data["info_update"] = datetime.datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
                update_data["info_update_desc"] = "已获取到详情"
                # 全量同步并确保关键字段映射覆盖
                self.mgo_db["global_vessels"].update_one(
                    {"imo": imo},
                    {"$set": update_data},
                    upsert=True
                )
                print("同步数据 imo:", imo, "ok")
            # 记录未返回的数据
            missing_pairs = []
            for m in mmsi_list:
                try:
                    mmsi_int = int(m)
                except Exception:
                    continue
                if mmsi_int not in returned_mmsi_set:
                    info = self.mgo_db["global_vessels"].find_one(
                        {"mmsi": mmsi_int}, {"imo": 1, "mmsi": 1, "_id": 0})
                    missing_imo = info.get("imo") if info else None
                    missing_pairs.append((missing_imo, mmsi_int))
            if missing_pairs:
                print("未获取到数据:")
                for imo, mmsi in missing_pairs:
                    print(f"imo: {imo}, mmsi: {mmsi}")
                    # 库中增加 info_update_desc 字段标注
                    self.mgo_db["global_vessels"].update_one(
                        {"mmsi": mmsi},
                        {"$set": {"info_update_desc": "未获取到详情"}}
                    )
        except Exception:
            traceback.print_exc()
            print("res:", res)
            print("error in update_hifleet_vessels")

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
            print("同步开始:", dataTime)
            # 只依据信息更新时间 info_update 判定是否需要补数据

            def need_update(item):
                # ③ 有特殊标志“未获取到详情”则不更新
                if item.get("info_update_desc") == "未获取到详情":
                    return False
                # ① info_update 字段不存在
                if "info_update" not in item:
                    return True
                # ② info_update 距离现在大于3个月
                try:
                    last_update = datetime.datetime.strptime(
                        item["info_update"], "%Y-%m-%d %H:%M:%S")
                    if (datetime.datetime.now() - last_update).days > 90:
                        return True
                except Exception:
                    # 字段格式异常，也强制更新
                    return True
                return False

            # 1、查找全量船舶 ---- 【默认操作】
            ##  只补缺失/不完整字段/超时的数据，也可以全量同步（如需全量查 imo_list = ...）
            # existing_record_list = list(self.mgo_db["global_vessels"].find(
            #     {"imo": {"$exists": True}}, {"_id": 0}
            # ))
            
            # need_sync_list = [
            #     item for item in existing_record_list if need_update(item)]
            
            # 2、查找某一个imo补充数据
            # imo_list = [1082433]
            # for imo in imo_list:
            #     need_sync_list = list(self.mgo_db["global_vessels"].find(
            #         {"imo": imo}, {"_id": 0}
            #     ))
            
            # 3、查找info_update_desc为未获取到详情的船舶
            # need_sync_list = list(self.mgo_db["global_vessels"].find(
            #     {"imo": {"$exists": True}, "info_update_desc": "未获取到详情"}, {"_id": 0}
            # ))
            
            # 4. 补充指定的imo 船舶
            # need_sync_list = [{"imo": 9253997, "mmsi": 440351000}]

            print("库内总船数:", len(need_sync_list))

            # 按 imo 升序排序，确保need_sync_list顺序一致
            need_sync_list = sorted(
                need_sync_list, key=lambda x: x.get("imo", 0))
            mmsi_list = [item["mmsi"] for item in need_sync_list]
            print("需补字段船只数量:", len(mmsi_list))

            batch_size = self.batch_size
            batches = [mmsi_list[i:i + batch_size]
                       for i in range(0, len(mmsi_list), batch_size)]
            for batch in batches:
                print("请求 batch:", batch)
                self.update_hifleet_vessels(batch)
                time.sleep(self.time_sleep_seconds)
                # break
            print("同步结束!")
        except Exception:
            traceback.print_exc()
            print("error in run")


class ModifyVesselsInfoInMgo(BaseModel):

    def __init__(self):
        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'global_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING)
            ]
        }
        super(ModifyVesselsInfoInMgo, self).__init__(config)

    @decorate.exception_capture_close_datebase
    def run(self):
        try:
            import time as _t
            t1 = _t.time()
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("执行时间:", dataTime)
            # 1. 预读所有文档
            all_docs = list(self.mgo_db["global_vessels"].find({}))
            id_to_doc = {doc["_id"]: doc for doc in all_docs}
            imo_group = {}
            for doc in all_docs:
                imo_raw = doc.get("imo")
                if imo_raw is None:
                    continue
                try:
                    imo_int = int(imo_raw)
                except Exception:
                    continue
                if imo_int not in imo_group:
                    imo_group[imo_int] = []
                imo_group[imo_int].append(doc["_id"])
            # 2. 统计 & 分批处理
            to_delete_ids = []
            ops_update = []
            log_merge = 0
            log_deleted = 0

            def merge_docs(docs):
                result = {}
                for d in docs:
                    for k, v in d.items():
                        if v not in (None, "", []):
                            # 优先内容更丰富、最近
                            if k not in result or (hasattr(v, "__len__") and len(str(v)) > len(str(result[k]))):
                                result[k] = v
                            elif k in ("info_update", "updated_at"):
                                try:
                                    t1 = str(result.get(k, ""))
                                    t2 = str(v)
                                    if t2 > t1:
                                        result[k] = v
                                except:
                                    pass
                return result
            for imo, ids in imo_group.items():
                docs = [id_to_doc[_id] for _id in ids]
                int_docs = [d for d in docs if isinstance(d["imo"], int)]
                str_docs = [d for d in docs if not isinstance(d["imo"], int)]
                # 标准化，只保留 int imo
                if int_docs:
                    # 删除所有 string imo 类型的冗余文档
                    del_ids = [d["_id"] for d in str_docs]
                    if del_ids:
                        to_delete_ids.extend(del_ids)
                        log_deleted += len(del_ids)
                    if len(int_docs) > 1:
                        # 多条 int imo 文档，需要融合后只保留一条
                        merged = merge_docs(int_docs)
                        keep_id = int_docs[0]["_id"]
                        # 标记除第一条之外要删除的
                        del_int_ids = [d["_id"] for d in int_docs[1:]]
                        if del_int_ids:
                            to_delete_ids.extend(del_int_ids)
                            log_deleted += len(del_int_ids)
                        ops_update.append(UpdateOne({"_id": keep_id}, {
                                          "$set": merged}, upsert=True))
                        log_merge += 1
                else:
                    # 全是 string imo，只保留一条
                    if len(docs) > 1:
                        merged = merge_docs(docs)
                        keep_id = docs[0]["_id"]
                        del_str_ids = [d["_id"] for d in docs[1:]]
                        if del_str_ids:
                            to_delete_ids.extend(del_str_ids)
                            log_deleted += len(del_str_ids)
                        ops_update.append(UpdateOne({"_id": keep_id}, {
                                          "$set": merged}, upsert=True))
                        log_merge += 1
            # 3. 批量真正执行去重和合并
            if to_delete_ids:
                self.mgo_db["global_vessels"].delete_many(
                    {"_id": {"$in": to_delete_ids}})
            if ops_update:
                self.mgo_db["global_vessels"].bulk_write(ops_update)
            # 4. 保证所有剩余文档的 imo 和 mmsi 均为 int 类型（如有未转换的一并转换）
            update_to_int_ops = []
            cnt_convert = 0
            for doc in self.mgo_db["global_vessels"].find({}, {"_id": 1, "imo": 1, "mmsi": 1}):
                updates = {}
                imo_raw = doc.get("imo")
                mmsi_raw = doc.get("mmsi")
                if imo_raw is not None and not isinstance(imo_raw, int):
                    try:
                        updates["imo"] = int(imo_raw)
                    except Exception:
                        pass
                if mmsi_raw is not None and not isinstance(mmsi_raw, int):
                    try:
                        updates["mmsi"] = int(mmsi_raw)
                    except Exception:
                        pass
                if updates:
                    update_to_int_ops.append(
                        UpdateOne({"_id": doc["_id"]}, {"$set": updates}))
                    cnt_convert += 1
            if update_to_int_ops:
                self.mgo_db["global_vessels"].bulk_write(update_to_int_ops)
            print(
                f"批量已清理冗余: 合并{log_merge}组, 删除{log_deleted}条，仅保留 int imo 唯一文档。后处理 imo/mmsi 转 int 共 {cnt_convert} 条. 用时: {round(_t.time()-t1,2)}秒")
        except Exception:
            traceback.print_exc()
            print("error in run")
