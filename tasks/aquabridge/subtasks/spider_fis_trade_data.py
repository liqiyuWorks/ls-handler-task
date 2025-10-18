#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pkg.public.models import BaseModel
from pkg.public.decorator import decorate
import pymongo
import requests
import logging
from typing import Dict, Optional, Any


class SpiderFisTradeData(BaseModel):
    """
    爬取FIS交易数据:
    支持多种航运金融衍生品（如C5TC、P4TC、P5TC等）的交易信息获取和分表存储。
    每个产品类型使用独立的MongoDB集合进行存储，便于数据管理和查询。
    """

    def __init__(self, product_type: str = "C5TC"):
        """
        初始化FIS交易数据爬虫
        
        Args:
            product_type: 产品类型，如 'C5TC', 'P4TC', 'P5TC' 等
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)
        
        # 设置产品类型和对应的配置
        self.product_type = product_type.upper()
        self.product_configs = self._get_product_configs()
        
        if self.product_type not in self.product_configs:
            raise ValueError(f"不支持的产品类型: {self.product_type}。支持的类型: {list(self.product_configs.keys())}")
        
        # 获取当前产品的配置
        product_config = self.product_configs[self.product_type]
        
        # 设置MongoDB配置 - 每个产品使用独立的集合，以date为唯一键
        config = {
            'collection': f'fis_{self.product_type.lower()}_trade_data',
            'uniq_idx': [
                ('date', pymongo.ASCENDING)
            ]
        }
        
        # 尝试初始化MongoDB连接
        try:
            super(SpiderFisTradeData, self).__init__(config)
            if not hasattr(self, 'mgo') or self.mgo is None:
                self.mgo = None
        except (ValueError, TypeError, KeyError, pymongo.errors.PyMongoError):
            self.config = config
            self.mgo = None
        
        # 设置API配置
        self.api_url = product_config['api_url']
        self.auth_token = product_config['auth_token']

    def _get_product_configs(self) -> Dict[str, Dict[str, str]]:
        """获取所有支持的产品配置"""
        return {
            'C5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods',
                'auth_token': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjA4MDQwMjUsImV4cCI6MTc2MDg5MDQyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.z7ClFGOP75GzMeqC-t9tryJ2CWl8BW2pFEnJMjTBbR1T6kOIgd5mkKbKaVJehKamNDRhp4qR13OaKu7h5zAl87NqpOy4I50wAmPCMhPf9PtqRbibWeGVoem-6mwnGfprdFQGYS3cQ6mRmuoRJxHfhgyIAMIcBcW01ifzUKgat5eZK1T2EOJYCHUDuIALXX-gCDnDX9eWkiehWASSWTo8oGqdRi-qB3XGI1O0rqGRO7fEQlGKVDvbZYBJIXxR9Y8Nk9F8YiemHTrD5_825FDVl4_acc4OVw-4OyoVVDrVaH3NRWz8fex_A8lP7G0FKZLToI9I80J1-ZsuOQgRlHVLWg',
                'description': '中国铁矿石期货合约'
            },
            'P4TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/12/periods',
                'auth_token': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjA4MDQwMjUsImV4cCI6MTc2MDg5MDQyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.z7ClFGOP75GzMeqC-t9tryJ2CWl8BW2pFEnJMjTBbR1T6kOIgd5mkKbKaVJehKamNDRhp4qR13OaKu7h5zAl87NqpOy4I50wAmPCMhPf9PtqRbibWeGVoem-6mwnGfprdFQGYS3cQ6mRmuoRJxHfhgyIAMIcBcW01ifzUKgat5eZK1T2EOJYCHUDuIALXX-gCDnDX9eWkiehWASSWTo8oGqdRi-qB3XGI1O0rqGRO7fEQlGKVDvbZYBJIXxR9Y8Nk9F8YiemHTrD5_825FDVl4_acc4OVw-4OyoVVDrVaH3NRWz8fex_A8lP7G0FKZLToI9I80J1-ZsuOQgRlHVLWg',
                'description': '巴拿马型散货船4条航线平均租金'
            },
            'P5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/39/periods',
                'auth_token': 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjA4MDQwMjUsImV4cCI6MTc2MDg5MDQyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.z7ClFGOP75GzMeqC-t9tryJ2CWl8BW2pFEnJMjTBbR1T6kOIgd5mkKbKaVJehKamNDRhp4qR13OaKu7h5zAl87NqpOy4I50wAmPCMhPf9PtqRbibWeGVoem-6mwnGfprdFQGYS3cQ6mRmuoRJxHfhgyIAMIcBcW01ifzUKgat5eZK1T2EOJYCHUDuIALXX-gCDnDX9eWkiehWASSWTo8oGqdRi-qB3XGI1O0rqGRO7fEQlGKVDvbZYBJIXxR9Y8Nk9F8YiemHTrD5_825FDVl4_acc4OVw-4OyoVVDrVaH3NRWz8fex_A8lP7G0FKZLToI9I80J1-ZsuOQgRlHVLWg',
                'description': '巴拿马型散货船5条航线平均租金'
            }
        }

    def _get_api_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        return {
            'authorization': f'Bearer {self.auth_token}',
            'content-type': 'application/json'
        }

    def _fetch_trade_data(self, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        获取交易数据
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            API响应数据或None
        """
        for attempt in range(max_retries):
            try:
                headers = self._get_api_headers()
                response = requests.get(
                    url=self.api_url,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    self.logger.error("%s API认证失败", self.product_type)
                    return None
                    
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    self.logger.error("%s API请求失败: %s", self.product_type, str(e))
            except (ValueError, TypeError, KeyError) as e:
                if attempt == max_retries - 1:
                    self.logger.error("%s 数据处理失败: %s", self.product_type, str(e))
                
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)
        
        return None

    def _format_trade_data(self, raw_data: Dict[str, Any], date: str = None) -> Dict[str, Any]:
        """
        格式化交易数据，支持分层存储
        将多条合约数据合成为一条以date为唯一键的分层数据
        
        Args:
            raw_data: 原始API数据
            date: 数据日期（可选，如果不提供则从API数据中提取）
            
        Returns:
            格式化后的分层数据，包含所有合约信息
        """
        try:
            # 提取期间数据
            periods_data = []
            if isinstance(raw_data, dict) and 'periodsForProductList' in raw_data:
                periods_data = raw_data['periodsForProductList']
            elif isinstance(raw_data, list):
                periods_data = raw_data
            else:
                # 如果数据格式不符合预期，将整个数据作为一个期间处理
                periods_data = [raw_data] if raw_data else []
            
            # 从API数据中提取实际日期
            if not date and periods_data:
                # 使用第一个合约的日期作为数据日期
                first_period = periods_data[0]
                if isinstance(first_period, dict) and 'date' in first_period:
                    api_date = first_period['date']
                    # 提取日期部分（去掉时间部分）
                    if 'T' in api_date:
                        date = api_date.split('T')[0]
                    else:
                        date = api_date
                else:
                    # 如果没有找到日期，使用当前日期
                    date = datetime.now().strftime('%Y-%m-%d')
            
            # 如果仍然没有日期，使用当前日期
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # 处理所有合约数据
            contracts = []
            contract_types = {}
            price_stats = {
                'total_contracts': 0,
                'monthly_contracts': 0,
                'quarterly_contracts': 0,
                'calendar_contracts': 0,
                'bid_price_range': {'min': float('inf'), 'max': float('-inf')},
                'offer_price_range': {'min': float('inf'), 'max': float('-inf')},
                'change_stats': {'up': 0, 'down': 0, 'unchanged': 0}
            }
            
            for period in periods_data:
                if not isinstance(period, dict):
                    continue
                    
                # 提取合约信息
                contract_info = self._extract_contract_info(period)
                if not contract_info:
                    continue
                
                # 创建合约记录
                contract_record = {
                    'period_id': period.get('periodId', len(contracts)),
                    'contract': contract_info['contract'],
                    'contract_display': contract_info['contract_display'],
                    'contract_type': contract_info['contract_type'],
                    'bid_price': contract_info['bid_price'],
                    'offer_price': contract_info['offer_price'],
                    'mid_price': contract_info['mid_price'],
                    'change_value': contract_info['change_value'],
                    'change_percentage': contract_info['change_percentage'],
                    'change_direction': contract_info['change_direction'],
                    'period_type': period.get('type', ''),
                    'description': period.get('description', {}),
                    'label': period.get('label', {}),
                    'period_date': period.get('date', ''),
                    'updated_date': period.get('updatedDate', ''),
                    'raw_data': period
                }
                
                contracts.append(contract_record)
                
                # 统计合约类型
                contract_type = contract_info['contract_type']
                contract_types[contract_type] = contract_types.get(contract_type, 0) + 1
                
                # 更新价格统计
                price_stats['total_contracts'] += 1
                if contract_type == 'monthly':
                    price_stats['monthly_contracts'] += 1
                elif contract_type == 'quarterly':
                    price_stats['quarterly_contracts'] += 1
                elif contract_type == 'calendar':
                    price_stats['calendar_contracts'] += 1
                
                # 更新价格范围
                bid_price = contract_info['bid_price']
                offer_price = contract_info['offer_price']
                if bid_price is not None:
                    price_stats['bid_price_range']['min'] = min(price_stats['bid_price_range']['min'], bid_price)
                    price_stats['bid_price_range']['max'] = max(price_stats['bid_price_range']['max'], bid_price)
                if offer_price is not None:
                    price_stats['offer_price_range']['min'] = min(price_stats['offer_price_range']['min'], offer_price)
                    price_stats['offer_price_range']['max'] = max(price_stats['offer_price_range']['max'], offer_price)
                
                # 更新变动统计
                change_direction = contract_info['change_direction']
                if change_direction in price_stats['change_stats']:
                    price_stats['change_stats'][change_direction] += 1
            
            # 处理价格范围中的无穷大值
            if price_stats['bid_price_range']['min'] == float('inf'):
                price_stats['bid_price_range'] = {'min': 0, 'max': 0}
            if price_stats['offer_price_range']['min'] == float('inf'):
                price_stats['offer_price_range'] = {'min': 0, 'max': 0}
            
            # 创建分层数据记录
            formatted_record = {
                'product_type': self.product_type,
                'date': date,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'fis_live_api',
                'total_contracts': len(contracts),
                'contracts': contracts,
                'contract_types': contract_types,
                'price_statistics': price_stats,
                'raw_data': raw_data
            }
            
            return formatted_record
            
        except (ValueError, TypeError, KeyError) as e:
            self.logger.error("格式化 %s 数据失败: %s", self.product_type, str(e))
            # 返回一个错误记录
            return {
                'product_type': self.product_type,
                'date': date,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'fis_live_api',
                'total_contracts': 0,
                'contracts': [],
                'contract_types': {},
                'price_statistics': {},
                'raw_data': raw_data,
                'error': str(e)
            }

    def _extract_contract_info(self, period: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从期间数据中提取合约信息
        
        Args:
            period: 期间数据
            
        Returns:
            提取的合约信息字典
        """
        try:
            # 提取合约名称
            contract = period.get('description', {}).get('en', '')
            if not contract:
                return None
            
            # 提取价格信息
            bid_price = period.get('bidPrice')
            offer_price = period.get('offerPrice')
            mid_price = period.get('midPrice')
            
            # 计算变动信息
            change_info = self._calculate_change_info(period)
            
            # 确定合约类型
            contract_type = self._determine_contract_type(contract)
            
            return {
                'contract': contract,
                'contract_display': contract,
                'contract_type': contract_type,
                'bid_price': bid_price,
                'offer_price': offer_price,
                'mid_price': mid_price,
                'change_value': change_info['value'],
                'change_percentage': change_info['percentage'],
                'change_direction': change_info['direction']
            }
            
        except (ValueError, TypeError, KeyError):
            return None

    def _calculate_change_info(self, period: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算变动信息
        
        Args:
            period: 期间数据
            
        Returns:
            变动信息字典
        """
        try:
            # 从原始数据中提取变动信息
            # 优先使用收盘变动数据，如果没有则使用日内变动数据
            close_movement_price = period.get('closeMovementPrice', 0)
            close_movement_change = period.get('closeMovementChange', 0.0)
            close_movement_direction = period.get('closeMovementDirection', 0)
            
            intraday_movement_price = period.get('intradayMovementPrice', 0)
            intraday_movement_change = period.get('intradayMovementChange', 0.0)
            intraday_movement_direction = period.get('intradayMovementDirection', 0)
            
            # 优先使用收盘变动数据
            if close_movement_price != 0:
                change_value = close_movement_price
                change_percentage = close_movement_change
                movement_direction = close_movement_direction
            elif intraday_movement_price != 0:
                change_value = intraday_movement_price
                change_percentage = intraday_movement_change
                movement_direction = intraday_movement_direction
            else:
                change_value = 0
                change_percentage = 0.0
                movement_direction = 0
            
            # 根据变动方向确定方向字符串
            if movement_direction == 1:  # 上涨
                direction = 'up'
            elif movement_direction == -1:  # 下跌
                direction = 'down'
            else:  # 无变动或未知
                direction = 'unchanged'
            
            return {
                'value': change_value,
                'percentage': change_percentage,
                'direction': direction
            }
            
        except (ValueError, TypeError, KeyError):
            return {
                'value': 0,
                'percentage': 0.0,
                'direction': 'unchanged'
            }

    def _determine_contract_type(self, contract: str) -> str:
        """
        确定合约类型
        
        Args:
            contract: 合约名称
            
        Returns:
            合约类型
        """
        contract_lower = contract.lower()
        
        if any(month in contract_lower for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                                    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']):
            return 'monthly'
        elif any(quarter in contract_lower for quarter in ['q1', 'q2', 'q3', 'q4']):
            return 'quarterly'
        elif 'cal' in contract_lower:
            return 'calendar'
        else:
            return 'other'

    def _save_trade_data(self, formatted_record: Dict[str, Any]) -> bool:
        """
        保存分层交易数据到MongoDB
        
        Args:
            formatted_record: 格式化后的分层数据记录
            
        Returns:
            保存是否成功
        """
        try:
            if not hasattr(self, 'mgo') or self.mgo is None or not formatted_record:
                return False
                
            result = self.mgo.set(
                key={'date': formatted_record['date']},
                data=formatted_record
            )
            return result is not None
                
        except (ValueError, TypeError, KeyError, pymongo.errors.PyMongoError) as e:
            self.logger.error("保存 %s 数据失败: %s", self.product_type, str(e))
            return False

    @decorate.exception_capture_close_datebase
    def run(self):
        """主运行方法"""
        raw_data = self._fetch_trade_data()
        
        if raw_data is not None:
            formatted_record = self._format_trade_data(raw_data)
            save_success = self._save_trade_data(formatted_record)
            
            if not save_success:
                self.logger.error("%s 数据保存失败", self.product_type)
        else:
            self.logger.error("%s 数据获取失败", self.product_type)


class SpiderAllFisTradeData:
    """
    爬取所有FIS交易数据:
    支持C5TC、P4TC、P5TC等所有产品类型的交易信息获取和分表存储。
    """
    
    def __init__(self):
        """初始化所有FIS交易数据爬虫"""
        self.logger = logging.getLogger(__name__)
        self.product_types = ['C5TC', 'P4TC', 'P5TC']
        self.spiders = {}
        
        # 为每个产品类型创建爬虫实例
        for product_type in self.product_types:
            try:
                self.spiders[product_type] = SpiderFisTradeData(product_type)
                self.logger.info("初始化 %s 爬虫成功", product_type)
            except (ValueError, TypeError, KeyError) as e:
                self.logger.error("初始化 %s 爬虫失败: %s", product_type, str(e))
                self.spiders[product_type] = None
    
    def run(self):
        """主运行方法 - 获取所有产品类型的数据"""
        self.logger.info("开始爬取所有FIS交易数据")
        
        success_count = 0
        total_count = len(self.product_types)
        
        for product_type in self.product_types:
            try:
                self.logger.info("正在处理 %s 数据...", product_type)
                
                spider = self.spiders.get(product_type)
                if spider is None:
                    self.logger.error("%s 爬虫未初始化，跳过", product_type)
                    continue
                
                # 获取原始数据
                raw_data = spider._fetch_trade_data()
                if raw_data is None:
                    self.logger.error("%s 数据获取失败", product_type)
                    continue
                
                # 格式化数据为分层结构
                formatted_record = spider._format_trade_data(raw_data)
                if formatted_record is None:
                    self.logger.error("%s 数据格式化失败", product_type)
                    continue
                
                # 保存分层数据
                save_success = spider._save_trade_data(formatted_record)
                if save_success:
                    self.logger.info("%s 数据获取和保存成功", product_type)
                    success_count += 1
                else:
                    self.logger.error("%s 数据保存失败", product_type)
                
            except (ValueError, TypeError, KeyError, requests.exceptions.RequestException) as e:
                self.logger.error("%s 处理失败: %s", product_type, str(e))
            finally:
                # 关闭爬虫连接
                try:
                    if spider:
                        spider.close()
                except (ValueError, TypeError, KeyError):
                    pass
        
        self.logger.info("所有FIS交易数据爬取完成: %d/%d 成功", success_count, total_count)
        return success_count == total_count
    
    def close(self):
        """关闭所有爬虫连接"""
        for spider in self.spiders.values():
            try:
                if spider:
                    spider.close()
            except (ValueError, TypeError, KeyError):
                pass
