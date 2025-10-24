#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
import pymongo
import requests
import logging
import os
from typing import Dict, Optional, Any


class SpiderFisTradeData(BaseModel):
    """
    爬取FIS交易数据:
    支持多种航运金融衍生品（如C5TC、P4TC、P5TC等）的交易信息获取和分表存储。
    每个产品类型使用独立的MongoDB集合进行存储，便于数据管理和查询。
    """

    def __init__(self, product_type: str = "C5TC"):
        self.logger = logging.getLogger(__name__)
        self.product_type = product_type.upper()
        
        # 产品配置
        self.product_configs = {
            'C5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/1/405/F/null/null',
                'collection_name': 'fis_trade_c5tc_data'
            },
            'P4TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/12/405/F/null/null',
                'collection_name': 'fis_trade_p4tc_data'
            },
            'P5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/39/405/F/null/null',
                'collection_name': 'fis_trade_p5tc_data'
            }
        }
        
        if self.product_type not in self.product_configs:
            raise ValueError(f"不支持的产品类型: {self.product_type}。支持的类型: {list(self.product_configs.keys())}")
        
        product_config = self.product_configs[self.product_type]
        self.api_url = product_config['api_url']
        self.collection_name = product_config['collection_name']
        
        # 数据库配置
        self.uniq_idx = [('Date', pymongo.ASCENDING)]
        config = {
            'cache_rds': True,
            'collection': self.collection_name,
            'uniq_idx': self.uniq_idx
        }
        super(SpiderFisTradeData, self).__init__(config)

    def _get_fis_auth_token(self):
        """获取FIS认证token"""
        try:
            if hasattr(self, 'cache_rds') and self.cache_rds:
                # 首先检查键是否存在
                if not self.cache_rds.exists("fis-live"):
                    self.logger.warning("Redis中不存在fis-live键，使用fallback token")
                    return self._get_fallback_token()

                # 检查键的类型
                key_type = self.cache_rds.type("fis-live")
                self.logger.info(f"Redis中fis-live键的类型: {key_type}")

                token = None

                if key_type == 'hash':
                    # 如果是hash类型，尝试获取auth_token字段
                    token = self.cache_rds.hget("fis-live", "auth_token")
                    if not token:
                        # 如果没有auth_token字段，尝试获取其他可能的字段
                        all_fields = self.cache_rds.hgetall("fis-live")
                        self.logger.info(f"fis-live hash中的所有字段: {list(all_fields.keys())}")

                        # 尝试常见的token字段名
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                self.logger.info(f"从hash字段 '{field_name}' 获取到token")
                                break

                elif key_type == 'string':
                    # 如果是string类型，直接获取值
                    token = self.cache_rds.get("fis-live")
                    self.logger.info("从string类型的fis-live键获取到token")

                elif key_type == 'list':
                    # 如果是list类型，获取第一个元素
                    token = self.cache_rds.lindex("fis-live", 0)
                    self.logger.info("从list类型的fis-live键获取到token")

                else:
                    self.logger.warning(f"不支持的Redis键类型: {key_type}")

                if token:
                    self.logger.info("从Redis缓存中获取到fis-live auth_token")
                    return token
                else:
                    self.logger.warning("Redis缓存中未找到有效的fis-live auth_token，使用fallback token")
                    return self._get_fallback_token()
            else:
                self.logger.warning("Redis连接不可用，使用fallback token")
                return self._get_fallback_token()
        except Exception as e:
            self.logger.error(f"获取FIS认证token时发生错误: {str(e)}，使用fallback token")
            return self._get_fallback_token()

    def _get_fallback_token(self):
        """获取FIS备用token"""
        # 首先尝试从环境变量获取
        fallback_token = os.getenv('FIS_FALLBACK_TOKEN')
        if fallback_token:
            self.logger.info("使用环境变量中的FIS_FALLBACK_TOKEN")
            return fallback_token
        
        # 如果没有环境变量，使用硬编码的token（仅用于测试）
        hardcoded_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEwMjU0MjUsImV4cCI6MTc2MTExMTgyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.urQaNPtTQYXm-c_nTpEhDY_tVINtCKpdg7X04EFsujSNU1ie1GD-_tjtsg9Ge7k4VkfYDt3Eg9lzIARqFvDGqwb5dggPU8AL9anIYcrcPY-fMVX7biVPTLlIl7t_3VY7Z-j9JQDUge9HS2lZFkDGMP4LJpu2tzZrQ1JiQ7oeVsvYLwgia8HgKtYvUM6iVkrACnOZTmDUEcMA2kn9Q1c68tDGJvbg7cmPasVDrzRx_2fKlR_OEbVCt78YEbCVs_hRlvr4NFPu2Ck6kkpLB2joKl1-p-bLQMxPGhydXKZsPjlMQ_W8SXfZwMKcfcpg9Ti4nC-Kt9gJcfOwW2q764AK-w"
        self.logger.warning("使用硬编码的fallback token（仅用于测试）")
        return hardcoded_token

    def _get_api_headers(self):
        """获取API请求头"""
        return {
            'Authorization': f'{self._get_fis_auth_token()}'
        }

    def _fetch_trade_data(self, max_retries=3):
        """获取交易数据"""
        for attempt in range(max_retries):
            try:
                headers = self._get_api_headers()
                self.logger.info(f"正在请求 {self.product_type} API: {self.api_url}")
                self.logger.debug(f"请求头: {headers}")
                
                response = requests.get(self.api_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(f"成功获取 {self.product_type} 数据，记录数: {len(data) if isinstance(data, list) else 'N/A'}")
                    return data
                elif response.status_code == 401:
                    self.logger.error(f"{self.product_type} API认证失败 (401) - Token可能已过期")
                    self.logger.error("请运行 'python update_fis_token.py' 更新token")
                    return None
                elif response.status_code == 404:
                    self.logger.error(f"{self.product_type} API接口不存在 (404): {self.api_url}")
                    return None
                else:
                    self.logger.warning(f"{self.product_type} API请求失败，状态码: {response.status_code}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"{self.product_type} API请求异常: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                    continue
                return None
            except Exception as e:
                self.logger.error(f"{self.product_type} 获取数据时发生未知错误: {str(e)}")
                return None
        
        self.logger.error(f"{self.product_type} 数据获取失败，已重试 {max_retries} 次")
        return None

    def _save_trade_data(self, raw_data):
        """保存交易数据"""
        if not hasattr(self, 'mgo') or self.mgo is None:
            self.logger.warning("MongoDB连接不可用，跳过数据保存")
            return False
        
        try:
            if not isinstance(raw_data, list):
                self.logger.error("数据格式错误，期望列表格式")
                return False
            
            if not raw_data:
                self.logger.warning("数据为空，跳过保存")
                return False
            
            success_count = 0
            total_count = len(raw_data)
            
            for trade_record in raw_data:
                if not isinstance(trade_record, dict):
                    self.logger.warning("跳过非字典格式的记录")
                    continue
                
                # 添加产品类型和创建时间
                trade_record['product_type'] = self.product_type
                trade_record['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 使用Date字段作为唯一键
                date_value = trade_record.get('Date')
                if not date_value:
                    self.logger.warning("跳过没有Date字段的记录")
                    continue
                
                result = self.mgo.set(
                    key={'Date': date_value},
                    data=trade_record
                )
                
                if result is not None:
                    success_count += 1
                    self.logger.debug(f"成功保存 {self.product_type} 日期为 {date_value} 的交易数据")
                else:
                    self.logger.warning(f"保存 {self.product_type} 日期为 {date_value} 的交易数据失败")
            
            if success_count > 0:
                self.logger.info(f"成功保存 {self.product_type} {success_count}/{total_count} 条交易数据")
                return True
            else:
                self.logger.error(f"没有成功保存任何 {self.product_type} 数据")
                return False
                
        except Exception as e:
            self.logger.error(f"保存交易数据时发生错误: {str(e)}")
            return False

    @decorate.exception_capture_close_datebase
    def run(self, task=None):
        """主运行方法"""
        self.logger.info(f"开始爬取FIS {self.product_type} 交易数据")

        try:
            raw_data = self._fetch_trade_data()
            
            if raw_data is None:
                self.logger.error(f"FIS {self.product_type} 交易数据获取失败")
                return False
            
            save_success = self._save_trade_data(raw_data)
            
            if save_success:
                self.logger.info(f"FIS {self.product_type} 交易数据爬取成功")
                return True
            else:
                self.logger.error(f"FIS {self.product_type} 交易数据保存失败")
                return False
                
        except Exception as e:
            self.logger.error(f"FIS {self.product_type} 交易数据爬取过程中发生错误: {str(e)}")
            return False


class SpiderAllFisTradeData:
    """
    爬取所有FIS交易数据:
    同时获取C5TC、P4TC、P5TC三个产品类型的交易数据。
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.product_types = ['C5TC', 'P4TC', 'P5TC']
        self.spiders = {}
        for product_type in self.product_types:
            try:
                self.spiders[product_type] = SpiderFisTradeData(product_type)
                self.logger.info(f"初始化 {product_type} 爬虫成功")
            except Exception as e:
                self.logger.error(f"初始化 {product_type} 爬虫失败: {str(e)}")
                self.spiders[product_type] = None

    def run_all(self):
        """运行所有产品的数据爬取"""
        self.logger.info("开始爬取所有FIS交易数据")
        results = {}
        for product_type in self.product_types:
            spider = self.spiders.get(product_type)
            if spider is None:
                self.logger.error(f"{product_type} 爬虫不可用，跳过")
                results[product_type] = False
                continue
            
            try:
                self.logger.info(f"开始爬取 {product_type} 数据")
                success = spider.run()
                results[product_type] = success
                if success:
                    self.logger.info(f"{product_type} 数据爬取完成")
                else:
                    self.logger.error(f"{product_type} 数据爬取失败")
            except Exception as e:
                self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
                results[product_type] = False
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        self.logger.info(f"所有FIS交易数据爬取完成: {success_count}/{total_count} 个产品成功")
        
        for product_type, success in results.items():
            status = "成功" if success else "失败"
            self.logger.info(f"  {product_type}: {status}")
        
        return results

    def run_single(self, product_type: str):
        """运行单个产品的数据爬取"""
        product_type = product_type.upper()
        
        if product_type not in self.product_types:
            self.logger.error(f"不支持的产品类型: {product_type}")
            return False
        
        spider = self.spiders.get(product_type)
        if spider is None:
            self.logger.error(f"{product_type} 爬虫不可用")
            return False
        
        try:
            self.logger.info(f"开始爬取 {product_type} 数据")
            success = spider.run()
            self.logger.info(f"{product_type} 数据爬取完成")
            return success
        except Exception as e:
            self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
            return False

    def run(self, task=None):
        """运行所有产品的数据爬取（兼容main.py调用）"""
        return self.run_all()

    def close(self):
        """关闭所有爬虫连接"""
        for product_type, spider in self.spiders.items():
            if spider is not None:
                try:
                    spider.close()
                    self.logger.info(f"关闭 {product_type} 爬虫连接")
                except Exception as e:
                    self.logger.error(f"关闭 {product_type} 爬虫连接时发生错误: {str(e)}")


class SpiderFisMarketTrades(BaseModel):
    """
    爬取FIS市场交易数据（已执行交易）:
    获取FIS平台上的实际执行交易信息，用于市场分析和决策支持。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_url = 'https://livepricing-prod2.azurewebsites.net/api/v1/marketTrades'
        self.collection_name = 'fis_market_trades'
        
        # 数据库配置
        self.uniq_idx = [('tradeId', pymongo.ASCENDING)]
        config = {
            'cache_rds': True,
            'collection': self.collection_name,
            'uniq_idx': self.uniq_idx
        }
        super(SpiderFisMarketTrades, self).__init__(config)

    def _get_fis_auth_token(self):
        """获取FIS认证token"""
        try:
            if hasattr(self, 'cache_rds') and self.cache_rds:
                if not self.cache_rds.exists("fis-live"):
                    self.logger.warning("Redis中不存在fis-live键，使用fallback token")
                    return self._get_fallback_token()

                key_type = self.cache_rds.type("fis-live")
                self.logger.info(f"Redis中fis-live键的类型: {key_type}")

                token = None
                if key_type == 'hash':
                    token = self.cache_rds.hget("fis-live", "auth_token")
                    if not token:
                        all_fields = self.cache_rds.hgetall("fis-live")
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                break
                elif key_type == 'string':
                    token = self.cache_rds.get("fis-live")
                elif key_type == 'list':
                    token = self.cache_rds.lindex("fis-live", 0)

                if token:
                    self.logger.info("从Redis缓存中获取到fis-live auth_token")
                    return token
                else:
                    self.logger.warning("Redis缓存中未找到有效的fis-live auth_token，使用fallback token")
                    return self._get_fallback_token()
            else:
                self.logger.warning("Redis连接不可用，使用fallback token")
                return self._get_fallback_token()
        except Exception as e:
            self.logger.error(f"获取FIS认证token时发生错误: {str(e)}，使用fallback token")
            return self._get_fallback_token()

    def _get_fallback_token(self):
        """获取FIS备用token"""
        fallback_token = os.getenv('FIS_FALLBACK_TOKEN')
        if fallback_token:
            self.logger.info("使用环境变量中的FIS_FALLBACK_TOKEN")
            return fallback_token
        
        hardcoded_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEwMjU0MjUsImV4cCI6MTc2MTExMTgyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.urQaNPtTQYXm-c_nTpEhDY_tVINtCKpdg7X04EFsujSNU1ie1GD-_tjtsg9Ge7k4VkfYDt3Eg9lzIARqFvDGqwb5dggPU8AL9anIYcrcPY-fMVX7biVPTLlIl7t_3VY7Z-j9JQDUge9HS2lZFkDGMP4LJpu2tzZrQ1JiQ7oeVsvYLwgia8HgKtYvUM6iVkrACnOZTmDUEcMA2kn9Q1c68tDGJvbg7cmPasVDrzRx_2fKlR_OEbVCt78YEbCVs_hRlvr4NFPu2Ck6kkpLB2joKl1-p-bLQMxPGhydXKZsPjlMQ_W8SXfZwMKcfcpg9Ti4nC-Kt9gJcfOwW2q764AK-w"
        self.logger.warning("使用硬编码的fallback token（仅用于测试）")
        return hardcoded_token

    def _get_api_headers(self):
        """获取API请求头"""
        return {
            'Authorization': f'{self._get_fis_auth_token()}'
        }

    def _fetch_market_trades(self, max_retries=3):
        """获取市场交易数据"""
        for attempt in range(max_retries):
            try:
                headers = self._get_api_headers()
                self.logger.info(f"正在请求市场交易API: {self.api_url}")
                
                response = requests.get(self.api_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(f"成功获取市场交易数据，记录数: {len(data) if isinstance(data, list) else 'N/A'}")
                    return data
                elif response.status_code == 401:
                    self.logger.error("市场交易API认证失败 (401) - Token可能已过期")
                    return None
                else:
                    self.logger.warning(f"市场交易API请求失败，状态码: {response.status_code}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"市场交易API请求异常: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                    continue
                return None
            except Exception as e:
                self.logger.error(f"获取市场交易数据时发生未知错误: {str(e)}")
                return None
        
        self.logger.error(f"市场交易数据获取失败，已重试 {max_retries} 次")
        return None

    def _save_market_trades(self, raw_data):
        """保存市场交易数据"""
        if not hasattr(self, 'mgo') or self.mgo is None:
            self.logger.warning("MongoDB连接不可用，跳过数据保存")
            return False
        
        try:
            if not isinstance(raw_data, list):
                self.logger.error("数据格式错误，期望列表格式")
                return False
            
            if not raw_data:
                self.logger.warning("数据为空，跳过保存")
                return False
            
            success_count = 0
            total_count = len(raw_data)
            
            for trade_record in raw_data:
                if not isinstance(trade_record, dict):
                    self.logger.warning("跳过非字典格式的记录")
                    continue
                
                # 添加创建时间
                trade_record['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 使用tradeId作为唯一键
                trade_id = trade_record.get('tradeId')
                if not trade_id:
                    self.logger.warning("跳过没有tradeId字段的记录")
                    continue
                
                result = self.mgo.set(
                    key={'tradeId': trade_id},
                    data=trade_record
                )
                
                if result is not None:
                    success_count += 1
                    self.logger.debug(f"成功保存交易ID为 {trade_id} 的市场交易数据")
                else:
                    self.logger.warning(f"保存交易ID为 {trade_id} 的市场交易数据失败")
            
            if success_count > 0:
                self.logger.info(f"成功保存 {success_count}/{total_count} 条市场交易数据")
                return True
            else:
                self.logger.error("没有成功保存任何市场交易数据")
                return False
                
        except Exception as e:
            self.logger.error(f"保存市场交易数据时发生错误: {str(e)}")
            return False

    @decorate.exception_capture_close_datebase
    def run(self, task=None):
        """主运行方法"""
        self.logger.info("开始爬取FIS市场交易数据")

        try:
            raw_data = self._fetch_market_trades()
            
            if raw_data is None:
                self.logger.error("FIS市场交易数据获取失败")
                return False
            
            save_success = self._save_market_trades(raw_data)
            
            if save_success:
                self.logger.info("FIS市场交易数据爬取成功")
                return True
            else:
                self.logger.error("FIS市场交易数据保存失败")
                return False
                
        except Exception as e:
            self.logger.error(f"FIS市场交易数据爬取过程中发生错误: {str(e)}")
            return False


class SpiderFisDailyTradeData(BaseModel):
    """
    爬取FIS逐日交易数据:
    获取C5TC、P4TC、P5TC等产品的逐日交易数据，用于图表展示和趋势分析。
    每个产品类型使用独立的MongoDB集合进行存储。
    """

    def __init__(self, product_type: str = "C5TC"):
        self.logger = logging.getLogger(__name__)
        self.product_type = product_type.upper()
        
        # 产品配置
        self.product_configs = {
            'C5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/1/405/F/null/null',
                'collection_name': 'fis_daily_c5tc_trade_data'
            },
            'P4TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/12/405/F/null/null',
                'collection_name': 'fis_daily_p4tc_trade_data'
            },
            'P5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/39/405/F/null/null',
                'collection_name': 'fis_daily_p5tc_trade_data'
            }
        }
        
        if self.product_type not in self.product_configs:
            raise ValueError(f"不支持的产品类型: {self.product_type}。支持的类型: {list(self.product_configs.keys())}")
        
        product_config = self.product_configs[self.product_type]
        self.api_url = product_config['api_url']
        self.collection_name = product_config['collection_name']
        
        # 数据库配置
        self.uniq_idx = [('Date', pymongo.ASCENDING)]

        # 初始化数据库连接
        config = {
            'cache_rds': True,
            'collection': self.collection_name,
            'uniq_idx': self.uniq_idx
        }
        
        try:
            super(SpiderFisDailyTradeData, self).__init__(config)
            self.logger.info(f"{self.product_type} 爬虫初始化成功")
        except Exception as e:
            self.logger.error(f"{self.product_type} 爬虫初始化失败: {str(e)}")
            # 即使数据库连接失败，也允许继续运行（仅获取数据）
            self.mgo = None

    def _get_fis_auth_token(self):
        """获取FIS认证token"""
        try:
            if hasattr(self, 'cache_rds') and self.cache_rds:
                # 首先检查键是否存在
                if not self.cache_rds.exists("fis-live"):
                    self.logger.warning("Redis中不存在fis-live键，使用fallback token")
                    return self._get_fallback_token()

                # 检查键的类型
                key_type = self.cache_rds.type("fis-live")
                self.logger.info(f"Redis中fis-live键的类型: {key_type}")

                token = None

                if key_type == 'hash':
                    # 如果是hash类型，尝试获取auth_token字段
                    token = self.cache_rds.hget("fis-live", "auth_token")
                    if not token:
                        # 如果没有auth_token字段，尝试获取其他可能的字段
                        all_fields = self.cache_rds.hgetall("fis-live")
                        self.logger.info(f"fis-live hash中的所有字段: {list(all_fields.keys())}")

                        # 尝试常见的token字段名
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                self.logger.info(f"从hash字段 '{field_name}' 获取到token")
                                break

                elif key_type == 'string':
                    # 如果是string类型，直接获取值
                    token = self.cache_rds.get("fis-live")
                    self.logger.info("从string类型的fis-live键获取到token")

                elif key_type == 'list':
                    # 如果是list类型，获取第一个元素
                    token = self.cache_rds.lindex("fis-live", 0)
                    self.logger.info("从list类型的fis-live键获取到token")

                else:
                    self.logger.warning(f"不支持的Redis键类型: {key_type}")

                if token:
                    self.logger.info("从Redis缓存中获取到fis-live auth_token")
                    return token
                else:
                    self.logger.warning("Redis缓存中未找到有效的fis-live auth_token，使用fallback token")
                    return self._get_fallback_token()
            else:
                self.logger.warning("Redis连接不可用，使用fallback token")
                return self._get_fallback_token()
        except Exception as e:
            self.logger.error(f"获取FIS认证token时发生错误: {str(e)}，使用fallback token")
            return self._get_fallback_token()

    def _get_fallback_token(self):
        """获取FIS备用token"""
        # 首先尝试从环境变量获取
        fallback_token = os.getenv('FIS_FALLBACK_TOKEN')
        if fallback_token:
            self.logger.info("使用环境变量中的FIS_FALLBACK_TOKEN")
            return fallback_token
        
        # 如果没有环境变量，使用硬编码的token（仅用于测试）
        hardcoded_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEwMjU0MjUsImV4cCI6MTc2MTExMTgyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.urQaNPtTQYXm-c_nTpEhDY_tVINtCKpdg7X04EFsujSNU1ie1GD-_tjtsg9Ge7k4VkfYDt3Eg9lzIARqFvDGqwb5dggPU8AL9anIYcrcPY-fMVX7biVPTLlIl7t_3VY7Z-j9JQDUge9HS2lZFkDGMP4LJpu2tzZrQ1JiQ7oeVsvYLwgia8HgKtYvUM6iVkrACnOZTmDUEcMA2kn9Q1c68tDGJvbg7cmPasVDrzRx_2fKlR_OEbVCt78YEbCVs_hRlvr4NFPu2Ck6kkpLB2joKl1-p-bLQMxPGhydXKZsPjlMQ_W8SXfZwMKcfcpg9Ti4nC-Kt9gJcfOwW2q764AK-w"
        self.logger.warning("使用硬编码的fallback token（仅用于测试）")
        return hardcoded_token

    def _get_api_headers(self):
        """获取API请求头"""
        return {
            'Authorization': f'{self._get_fis_auth_token()}'
        }

    def _fetch_daily_trade_data(self, max_retries=3):
        """获取逐日交易数据"""
        for attempt in range(max_retries):
            try:
                headers = self._get_api_headers()
                self.logger.info(f"正在请求 {self.product_type} API: {self.api_url}")
                self.logger.debug(f"请求头: {headers}")
                
                response = requests.get(self.api_url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(f"成功获取 {self.product_type} 数据，记录数: {len(data) if isinstance(data, list) else 'N/A'}")
                    return data
                elif response.status_code == 401:
                    self.logger.error(f"{self.product_type} API认证失败 (401) - Token可能已过期")
                    self.logger.error("请运行 'python update_fis_token.py' 更新token")
                    return None
                elif response.status_code == 404:
                    self.logger.error(f"{self.product_type} API接口不存在 (404): {self.api_url}")
                    return None
                else:
                    self.logger.warning(f"{self.product_type} API请求失败，状态码: {response.status_code}")
                    if attempt < max_retries - 1:
                        self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                self.logger.error(f"{self.product_type} API请求异常: {str(e)}")
                if attempt < max_retries - 1:
                    self.logger.info(f"重试 {attempt + 1}/{max_retries}")
                    continue
                return None
            except Exception as e:
                self.logger.error(f"{self.product_type} 获取数据时发生未知错误: {str(e)}")
                return None
        
        self.logger.error(f"{self.product_type} 数据获取失败，已重试 {max_retries} 次")
        return None

    def _format_date_field(self, date_value):
        """格式化Date字段为YYYY-MM-DD格式"""
        try:
            if not date_value:
                return None
            
            if isinstance(date_value, str):
                if 'T' in date_value:
                    return date_value.split('T')[0]
                elif len(date_value) == 10 and date_value.count('-') == 2:
                    return date_value
                else:
                    try:
                        dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                        return dt.strftime('%Y-%m-%d')
                    except ValueError:
                        return None
            
            elif isinstance(date_value, datetime):
                return date_value.strftime('%Y-%m-%d')
            
            return None
            
        except Exception as e:
            self.logger.error(f"格式化Date字段时发生错误: {str(e)}")
            return None

    def _save_daily_trade_data(self, raw_data):
        """保存逐日交易数据，根据Date字段作为唯一键"""
        if not hasattr(self, 'mgo') or self.mgo is None:
            self.logger.warning("MongoDB连接不可用，跳过数据保存")
            return False
        
        try:
            if not isinstance(raw_data, list):
                self.logger.error("数据格式错误，期望列表格式")
                return False
            
            if not raw_data:
                self.logger.warning("数据为空，跳过保存")
                return False
            
            success_count = 0
            total_count = len(raw_data)
            
            for trade_record in raw_data:
                if not isinstance(trade_record, dict):
                    self.logger.warning("跳过非字典格式的记录")
                    continue
                
                date_value = self._format_date_field(trade_record.get('Date'))
                if not date_value:
                    self.logger.warning("跳过没有有效Date字段的记录")
                    continue
                
                save_data = trade_record.copy()
                save_data['Date'] = date_value
                save_data['product_type'] = self.product_type
                save_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                result = self.mgo.set(
                    key={'Date': date_value},
                    data=save_data
                )
                
                if result is not None:
                    success_count += 1
                    self.logger.debug(f"成功保存 {self.product_type} 日期为 {date_value} 的交易数据")
                else:
                    self.logger.warning(f"保存 {self.product_type} 日期为 {date_value} 的交易数据失败")
            
            if success_count > 0:
                self.logger.info(f"成功保存 {self.product_type} {success_count}/{total_count} 条逐日交易数据")
                return True
            else:
                self.logger.error(f"没有成功保存任何 {self.product_type} 数据")
                return False
                
        except Exception as e:
            self.logger.error(f"保存逐日交易数据时发生错误: {str(e)}")
            return False

    @decorate.exception_capture_close_datebase
    def run(self, task=None):
        """主运行方法"""
        self.logger.info(f"开始爬取FIS {self.product_type} 逐日交易数据")

        try:
            # 获取原始数据
            raw_data = self._fetch_daily_trade_data()
            
            if raw_data is None:
                self.logger.error(f"FIS {self.product_type} 逐日交易数据获取失败")
                return False
            
            # 保存数据
            save_success = self._save_daily_trade_data(raw_data)
            
            if save_success:
                self.logger.info(f"FIS {self.product_type} 逐日交易数据爬取成功")
                return True
            else:
                self.logger.error(f"FIS {self.product_type} 逐日交易数据保存失败")
                return False
                
        except Exception as e:
            self.logger.error(f"FIS {self.product_type} 逐日交易数据爬取过程中发生错误: {str(e)}")
            return False


class SpiderAllFisDailyTradeData:
    """
    爬取所有FIS逐日交易数据:
    同时获取C5TC、P4TC、P5TC三个产品类型的逐日交易数据。
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.product_types = ['C5TC', 'P4TC', 'P5TC']
        self.spiders = {}
        for product_type in self.product_types:
            try:
                self.spiders[product_type] = SpiderFisDailyTradeData(product_type)
                self.logger.info(f"初始化 {product_type} 爬虫成功")
            except Exception as e:
                self.logger.error(f"初始化 {product_type} 爬虫失败: {str(e)}")
                self.spiders[product_type] = None

    def run_all(self):
        """运行所有产品的数据爬取"""
        self.logger.info("开始爬取所有FIS逐日交易数据")
        results = {}
        for product_type in self.product_types:
            spider = self.spiders.get(product_type)
            if spider is None:
                self.logger.error(f"{product_type} 爬虫不可用，跳过")
                results[product_type] = False
                continue
            
            try:
                self.logger.info(f"开始爬取 {product_type} 数据")
                success = spider.run()
                results[product_type] = success
                if success:
                    self.logger.info(f"{product_type} 数据爬取完成")
                else:
                    self.logger.error(f"{product_type} 数据爬取失败")
            except Exception as e:
                self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
                results[product_type] = False
        
        # 统计结果
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        self.logger.info(f"所有FIS逐日交易数据爬取完成: {success_count}/{total_count} 个产品成功")
        
        # 打印详细结果
        for product_type, success in results.items():
            status = "成功" if success else "失败"
            self.logger.info(f"  {product_type}: {status}")
        
        return results

    def run_single(self, product_type: str):
        """运行单个产品的数据爬取"""
        product_type = product_type.upper()
        
        if product_type not in self.product_types:
            self.logger.error(f"不支持的产品类型: {product_type}")
            return False
        
        spider = self.spiders.get(product_type)
        if spider is None:
            self.logger.error(f"{product_type} 爬虫不可用")
            return False
        
        try:
            self.logger.info(f"开始爬取 {product_type} 数据")
            success = spider.run()
            self.logger.info(f"{product_type} 数据爬取完成")
            return success
        except Exception as e:
            self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
            return False

    def run(self, task=None):
        """运行所有产品的数据爬取（兼容main.py调用）"""
        return self.run_all()

    def close(self):
        """关闭所有爬虫连接"""
        for product_type, spider in self.spiders.items():
            if spider is not None:
                try:
                    spider.close()
                    self.logger.info(f"关闭 {product_type} 爬虫连接")
                except Exception as e:
                    self.logger.error(f"关闭 {product_type} 爬虫连接时发生错误: {str(e)}")
