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
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class SpiderHifleetNewbuildingVessels(BaseModel):
    """爬取 hifleet 新造船数据，仅关注干散货（散货船）和杂货船"""
    HIFLEET_VESSELS_LIST_URL = "https://www.hifleet.com/particulars/getShipDatav3"

    # 多个不同的 User-Agent 轮换使用
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    def __init__(self):
        # 可配置参数
        self.PAGE_START = int(os.getenv('PAGE_START', '1'))
        self.PAGE_END = int(os.getenv('PAGE_END', '10'))  # 默认最多10页
        self.HIFLEET_VESSELS_LIMIT = int(os.getenv('HIFLEET_VESSELS_LIMIT', '500'))
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', '20'))
        
        # 新造船船龄范围（年），默认5年以内
        self.max_ship_age = int(os.getenv('MAX_SHIP_AGE', '5'))
        
        # 支持的船舶类型：干散货（散货船）和杂货船
        self.shiptypes = ['散货船', '杂货船']
        
        # 代理配置（可选）
        self.use_proxy = os.getenv('USE_PROXY', 'false').lower() == 'true'
        self.proxy_url = os.getenv('PROXY_URL', '')

        config = {
            'handle_db': 'mgo',
            "cache_rds": True,
            'collection': 'global_vessels',
            'uniq_idx': [
                ('imo', pymongo.ASCENDING)
            ]
        }
        
        # 基础 headers 模板
        self.base_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Origin": "https://www.hifleet.com",
            "Referer": "https://www.hifleet.com/vessels/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
        }

        super(SpiderHifleetNewbuildingVessels, self).__init__(config)

        # 创建带重试机制的 session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_random_headers(self):
        """生成随机的 headers，每次请求都不同"""
        headers = self.base_headers.copy()
        headers["User-Agent"] = random.choice(self.USER_AGENTS)
        headers.pop("Host", None)
        headers.pop("Content-Length", None)
        return headers

    def get_proxy_dict(self):
        """获取代理配置"""
        if self.use_proxy and self.proxy_url:
            return {
                "http": self.proxy_url,
                "https": self.proxy_url
            }
        env_proxies = {}
        for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            proxy_val = os.environ.get(key)
            if proxy_val:
                scheme = key.lower().replace('_proxy', '')
                if 'http' in scheme:
                    env_proxies['http'] = proxy_val
                if 'https' in scheme or 'all' in scheme:
                    env_proxies['https'] = proxy_val
        if env_proxies:
            return env_proxies
        return None

    def create_payload(self, shiptype, page):
        """创建请求 payload"""
        current_year = datetime.datetime.now().year
        # 计算最小建造年份（当前年份 - 最大船龄）
        min_build_year = current_year - self.max_ship_age
        
        payload = {
            "offset": page,
            "limit": self.HIFLEET_VESSELS_LIMIT,
            "_v": "5.3.588",
            "params": {
                "shipname": "",
                "callsign": "",
                "shiptype": shiptype,
                "shipflag": "",
                "keyword": "",
                "mmsi": -1,
                "imo": -1,
                "isFleetShip": 0,
                "shipagemin": 0,  # 最小船龄为0
                "shipagemax": self.max_ship_age,  # 最大船龄限制
                "loamin": -1,
                "loamax": -1,
                "dwtmin": -1,
                "dwtmax": -1,
                "sortcolumn": "yearofbuild",
                "sorttype": "desc",  # 按建造年份降序排列，最新的在前
                "isFleetShip": 0
            }
        }
        return payload

    def process_vessel_data(self, item):
        """处理单条船舶数据"""
        # 优先使用 IMO 作为唯一键
        imo_raw = item.get("imo")
        try:
            imo_val = int(float(imo_raw)) if imo_raw not in (None, "", "null") else None
        except (TypeError, ValueError):
            imo_val = None

        if not imo_val or imo_val <= 0:
            print(f"跳过无效IMO记录: imo={imo_raw}, shipname={item.get('shipname')}")
            return None

        # 规范化 mmsi
        mmsi_raw = item.get("mmsi")
        try:
            if mmsi_raw not in (None, "", "null"):
                item["mmsi"] = int(float(mmsi_raw))
            else:
                item["mmsi"] = None
        except (TypeError, ValueError):
            item["mmsi"] = None

        item["imo"] = imo_val
        
        # 添加新造船标记
        item["is_newbuilding"] = True
        item["newbuilding_update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return item

    @decorate.exception_capture_close_datebase
    def run(self):
        """执行新造船数据爬取任务"""
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"开始爬取新造船数据 - {dataTime}")
            print(f"船舶类型: {', '.join(self.shiptypes)}")
            print(f"最大船龄: {self.max_ship_age}年")
            print(f"页码范围: {self.PAGE_START} - {self.PAGE_END}")
            print("-" * 60)

            total_inserted = 0
            total_existing = 0

            # 遍历每种船舶类型
            for shiptype in self.shiptypes:
                print(f"\n## 开始处理船舶类型: {shiptype}")
                
                # 遍历每一页
                for page in range(self.PAGE_START, self.PAGE_END):
                    print(f"### 正在处理 {shiptype} 第 {page} 页数据")
                    
                    payload = self.create_payload(shiptype, page)
                    headers = self.get_random_headers()
                    proxies = self.get_proxy_dict()

                    try:
                        response = self.session.post(
                            self.HIFLEET_VESSELS_LIST_URL,
                            json=payload,
                            headers=headers,
                            proxies=proxies if proxies else None,
                            timeout=30
                        )

                        # 处理限流和错误
                        if response.status_code == 429:
                            print("收到 429 限流响应，等待 60 秒...")
                            time.sleep(60)
                            continue
                        elif response.status_code == 401:
                            print("收到 401 未授权响应，可能被检测为爬虫，增加等待时间...")
                            time.sleep(self.time_sleep_seconds * 2)
                            continue

                        if response.status_code == 200:
                            data = response.json().get("data", [])
                            status = response.json().get("status", "")

                            # 检查是否被拒绝或没有数据
                            if status == "402" or not data or data == []:
                                print(f"{shiptype} 读取完成，响应: {response.text[:100] if response.text else '无数据'}")
                                break

                            # 处理数据
                            page_inserted = 0
                            page_existing = 0
                            
                            for item in data:
                                processed_item = self.process_vessel_data(item)
                                if not processed_item:
                                    continue

                                imo_val = processed_item["imo"]
                                
                                # 检查是否已存在
                                existing_record = self.mgo_db["global_vessels"].find_one({"imo": imo_val})
                                
                                if not existing_record:
                                    # 插入新记录
                                    self.mgo.set(None, processed_item)
                                    print(f"插入新记录: imo={imo_val}, 类型={shiptype}, 船名={item.get('shipname', 'N/A')}")
                                    page_inserted += 1
                                    total_inserted += 1
                                else:
                                    # 更新已有记录的新造船信息
                                    update_data = {
                                        "is_newbuilding": True,
                                        "newbuilding_update_time": processed_item["newbuilding_update_time"]
                                    }
                                    # 如果已有记录中没有某些字段，也更新这些字段
                                    for key in ["mmsi", "shipname", "shiptype", "yearofbuild"]:
                                        if key in processed_item and key not in existing_record:
                                            update_data[key] = processed_item[key]
                                    
                                    self.mgo_db["global_vessels"].update_one(
                                        {"imo": imo_val},
                                        {"$set": update_data}
                                    )
                                    print(f"更新已有记录: imo={imo_val}, 类型={shiptype}")
                                    page_existing += 1
                                    total_existing += 1

                            print(f"第 {page} 页完成 - 新增: {page_inserted}, 更新: {page_existing}")
                            
                            # 如果这页没有新数据，可能已经到底了
                            if page_inserted == 0 and page_existing == 0:
                                print(f"{shiptype} 没有更多数据，跳过剩余页码")
                                break
                                
                        else:
                            print(f"请求失败，状态码: {response.status_code}, 响应: {response.text[:200]}")

                    except requests.exceptions.RequestException as e:
                        print(f"请求异常: {e}")
                        time.sleep(self.time_sleep_seconds)

                    # 添加随机延迟，模拟人类行为
                    sleep_time = self.time_sleep_seconds + random.uniform(1, 5)
                    print(f"等待 {sleep_time:.2f} 秒后继续...")
                    time.sleep(sleep_time)

                print(f"\n{shiptype} 处理完成")

            print("\n" + "=" * 60)
            print(f"新造船数据爬取完成！")
            print(f"总计 - 新增: {total_inserted}, 更新: {total_existing}")
            print("=" * 60)

        except Exception as e:
            print("error:", e)
            traceback.print_exc()
