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

    def __init__(self, product_type: str = "C5TC", auth_token: str = None):
        """
        初始化FIS交易数据爬虫

        Args:
            product_type: 产品类型，如 'C5TC', 'P4TC', 'P5TC' 等
            auth_token: 认证token，如果提供则直接使用，否则从Redis获取
        """
        # 设置日志
        self.logger = logging.getLogger(__name__)

        # 设置产品类型
        self.product_type = product_type.upper()

        # 设置MongoDB配置 - 每个产品使用独立的集合，以date为唯一键
        config = {
            'cache_rds': True,
            'collection': f'fis_{self.product_type.lower()}_trade_data',
            'uniq_idx': [
                ('date', pymongo.ASCENDING)
            ]
        }

        # 先初始化数据库连接（包括Redis）
        try:
            super(SpiderFisTradeData, self).__init__(config)
            if not hasattr(self, 'mgo') or self.mgo is None:
                self.mgo = None
        except (ValueError, TypeError, KeyError, pymongo.errors.PyMongoError):
            self.config = config
            self.mgo = None

        # 在Redis连接初始化后获取产品配置
        self.product_configs = self._get_product_configs(auth_token)

        if self.product_type not in self.product_configs:
            raise ValueError(
                f"不支持的产品类型: {self.product_type}。支持的类型: {list(self.product_configs.keys())}")

        # 获取当前产品的配置
        product_config = self.product_configs[self.product_type]

        # 设置API配置
        self.api_url = product_config['api_url']
        self.auth_token = product_config['auth_token']

    def _get_product_configs(self, auth_token: str = None) -> Dict[str, Dict[str, str]]:
        """获取所有支持的产品配置"""
        # 如果提供了auth_token则直接使用，否则从Redis获取
        if auth_token is None:
            auth_token = self._get_fis_auth_token()

        return {
            'C5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods',
                'auth_token': auth_token,
                'description': '中国铁矿石期货合约'
            },
            'P4TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/12/periods',
                'auth_token': auth_token,
                'description': '巴拿马型散货船4条航线平均租金'
            },
            'P5TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/39/periods',
                'auth_token': auth_token,
                'description': '巴拿马型散货船5条航线平均租金'
            }
        }

    def _get_fis_auth_token(self):
        """从Redis缓存中获取fis-live的auth_token"""
        try:
            if hasattr(self, 'cache_rds') and self.cache_rds:
                # 首先检查键是否存在
                if not self.cache_rds.exists("fis-live"):
                    self.logger.warning("Redis中不存在fis-live键")
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
                        self.logger.info(
                            f"fis-live hash中的所有字段: {list(all_fields.keys())}")

                        # 尝试常见的token字段名
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                self.logger.info(
                                    f"从hash字段 '{field_name}' 获取到token")
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
                    self.logger.warning("Redis缓存中未找到有效的fis-live auth_token")
            else:
                self.logger.warning("Redis缓存连接不可用")
        except Exception as e:
            self.logger.error("从Redis获取fis-live auth_token失败: %s", str(e))

        # 如果Redis中没有找到token，使用环境变量作为备选
        return self._get_fallback_token()

    def _get_fallback_token(self):
        """获取备选token"""
        fallback_token = os.getenv('FIS_AUTH_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEwMjU0MjUsImV4cCI6MTc2MTExMTgyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.urQaNPtTQYXm-c_nTpEhDY_tVINtCKpdg7X04EFsujSNU1ie1GD-_tjtsg9Ge7k4VkfYDt3Eg9lzIARqFvDGqwb5dggPU8AL9anIYcrcPY-fMVX7biVPTLlIl7t_3VY7Z-j9JQDUge9HS2lZFkDGMP4LJpu2tzZrQ1JiQ7oeVsvYLwgia8HgKtYvUM6iVkrACnOZTmDUEcMA2kn9Q1c68tDGJvbg7cmPasVDrzRx_2fKlR_OEbVCt78YEbCVs_hRlvr4NFPu2Ck6kkpLB2joKl1-p-bLQMxPGhydXKZsPjlMQ_W8SXfZwMKcfcpg9Ti4nC-Kt9gJcfOwW2q764AK-w')
        self.logger.info("使用环境变量中的FIS_AUTH_TOKEN作为备选")
        return fallback_token

    def _get_api_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        return {
            'authorization': f'{self.auth_token}',
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
                    self.logger.error("%s API请求失败: %s",
                                      self.product_type, str(e))
            except (ValueError, TypeError, KeyError) as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        "%s 数据处理失败: %s", self.product_type, str(e))

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
                contract_types[contract_type] = contract_types.get(
                    contract_type, 0) + 1

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
                    price_stats['bid_price_range']['min'] = min(
                        price_stats['bid_price_range']['min'], bid_price)
                    price_stats['bid_price_range']['max'] = max(
                        price_stats['bid_price_range']['max'], bid_price)
                if offer_price is not None:
                    price_stats['offer_price_range']['min'] = min(
                        price_stats['offer_price_range']['min'], offer_price)
                    price_stats['offer_price_range']['max'] = max(
                        price_stats['offer_price_range']['max'], offer_price)

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
            intraday_movement_change = period.get(
                'intradayMovementChange', 0.0)
            intraday_movement_direction = period.get(
                'intradayMovementDirection', 0)

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

        # 先获取一次auth_token，避免重复获取
        self.auth_token = self._get_fis_auth_token_once()

        # 为每个产品类型创建爬虫实例
        for product_type in self.product_types:
            try:
                self.spiders[product_type] = SpiderFisTradeData(
                    product_type, auth_token=self.auth_token)
                self.logger.info("初始化 %s 爬虫成功", product_type)
            except (ValueError, TypeError, KeyError) as e:
                self.logger.error("初始化 %s 爬虫失败: %s", product_type, str(e))
                self.spiders[product_type] = None

    def _get_fis_auth_token_once(self):
        """只获取一次auth_token，避免重复操作"""
        try:
            # 创建临时Redis连接来获取token
            import redis
            import os

            host = os.getenv('CACHE_REDIS_HOST', '127.0.0.1')
            port = int(os.getenv('CACHE_REDIS_PORT', '6379'))
            password = os.getenv('CACHE_REDIS_PASSWORD', None)
            cache_rds = redis.Redis(host=host, port=port, db=0, password=password,
                                    decode_responses=True, health_check_interval=30)

            # 检查键是否存在
            if not cache_rds.exists("fis-live"):
                self.logger.warning("Redis中不存在fis-live键")
                return self._get_fallback_token()

            # 检查键的类型
            key_type = cache_rds.type("fis-live")
            self.logger.info(f"Redis中fis-live键的类型: {key_type}")

            token = None

            if key_type == 'hash':
                # 如果是hash类型，尝试获取auth_token字段
                token = cache_rds.hget("fis-live", "auth_token")
                if not token:
                    # 如果没有auth_token字段，尝试获取其他可能的字段
                    all_fields = cache_rds.hgetall("fis-live")
                    self.logger.info(
                        f"fis-live hash中的所有字段: {list(all_fields.keys())}")

                    # 尝试常见的token字段名
                    for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                        if field_name in all_fields:
                            token = all_fields[field_name]
                            self.logger.info(
                                f"从hash字段 '{field_name}' 获取到token")
                            break

            elif key_type == 'string':
                # 如果是string类型，直接获取值
                token = cache_rds.get("fis-live")
                self.logger.info("从string类型的fis-live键获取到token")

            elif key_type == 'list':
                # 如果是list类型，获取第一个元素
                token = cache_rds.lindex("fis-live", 0)
                self.logger.info("从list类型的fis-live键获取到token")

            else:
                self.logger.warning(f"不支持的Redis键类型: {key_type}")

            if token:
                self.logger.info("从Redis缓存中获取到fis-live auth_token")
                return token
            else:
                self.logger.warning("Redis缓存中未找到有效的fis-live auth_token")
                return self._get_fallback_token()

        except Exception as e:
            self.logger.error("从Redis获取fis-live auth_token失败: %s", str(e))
            return self._get_fallback_token()
        finally:
            # 关闭临时连接
            try:
                cache_rds.close()
            except:
                pass

    def _get_fallback_token(self):
        """获取备选token"""
        fallback_token = os.getenv('FIS_AUTH_TOKEN', 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEwMjU0MjUsImV4cCI6MTc2MTExMTgyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.urQaNPtTQYXm-c_nTpEhDY_tVINtCKpdg7X04EFsujSNU1ie1GD-_tjtsg9Ge7k4VkfYDt3Eg9lzIARqFvDGqwb5dggPU8AL9anIYcrcPY-fMVX7biVPTLlIl7t_3VY7Z-j9JQDUge9HS2lZFkDGMP4LJpu2tzZrQ1JiQ7oeVsvYLwgia8HgKtYvUM6iVkrACnOZTmDUEcMA2kn9Q1c68tDGJvbg7cmPasVDrzRx_2fKlR_OEbVCt78YEbCVs_hRlvr4NFPu2Ck6kkpLB2joKl1-p-bLQMxPGhydXKZsPjlMQ_W8SXfZwMKcfcpg9Ti4nC-Kt9gJcfOwW2q764AK-w')
        self.logger.info("使用环境变量中的FIS_AUTH_TOKEN作为备选")
        return fallback_token

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


class SpiderFisMarketTrades(BaseModel):
    """
    爬取FIS市场交易数据（已执行交易）:
    获取FIS平台上的实际执行交易信息，用于市场分析和决策支持。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_url = 'https://livepricing-prod2.azurewebsites.net/api/v1/executedTrade'
        self.collection_name = 'fis_market_trades'

        # 数据库配置
        self.uniq_idx = [('tradedDate', pymongo.ASCENDING)]
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
                    self.logger.warning(
                        "Redis缓存中未找到有效的fis-live auth_token，使用fallback token")
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
                print(headers)

                # 添加查询参数获取所有产品的交易数据
                params = {
                    'productIds': [1, 12, 90, 39, 0]  # 对应C5TC、P4TC、P5TC等产品
                }

                self.logger.info(f"正在请求市场交易API: {self.api_url}")
                self.logger.info(f"查询参数: {params}")

                response = requests.get(
                    self.api_url, headers=headers, params=params, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(
                        f"成功获取市场交易数据，记录数: {len(data) if isinstance(data, list) else 'N/A'}")
                    return data
                elif response.status_code == 401:
                    self.logger.error("市场交易API认证失败 (401) - Token可能已过期")
                    return None
                else:
                    self.logger.warning(
                        f"市场交易API请求失败，状态码: {response.status_code}")
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
                trade_record['created_at'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')

                self.mgo.set(None, data=trade_record)

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

            self._save_market_trades(raw_data)

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
            raise ValueError(
                f"不支持的产品类型: {self.product_type}。支持的类型: {list(self.product_configs.keys())}")

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
                        self.logger.info(
                            f"fis-live hash中的所有字段: {list(all_fields.keys())}")

                        # 尝试常见的token字段名
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                self.logger.info(
                                    f"从hash字段 '{field_name}' 获取到token")
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
                    self.logger.warning(
                        "Redis缓存中未找到有效的fis-live auth_token，使用fallback token")
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
                self.logger.info(
                    f"正在请求 {self.product_type} API: {self.api_url}")
                self.logger.debug(f"请求头: {headers}")

                response = requests.get(
                    self.api_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(
                        f"成功获取 {self.product_type} 数据，记录数: {len(data) if isinstance(data, list) else 'N/A'}")
                    return data
                elif response.status_code == 401:
                    self.logger.error(
                        f"{self.product_type} API认证失败 (401) - Token可能已过期")
                    self.logger.error(
                        "请运行 'python update_fis_token.py' 更新token")
                    return None
                elif response.status_code == 404:
                    self.logger.error(
                        f"{self.product_type} API接口不存在 (404): {self.api_url}")
                    return None
                else:
                    self.logger.warning(
                        f"{self.product_type} API请求失败，状态码: {response.status_code}")
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
                        dt = datetime.fromisoformat(
                            date_value.replace('Z', '+00:00'))
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
                save_data['created_at'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')

                result = self.mgo.set(
                    key={'Date': date_value},
                    data=save_data
                )

                if result is not None:
                    success_count += 1
                    self.logger.debug(
                        f"成功保存 {self.product_type} 日期为 {date_value} 的交易数据")
                else:
                    self.logger.warning(
                        f"保存 {self.product_type} 日期为 {date_value} 的交易数据失败")

            if success_count > 0:
                self.logger.info(
                    f"成功保存 {self.product_type} {success_count}/{total_count} 条逐日交易数据")
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
            self.logger.error(
                f"FIS {self.product_type} 逐日交易数据爬取过程中发生错误: {str(e)}")
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
                self.spiders[product_type] = SpiderFisDailyTradeData(
                    product_type)
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

        self.logger.info(
            f"所有FIS逐日交易数据爬取完成: {success_count}/{total_count} 个产品成功")

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
