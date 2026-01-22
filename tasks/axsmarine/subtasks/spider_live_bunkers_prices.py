#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pkg.public.decorator import decorate
import os
import pymongo
import http.client
import datetime
import time
import json
import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import ssl
from pkg.public.models import BaseModel
from pkg.public.wechat_push import WechatPush, PrefixEnums


class SpiderLiveBunkersPrices(BaseModel):
    LIVE_BUNKERS_PRICES_URL = "https://app.axsmarine.com/Apps/Bunker/api/get-rates"

    def __init__(self):
        config = {
            'cache_rds': True,
            'handle_db': 'mgo',
            'collection': 'axs_live_bunkers_prices',
            'uniq_idx': [
                ('portName', pymongo.ASCENDING),
                ('portCountry', pymongo.ASCENDING),
                ('grade', pymongo.ASCENDING),
            ]
        }
        super(SpiderLiveBunkersPrices, self).__init__(config)
        
        # 创建带有重试机制的session
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # 创建适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置SSL配置
        self.session.verify = False  # 临时禁用SSL验证
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @decorate.exception_capture_close_datebase
    def run(self):
        dataTime = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
        print(f"SpiderLiveBunkersPrices start at {dataTime}")
        
        # 获取cookie（如果配置了Redis cache）
        cookie = None
        if hasattr(self, 'cache_rds') and self.cache_rds:
            try:
                cookie = self.cache_rds.get('axs_live_cookie')
            except Exception:
                pass
        
        try:
            # 构建请求URL和参数
            url = f"{self.LIVE_BUNKERS_PRICES_URL}?_dc={int(time.time() * 1000)}&page=1&start=0&limit=25"
            
            # 设置请求头
            headers = {
                'authority': 'app.axsmarine.com',
                'x-requested-with': 'XMLHttpRequest',
                'Cookie': cookie
            }
            
            # 发送请求
            logging.info(f"Requesting data from: {url}")
            
            # 使用session发送请求，包含重试机制
            response = self.session.get(
                url, 
                headers=headers, 
                timeout=30,
                verify=False  # 禁用SSL验证
            )
            response.raise_for_status()
            
            # 解析响应数据
            data = response.json()
            logging.info(f"Raw response type: {type(data)}")
            # logging.info(f"Raw response content: {data}")
            
            # 处理不同的响应格式
            if isinstance(data, list):
                # 如果直接返回列表
                records = data
                logging.info(f"Received list response with {len(records)} records")
            elif isinstance(data, dict):
                # 如果是字典格式，尝试获取data字段
                records = data.get('data', [])
                logging.info(f"Received dict response with {len(records)} records")
            else:
                logging.error(f"Unexpected response format: {type(data)}")
                records = []
            
            # 处理并保存数据
            saved_count = 0
            for i, item in enumerate(records):
                try:
                    # 验证item是否为字典
                    if not isinstance(item, dict):
                        logging.warning(f"Item {i} is not a dictionary: {type(item)} - {item}")
                        continue
                    
                    # 添加时间戳
                    item['dataTime'] = dataTime
                    item['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 保存到数据库
                    result = self.mgo.set(None, item)
                    if result:
                        saved_count += 1
                        logging.debug(f"Saved bunker price data for {item.get('portName', 'Unknown')} - {item.get('grade', 'Unknown')}")
                    
                except Exception as e:
                    logging.error(f"Error saving item {i}: {item} - Error: {e}")
                    continue
            
            logging.info(f"Successfully saved {saved_count} bunker price records")
            print(f"SpiderLiveBunkersPrices completed: saved {saved_count} records")
            
        except requests.exceptions.SSLError as e:
            logging.error(f"SSL connection error: {e}")
            logging.info("Trying alternative request method...")
            try:
                # 尝试使用不同的SSL配置
                import ssl
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                # 创建新的session with different SSL settings
                alt_session = requests.Session()
                alt_session.verify = False
                
                response = alt_session.get(url, headers=headers, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                logging.info(f"Alternative request successful. Response type: {type(data)}")
                
                # 处理不同的响应格式
                if isinstance(data, list):
                    records = data
                    logging.info(f"Alternative request received list with {len(records)} records")
                elif isinstance(data, dict):
                    records = data.get('data', [])
                    logging.info(f"Alternative request received dict with {len(records)} records")
                else:
                    logging.error(f"Alternative request unexpected response format: {type(data)}")
                    records = []
                
                # 处理数据
                saved_count = 0
                for i, item in enumerate(records):
                    try:
                        # 验证item是否为字典
                        if not isinstance(item, dict):
                            logging.warning(f"Alternative request - Item {i} is not a dictionary: {type(item)} - {item}")
                            continue
                        
                        item['dataTime'] = dataTime
                        item['created_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        result = self.mgo.set(None, item)
                        if result:
                            saved_count += 1
                            logging.debug(f"Alternative request saved: {item.get('portName', 'Unknown')} - {item.get('grade', 'Unknown')}")
                    except Exception as e:
                        logging.error(f"Alternative request error saving item {i}: {item} - Error: {e}")
                        continue
                
                logging.info(f"Successfully saved {saved_count} bunker price records via alternative method")
                print(f"SpiderLiveBunkersPrices completed: saved {saved_count} records")
                
            except Exception as alt_e:
                logging.error(f"Alternative request also failed: {alt_e}")
                raise
                
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in SpiderLiveBunkersPrices: {e}")
            raise