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
        """
        初始化FIS交易数据爬虫

        Args:
            product_type: 产品类型，如 'C5TC', 'P4TC', 'P5TC' 等
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
        self.product_configs = self._get_product_configs()

        if self.product_type not in self.product_configs:
            raise ValueError(
                f"不支持的产品类型: {self.product_type}。支持的类型: {list(self.product_configs.keys())}")

        # 获取当前产品的配置
        product_config = self.product_configs[self.product_type]

        # 设置API配置
        self.api_url = product_config['api_url']
        self.auth_token = product_config['auth_token']

    def _get_product_configs(self) -> Dict[str, Dict[str, str]]:
        """获取所有支持的产品配置"""
        # 从Redis获取auth_token
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
            },
            'C5': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/25/periods',
                'auth_token': auth_token,
                'description': 'C5航线期货合约'
            },
            'S10TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/28/periods',
                'auth_token': auth_token,
                'description': 'S10TC期货合约'
            },
            'HS7TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/product/87/periods',
                'auth_token': auth_token,
                'description': 'HS7TC期货合约'
            }
        }

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

                token = None

                if key_type == 'hash':
                    # 如果是hash类型，尝试获取auth_token字段
                    token = self.cache_rds.hget("fis-live", "auth_token")
                    if not token:
                        # 如果没有auth_token字段，尝试获取其他可能的字段
                        all_fields = self.cache_rds.hgetall("fis-live")
                        # 尝试常见的token字段名
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                break

                elif key_type == 'string':
                    # 如果是string类型，直接获取值
                    token = self.cache_rds.get("fis-live")

                elif key_type == 'list':
                    # 如果是list类型，获取第一个元素
                    token = self.cache_rds.lindex("fis-live", 0)

                else:
                    self.logger.warning(f"不支持的Redis键类型: {key_type}")

                if token:
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
        fallback_token = os.getenv('FIS_AUTH_TOKEN')
        if fallback_token:
            self.logger.info("使用环境变量中的FIS_AUTH_TOKEN")
            return fallback_token

        # 如果没有环境变量，使用硬编码的token（仅用于测试）
        hardcoded_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEwMjU0MjUsImV4cCI6MTc2MTExMTgyNSwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.urQaNPtTQYXm-c_nTpEhDY_tVINtCKpdg7X04EFsujSNU1ie1GD-_tjtsg9Ge7k4VkfYDt3Eg9lzIARqFvDGqwb5dggPU8AL9anIYcrcPY-fMVX7biVPTLlIl7t_3VY7Z-j9JQDUge9HS2lZFkDGMP4LJpu2tzZrQ1JiQ7oeVsvYLwgia8HgKtYvUM6iVkrACnOZTmDUEcMA2kn9Q1c68tDGJvbg7cmPasVDrzRx_2fKlR_OEbVCt78YEbCVs_hRlvr4NFPu2Ck6kkpLB2joKl1-p-bLQMxPGhydXKZsPjlMQ_W8SXfZwMKcfcpg9Ti4nC-Kt9gJcfOwW2q764AK-w"
        self.logger.warning("使用硬编码的fallback token（仅用于测试）")
        return hardcoded_token

    def _get_api_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        # 确保token格式正确，如果没有Bearer前缀则添加
        token = self.auth_token
        if token and not token.startswith('Bearer '):
            token = f'Bearer {token}'
        
        return {
            'authorization': token,
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
        try:
            raw_data = self._fetch_trade_data()

            if raw_data is not None:
                formatted_record = self._format_trade_data(raw_data)
                save_success = self._save_trade_data(formatted_record)

                if save_success:
                    self.logger.info("%s 数据获取和保存成功", self.product_type)
                    return True
                else:
                    self.logger.error("%s 数据保存失败", self.product_type)
                    return False
            else:
                self.logger.error("%s 数据获取失败", self.product_type)
                return False
        except Exception as e:
            self.logger.error("%s 爬取过程中发生错误: %s", self.product_type, str(e))
            return False


class SpiderAllFisTradeData:
    """
    爬取所有FIS交易数据:
    支持C5TC、P4TC、P5TC、C5、S10TC、HS7TC等所有产品类型的交易信息获取和分表存储。
    """

    def __init__(self):
        """初始化所有FIS交易数据爬虫"""
        self.logger = logging.getLogger(__name__)
        self.product_types = ['C5TC', 'P4TC', 'P5TC', 'C5', 'S10TC', 'HS7TC']
        # 不再在初始化时创建爬虫实例，而是在每次运行时动态创建
        # 这样可以确保每次都从Redis获取最新的token

    def run_all(self):
        """运行所有产品的数据爬取"""
        self.logger.info("开始爬取 FIS 交易数据")
        results = {}

        # 每次运行时重新创建爬虫实例，确保从Redis动态获取最新token
        for product_type in self.product_types:
            spider = None
            try:
                # 创建新的爬虫实例，每次都会从Redis获取最新的token
                spider = SpiderFisTradeData(product_type)

                # run() 方法有装饰器 @decorate.exception_capture_close_datebase
                # 会自动在 finally 块中调用 close()，确保数据库连接正确关闭
                success = spider.run()
                results[product_type] = success

            except Exception as e:
                self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
                results[product_type] = False
                # 如果异常发生在创建实例后但 run() 之前，需要手动关闭
                if spider is not None:
                    try:
                        spider.close()
                    except Exception as close_e:
                        self.logger.debug(f"关闭 {product_type} 爬虫连接时出错: {close_e}")

        # 统计结果
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        # 打印结果摘要
        for product_type, success in results.items():
            status = "✓" if success else "✗"
            self.logger.info(f"  {product_type}: {status}")

        self.logger.info(f"完成: {success_count}/{total_count}")

        return results

    def run_single(self, product_type: str):
        """运行单个产品的数据爬取"""
        product_type = product_type.upper()

        if product_type not in self.product_types:
            self.logger.error(f"不支持的产品类型: {product_type}")
            return False

        spider = None
        try:
            # 每次运行时创建新的爬虫实例，确保从Redis获取最新的token
            spider = SpiderFisTradeData(product_type)

            # run() 方法有装饰器 @decorate.exception_capture_close_datebase
            # 会自动在 finally 块中调用 close()，确保数据库连接正确关闭
            success = spider.run()
            return success

        except Exception as e:
            self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
            # 如果异常发生在创建实例后但 run() 之前，需要手动关闭
            if spider is not None:
                try:
                    spider.close()
                except Exception as close_e:
                    self.logger.debug(f"关闭 {product_type} 爬虫连接时出错: {close_e}")
            return False

    def run(self, task=None):
        """运行所有产品的数据爬取（兼容main.py调用）"""
        return self.run_all()

    def close(self):
        """关闭所有爬虫连接（已优化为每次运行时动态创建，无需关闭）"""
        # 爬虫实例在每次运行时动态创建并立即关闭，无需在此处处理


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
        self.uniq_idx = [
            ('tradedDate', pymongo.ASCENDING),
            ('sourceType', pymongo.ASCENDING),
            ('periodName', pymongo.ASCENDING),
            ('productName', pymongo.ASCENDING)
        ]
        config = {
            'cache_rds': True,
            'collection': self.collection_name,
            'uniq_idx': self.uniq_idx
        }
        super(SpiderFisMarketTrades, self).__init__(config)

    def _get_fis_auth_token(self):
        """获取FIS认证token"""
        try:
            # 如果Redis连接不存在，尝试重新建立连接
            if not self.cache_rds:
                self.logger.warning("Redis连接不存在，尝试重新建立连接")
                try:
                    self.cache_rds = self.get_cache_rds()
                    if not self.cache_rds:
                        self.logger.error("无法重新建立Redis连接")
                        return None
                except Exception as e:
                    self.logger.error(f"重新建立Redis连接失败: {str(e)}")
                    return None

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
                self.logger.warning("Redis中未找到fis-live token")
                return None
                
        except Exception as e:
            self.logger.error(f"获取FIS认证token时发生错误: {str(e)}")
            return None

    def _get_api_headers(self):
        """获取API请求头"""
        token = self._get_fis_auth_token()
        if not token:
            self.logger.error("无法获取FIS认证token")
            return {'Authorization': 'None'}
            
        return {'Authorization': token}

    def _fetch_market_trades(self, max_retries=3):
        """获取市场交易数据"""
        for attempt in range(max_retries):
            try:
                headers = self._get_api_headers()
                self.logger.debug(f"API请求头: {headers}")

                # 检查token是否有效
                if headers.get('Authorization') == 'None':
                    self.logger.error("Token无效，无法继续请求")
                    if attempt < max_retries - 1:
                        self.logger.info(f"等待重试 {attempt + 1}/{max_retries}")
                        import time
                        time.sleep(2)  # 等待2秒后重试
                        continue
                    return None

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
                    self.logger.error(f"请求URL: {self.api_url}")
                    self.logger.error(f"请求头: {headers}")
                    self.logger.error(f"查询参数: {params}")
                    self.logger.error(f"响应状态码: {response.status_code}")
                    self.logger.error(f"响应头: {dict(response.headers)}")
                    try:
                        response_text = response.text
                        self.logger.error(f"响应内容: {response_text}")
                    except Exception as e:
                        self.logger.error(f"无法读取响应内容: {str(e)}")

                    # 检查token来源和有效性
                    token = self._get_fis_auth_token()
                    if token:
                        self.logger.error(
                            f"当前使用的Token: {token[:50]}...{token[-20:] if len(token) > 70 else token}")
                        # 尝试解析JWT token（如果可能）
                        try:
                            import base64
                            import json
                            # JWT token通常有三部分，用.分隔
                            parts = token.split('.')
                            if len(parts) == 3:
                                # 解码payload部分（第二部分）
                                payload = parts[1]
                                # 添加padding如果需要
                                payload += '=' * (4 - len(payload) % 4)
                                decoded = base64.b64decode(payload)
                                payload_data = json.loads(decoded)
                                self.logger.error(
                                    f"Token payload信息: {payload_data}")
                        except Exception as e:
                            self.logger.error(f"无法解析Token payload: {str(e)}")
                    else:
                        self.logger.error("无法获取Token")

                    # 如果是第一次401错误，尝试重新获取token
                    if attempt == 0:
                        self.logger.info("尝试重新获取token...")
                        # 强制重新建立Redis连接
                        try:
                            self.cache_rds = self.get_cache_rds()
                            new_token = self._get_fis_auth_token()
                            if new_token and new_token != token:
                                self.logger.info("成功获取新token，将在下次重试时使用")
                                continue
                        except Exception as e:
                            self.logger.error(f"重新获取token失败: {str(e)}")

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

                # 提取用于去重的关键字段
                traded_date = trade_record.get('tradedDate')
                source_type = trade_record.get('sourceType')
                period_name = trade_record.get('periodName')
                product_name = trade_record.get('productName')

                # 检查必需字段是否存在
                if not all([traded_date, source_type, period_name, product_name]):
                    self.logger.warning(
                        f"记录缺少必需的字段，跳过。tradedDate: {traded_date}, sourceType: {source_type}, periodName: {period_name}, productName: {product_name}")
                    continue

                # 添加创建时间
                trade_record['created_at'] = datetime.now().strftime(
                    '%Y-%m-%d %H:%M:%S')

                # 使用组合键作为唯一标识
                key = {
                    'tradedDate': traded_date,
                    'sourceType': source_type,
                    'periodName': period_name,
                    'productName': product_name
                }

                result = self.mgo.set(key=key, data=trade_record)

                if result is not None:
                    success_count += 1
                    self.logger.debug(f"成功保存记录: {key}")
                else:
                    self.logger.warning(f"保存记录失败: {key}")

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
    获取C5TC、P4TC、P5TC、C5、S10TC、HS7TC等产品的逐日交易数据，用于图表展示和趋势分析。
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
            },
            'C5': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/25/405/F/null/null',
                'collection_name': 'fis_daily_c5_trade_data'
            },
            'S10TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/28/405/F/null/null',
                'collection_name': 'fis_daily_s10tc_trade_data'
            },
            'HS7TC': {
                'api_url': 'https://livepricing-prod2.azurewebsites.net/api/v1/chartData/87/405/F/null/null',
                'collection_name': 'fis_daily_hs7tc_trade_data'
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

                token = None

                if key_type == 'hash':
                    # 如果是hash类型，尝试获取auth_token字段
                    token = self.cache_rds.hget("fis-live", "auth_token")
                    if not token:
                        # 如果没有auth_token字段，尝试获取其他可能的字段
                        all_fields = self.cache_rds.hgetall("fis-live")
                        # 尝试常见的token字段名
                        for field_name in ['token', 'access_token', 'authorization', 'auth_token']:
                            if field_name in all_fields:
                                token = all_fields[field_name]
                                break

                elif key_type == 'string':
                    # 如果是string类型，直接获取值
                    token = self.cache_rds.get("fis-live")

                elif key_type == 'list':
                    # 如果是list类型，获取第一个元素
                    token = self.cache_rds.lindex("fis-live", 0)

                else:
                    self.logger.warning(f"不支持的Redis键类型: {key_type}")

                if token:
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
        token = self._get_fis_auth_token()
        if not token:
            self.logger.error("无法获取FIS认证token")
            return {'Authorization': 'None'}
        
        # 确保token格式正确
        if not token.startswith('Bearer '):
            token = f'Bearer {token}'
            
        return {'Authorization': token}

    def _fetch_daily_trade_data(self, max_retries=3):
        """获取逐日交易数据"""
        for attempt in range(max_retries):
            try:
                headers = self._get_api_headers()
                response = requests.get(
                    self.api_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    self.logger.info(
                        f"获取 {self.product_type} 数据成功: {len(data) if isinstance(data, list) else 'N/A'} 条")
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
                    f"保存 {self.product_type} 数据: {success_count}/{total_count} 条")
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
        try:
            # 获取原始数据
            raw_data = self._fetch_daily_trade_data()

            if raw_data is None:
                self.logger.error(f"{self.product_type} 数据获取失败")
                return False

            # 保存数据
            save_success = self._save_daily_trade_data(raw_data)

            if save_success:
                return True
            else:
                self.logger.error(f"{self.product_type} 数据保存失败")
                return False

        except Exception as e:
            self.logger.error(
                f"{self.product_type} 爬取过程中发生错误: {str(e)}")
            return False


class SpiderAllFisDailyTradeData:
    """
    爬取所有FIS逐日交易数据:
    同时获取C5TC、P4TC、P5TC、C5、S10TC、HS7TC六个产品类型的逐日交易数据。
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.product_types = ['C5TC', 'P4TC', 'P5TC', 'C5', 'S10TC', 'HS7TC']
        # 不再在初始化时创建爬虫实例，而是在每次运行时动态创建
        # 这样可以确保每次都从Redis获取最新的token

    def run_all(self):
        """运行所有产品的数据爬取"""
        self.logger.info("开始爬取 FIS 逐日交易数据")
        results = {}

        # 每次运行时重新创建爬虫实例，确保从Redis动态获取最新token
        for product_type in self.product_types:
            spider = None
            try:
                # 创建新的爬虫实例，每次都会从Redis获取最新的token
                spider = SpiderFisDailyTradeData(product_type)

                # run() 方法有装饰器 @decorate.exception_capture_close_datebase
                # 会自动在 finally 块中调用 close()，确保数据库连接正确关闭
                success = spider.run()
                results[product_type] = success

            except Exception as e:
                self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
                results[product_type] = False
                # 如果异常发生在创建实例后但 run() 之前，需要手动关闭
                if spider is not None:
                    try:
                        spider.close()
                    except Exception as close_e:
                        self.logger.debug(f"关闭 {product_type} 爬虫连接时出错: {close_e}")

        # 统计结果
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)

        # 打印结果摘要
        for product_type, success in results.items():
            status = "✓" if success else "✗"
            self.logger.info(f"  {product_type}: {status}")

        self.logger.info(f"完成: {success_count}/{total_count}")

        return results

    def run_single(self, product_type: str):
        """运行单个产品的数据爬取"""
        product_type = product_type.upper()

        if product_type not in self.product_types:
            self.logger.error(f"不支持的产品类型: {product_type}")
            return False

        spider = None
        try:
            # 每次运行时创建新的爬虫实例，确保从Redis获取最新的token
            spider = SpiderFisDailyTradeData(product_type)

            # run() 方法有装饰器 @decorate.exception_capture_close_datebase
            # 会自动在 finally 块中调用 close()，确保数据库连接正确关闭
            success = spider.run()
            return success

        except Exception as e:
            self.logger.error(f"爬取 {product_type} 数据时发生错误: {str(e)}")
            # 如果异常发生在创建实例后但 run() 之前，需要手动关闭
            if spider is not None:
                try:
                    spider.close()
                except Exception as close_e:
                    self.logger.debug(f"关闭 {product_type} 爬虫连接时出错: {close_e}")
            return False

    def run(self, task=None):
        """运行所有产品的数据爬取（兼容main.py调用）"""
        return self.run_all()

    def close(self):
        """关闭所有爬虫连接（已优化为每次运行时动态创建，无需关闭）"""
        # 爬虫实例在每次运行时动态创建并立即关闭，无需在此处处理
