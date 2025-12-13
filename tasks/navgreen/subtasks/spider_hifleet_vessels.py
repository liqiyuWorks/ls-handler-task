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


def get_check_svc_token(cache_rds):
    """检查和获取过期的海科 token """
    token = cache_rds.hget("svc", "access_token")
    return token


def request_svc_detail(token, mmsi_list):
    url = "https://svc.data.myvessel.cn/sdc/v1/vessels/details"

    payload = {"mmsiList": mmsi_list}
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "User-Agent": "PostmanRuntime-ApipostRuntime/1.1.0",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        url=url,
        headers=headers,
        json=payload,
        timeout=30)

    return response.json().get("data", [])


class SpiderHifleetVessels(BaseModel):
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
        self.PAGE_START = int(os.getenv('PAGE_START', '1'))
        self.PAGE_END = int(os.getenv('PAGE_END', '31'))  # 从114页开始（输入 115）
        self.HIFLEET_VESSELS_LIMIT = int(
            os.getenv('HIFLEET_VESSELS_LIMIT', '500'))
        self.time_sleep_seconds = float(os.getenv('TIME_SLEEP_SECONDS', '20'))
        self.shiptype = os.getenv('SHIPTYPE', '杂货船') # 散货船,杂货船，滚装船，石油化学品船********

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
        self.payload = {
            "offset": 1,
            "limit": self.HIFLEET_VESSELS_LIMIT,
            "_v": "5.3.588",
            "params": {
                "shipname": "",
                "callsign": "",
                "shiptype": "",
                "shipflag": "",
                "keyword": "",
                "mmsi": -1,
                "imo": -1,
                "isFleetShip": 0,
                "shipagemin": -1,
                "shipagemax": -1,
                "loamin": -1,
                "loamax": -1,
                "dwtmin": -1,
                "dwtmax": -1,
                "sortcolumn": "yearofbuild",
                "shiptype": "散货船",
                "sorttype": "desc",
                "isFleetShip": 0
            }
        }
        if self.shiptype:
            self.payload["params"]["shiptype"] = self.shiptype

        # 基础 headers 模板，动态生成
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

        super(SpiderHifleetVessels, self).__init__(config)

        # 创建带重试机制的 session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            connect=3,      # 新增，连接失败自动重试
            read=3,         # 新增，读取时重试
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

        # 随机选择 User-Agent
        headers["User-Agent"] = random.choice(self.USER_AGENTS)

        # 移除 Host 和 Content-Length（由 requests 自动处理）
        headers.pop("Host", None)
        headers.pop("Content-Length", None)

        return headers

    def get_proxy_dict(self):
        """获取代理配置，自动适配操作系统环境变量，优先用 self.proxy_url"""
        # 优先使用 self.proxy_url 指定的代理
        if self.use_proxy and self.proxy_url:
            return {
                "http": self.proxy_url,
                "https": self.proxy_url
            }
        # 检查常用环境变量（系统代理）
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
        # 返回 None 代表让 requests 自动使用系统代理机制
        return None

    def update_hifleet_vessels(self, token, mmsi):
        try:
            # 调用 svc 查询 海科 request_svc_detail
            res = request_svc_detail(token, [mmsi])
            if res:
                self.mgo.set(None, res[0])
                print("更新数据", mmsi, "ok")
            else:
                print("更新数据", mmsi, "error")
        except Exception as e:
            traceback.print_exc()
            print("error:", res, e)

    @decorate.exception_capture_close_datebase
    def run(self):
        # token = get_check_svc_token(self.cache_rds)
        try:
            dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
            print(dataTime)
            # 从最后一页往前倒序遍历（PAGE_END-1 到 PAGE_START，含）
            for index in range(self.PAGE_START, self.PAGE_END): # 正序
            # for index in range(self.PAGE_END - 1, self.PAGE_START - 1, -1):  # 逆序
                print(f"## 开始插入第 {index} 页的数据")
                self.payload["offset"] = index

                # 使用动态 headers 和代理
                headers = self.get_random_headers()
                proxies = self.get_proxy_dict()

                try:
                    response = self.session.post(
                        self.HIFLEET_VESSELS_LIST_URL,
                        json=self.payload,
                        headers=headers                        # proxies 自动适配，不再强制传递 None/空
                        , proxies=proxies if proxies else None, timeout=30
                    )

                    # 如果是 429 或 401，增加等待时间
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

                        # 检查是否被拒绝
                        if status == "402" or data == [] or data == None:
                            print(f"读取完成，运行结束... 响应: {response.text}")
                            break

                        # 处理数据
                        for item in data:
                            # 优先使用 IMO 作为唯一键，跳过无效 IMO 的记录
                            imo_raw = item.get("imo")
                            try:
                                imo_val = int(float(imo_raw)) if imo_raw not in (
                                    None, "", "null") else None
                            except (TypeError, ValueError):
                                imo_val = None

                            if not imo_val or imo_val <= 0:
                                print(
                                    f"跳过无效IMO记录: imo={imo_raw}, shipname={item.get('shipname')}")
                                continue

                            # 可选：规范化 mmsi 类型为 int（若存在且可转换）
                            mmsi_raw = item.get("mmsi")
                            try:
                                if mmsi_raw not in (None, "", "null"):
                                    item["mmsi"] = int(float(mmsi_raw))
                                else:
                                    item["mmsi"] = None
                            except (TypeError, ValueError):
                                item["mmsi"] = None

                            item["imo"] = imo_val

                            existing_record = self.mgo_db["global_vessels"].find_one({
                                                                                     "imo": imo_val})
                            if not existing_record:
                                self.mgo.set(None, item)
                                print(f"插入新记录: imo={imo_val}")
                            else:
                                print(f"已存在，不插入，imo={imo_val}")
                        # else:
                        #     if existing_record["dwt"] is None or existing_record["dwt"] == 0 or existing_record["dwt"] == "" or existing_record["dwt"] == "******":
                        #         self.update_hifleet_vessels(token, int(item.get('mmsi')))
                    else:
                        print(
                            f"请求失败，状态码: {response.status_code}, 响应: {response.text}")

                except requests.exceptions.RequestException as e:
                    print(f"请求异常: {e}")
                    time.sleep(self.time_sleep_seconds)

                # 添加随机延迟，模拟人类行为
                sleep_time = self.time_sleep_seconds + random.uniform(1, 5)
                print(f"等待 {sleep_time:.2f} 秒后继续...")
                time.sleep(sleep_time)

        except Exception as e:
            print("error:", e)
            traceback.print_exc()
