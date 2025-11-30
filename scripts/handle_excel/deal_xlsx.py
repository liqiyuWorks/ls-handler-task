#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Excel 回测数据处理脚本
解析回测数据目录下的 xlsx 文件，并根据文件名存储到对应的 MongoDB 集合
"""

import os
import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestDataProcessor:
    """回测数据处理器"""
    
    def __init__(self, mongo_host: str, mongo_port: int, mongo_db: str, 
                 mongo_user: str, mongo_password: str):
        """
        初始化处理器
        
        Args:
            mongo_host: MongoDB 主机地址
            mongo_port: MongoDB 端口
            mongo_db: 数据库名称
            mongo_user: 用户名
            mongo_password: 密码
        """
        self.mongo_host = mongo_host
        self.mongo_port = mongo_port
        self.mongo_db = mongo_db
        self.mongo_user = mongo_user
        self.mongo_password = mongo_password
        
        self.client = None
        self.db = None
        
        # 不再使用固定的集合名称，而是根据合约类型动态生成
        # 格式：backtest_{contract_type}_historical_forecast_data
        
        self._connect()
    
    def _connect(self):
        """建立 MongoDB 连接"""
        try:
            connection_string = (
                f"mongodb://{self.mongo_user}:{self.mongo_password}@"
                f"{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?authSource={self.mongo_db}"
            )
            
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.mongo_db]
            
            logger.info(f"✓ MongoDB 连接成功: {self.mongo_host}:{self.mongo_port}")
            logger.info(f"✓ 使用数据库: {self.mongo_db}")
            
        except ConnectionFailure as e:
            logger.error(f"✗ MongoDB 连接失败: {e}")
            raise
        except Exception as e:
            logger.error(f"✗ MongoDB 初始化失败: {e}")
            raise
    
    def get_collection_name(self, contract_type: str) -> str:
        """
        根据合约类型生成集合名称
        
        Args:
            contract_type: 合约类型（如 P5, P3A, C3 等）
            
        Returns:
            集合名称，格式：backtest_{contract_type}_historical_forecast_data
        """
        return f"backtest_{contract_type}_historical_forecast_data"
    
    def determine_forecast_days(self, filename: str, columns: List[str]) -> int:
        """
        确定预测天数（42天或14天）
        
        Args:
            filename: 文件名
            columns: 数据列名列表
            
        Returns:
            预测天数（42 或 14）
        """
        # 优先从文件名判断
        if "42天后" in filename or "42天" in filename:
            return 42
        elif "14天后" in filename or "14天" in filename:
            return 14
        
        # 如果文件名无法判断，从列名判断
        columns_str = " ".join(columns)
        if "42天" in columns_str:
            return 42
        elif "14天" in columns_str:
            return 14
        
        # 默认使用 42 天（如果无法从文件名和列名判断）
        logger.warning(f"无法确定文件 {filename} 的天数，默认使用 42 天")
        return 42
    
    def extract_contract_type(self, filename: str) -> str:
        """
        从文件名中提取合约类型（如 P3A, P5, P6, C3, C5）
        
        Args:
            filename: 文件名
            
        Returns:
            合约类型
        """
        match = re.search(r'([PC]\d+[A-Z]?)-', filename)
        if match:
            return match.group(1)
        return "UNKNOWN"
    
    def parse_excel_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        解析 Excel 文件
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            解析后的数据字典，包含合约类型、预测天数（42或14）和记录列表
        """
        try:
            filename = os.path.basename(file_path)
            logger.info(f"开始解析文件: {filename}")
            
            # 读取 Excel 文件
            df = pd.read_excel(file_path)
            
            if df.empty:
                logger.warning(f"文件 {filename} 为空")
                return None
            
            # 提取合约类型
            contract_type = self.extract_contract_type(filename)
            
            # 确定预测天数（42天或14天）
            forecast_days = self.determine_forecast_days(filename, df.columns.tolist())
            
            # 清理列名（去除空格）
            df.columns = df.columns.str.strip()
            
            # 将 DataFrame 转换为字典列表
            records = []
            for _, row in df.iterrows():
                record = {}
                
                # 处理日期
                date_col = None
                for col in df.columns:
                    if '日期' in col or col == 'date':
                        date_col = col
                        break
                
                if date_col:
                    date_value = row[date_col]
                    if pd.isna(date_value):
                        continue  # 跳过日期为空的行
                    if isinstance(date_value, pd.Timestamp):
                        date_value = date_value.strftime('%Y-%m-%d')
                    elif isinstance(date_value, str):
                        date_value = date_value.strip()
                    record['date'] = date_value
                else:
                    continue  # 跳过没有日期列的行
                
                # 处理实际价格
                actual_price_col = None
                for col in df.columns:
                    if '实际价格' in col or col == 'actual_price':
                        actual_price_col = col
                        break
                
                if actual_price_col:
                    value = row[actual_price_col]
                    if pd.isna(value) or value == '-' or value == '':
                        record['actual_price'] = None
                    elif isinstance(value, (int, float)):
                        record['actual_price'] = round(float(value), 2)
                    else:
                        try:
                            record['actual_price'] = round(float(value), 2) if str(value).strip() != '-' else None
                        except:
                            record['actual_price'] = None
                else:
                    record['actual_price'] = None
                
                # 处理预测价格
                forecast_price_col = None
                forecast_col_name = None
                for col in df.columns:
                    if '预测价格' in col or col == 'forecast_price':
                        forecast_price_col = col
                        forecast_col_name = col
                        break
                
                if forecast_price_col:
                    value = row[forecast_price_col]
                    if pd.isna(value) or value == '-' or value == '':
                        forecast_price = None
                    elif isinstance(value, (int, float)):
                        forecast_price = round(float(value), 2)
                    else:
                        try:
                            forecast_price = round(float(value), 2) if str(value).strip() != '-' else None
                        except:
                            forecast_price = None
                    
                    record['forecast_price'] = forecast_price
                    record['forecast_days'] = forecast_days
                else:
                    record['forecast_price'] = None
                    record['forecast_days'] = forecast_days
                
                records.append(record)
            
            result = {
                'filename': filename,
                'contract_type': contract_type,
                'forecast_days': forecast_days,
                'total_records': len(records),
                'records': records
            }
            
            logger.info(f"✓ 解析完成: {filename}, 合约类型: {contract_type}, 预测天数: {forecast_days}, 共 {len(records)} 条记录")
            return result
            
        except Exception as e:
            logger.error(f"✗ 解析文件失败 {file_path}: {e}")
            return None
    
    def merge_and_store_by_contract(self, all_parsed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按合约类型合并数据并存储到 MongoDB
        
        Args:
            all_parsed_data: 所有解析后的数据列表
            
        Returns:
            处理结果统计
        """
        # 按合约类型分组
        contract_groups = {}
        for parsed_data in all_parsed_data:
            if parsed_data is None:
                continue
            contract_type = parsed_data['contract_type']
            if contract_type not in contract_groups:
                contract_groups[contract_type] = []
            contract_groups[contract_type].append(parsed_data)
        
        results = {
            'success': 0,
            'failed': 0,
            'total': len(contract_groups),
            'details': []
        }
        
        # 处理每个合约类型
        for contract_type, parsed_data_list in contract_groups.items():
            try:
                # 合并该合约类型的所有数据
                merged_records = self._merge_contract_data(parsed_data_list)
                
                # 存储到对应的集合
                collection_name = self.get_collection_name(contract_type)
                success = self._store_merged_data(collection_name, contract_type, merged_records)
                
                if success:
                    results['success'] += 1
                    results['details'].append({
                        'contract_type': contract_type,
                        'collection': collection_name,
                        'records_count': len(merged_records),
                        'status': 'success'
                    })
                    logger.info(f"✓ 合约 {contract_type} 存储成功: {collection_name}, 共 {len(merged_records)} 条记录")
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'contract_type': contract_type,
                        'collection': collection_name,
                        'status': 'failed'
                    })
            except Exception as e:
                results['failed'] += 1
                logger.error(f"✗ 处理合约 {contract_type} 失败: {e}")
                results['details'].append({
                    'contract_type': contract_type,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results
    
    def _merge_contract_data(self, parsed_data_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        合并同一合约类型的42天和14天预测数据
        
        Args:
            parsed_data_list: 同一合约类型的所有解析数据
            
        Returns:
            按日期索引的合并记录字典
        """
        merged = {}  # key: date, value: merged record
        
        for parsed_data in parsed_data_list:
            forecast_days = parsed_data['forecast_days']
            for record in parsed_data['records']:
                date = record['date']
                if not date:
                    continue
                
                if date not in merged:
                    # 创建新记录
                    merged[date] = {
                        'date': date,
                        'actual_price': record.get('actual_price'),
                        'forecast_42d': None,
                        'forecast_14d': None
                    }
                
                # 合并预测价格（根据预测天数分别填充）
                forecast_price = record.get('forecast_price')
                
                if forecast_days == 42:
                    merged[date]['forecast_42d'] = forecast_price
                elif forecast_days == 14:
                    merged[date]['forecast_14d'] = forecast_price
                elif forecast_days == 'both':
                    # 如果文件同时包含42天和14天数据（理论上不应该出现，但保留兼容性）
                    merged[date]['forecast_42d'] = forecast_price
                    merged[date]['forecast_14d'] = forecast_price
                
                # 合并实际价格（优先使用非空值）
                if merged[date]['actual_price'] is None and record.get('actual_price') is not None:
                    merged[date]['actual_price'] = record.get('actual_price')
        
        return merged
    
    def _store_merged_data(self, collection_name: str, contract_type: str, 
                          merged_records: Dict[str, Dict[str, Any]]) -> bool:
        """
        存储合并后的数据到 MongoDB
        
        Args:
            collection_name: 集合名称
            contract_type: 合约类型
            merged_records: 合并后的记录字典
            
        Returns:
            存储是否成功
        """
        try:
            collection = self.db[collection_name]
            
            # 创建索引
            self._create_indexes(collection)
            
            inserted_count = 0
            updated_count = 0
            errors = []
            
            for date, record in merged_records.items():
                try:
                    # 唯一键是日期
                    unique_id = date
                    record['_id'] = unique_id
                    record['contract_type'] = contract_type  # 保留合约类型字段便于查询
                    
                    # 使用 replace_one 实现 upsert
                    result = collection.replace_one(
                        {'_id': unique_id},
                        record,
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        inserted_count += 1
                    elif result.modified_count > 0:
                        updated_count += 1
                    
                except Exception as e:
                    error_msg = f"存储记录失败 (日期: {date}): {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            if errors:
                logger.warning(f"存储过程中的错误数量: {len(errors)}")
                if len(errors) <= 5:
                    for error in errors:
                        logger.warning(f"  - {error}")
            
            return len(errors) == 0
            
        except Exception as e:
            logger.error(f"✗ 存储到 MongoDB 失败: {e}")
            return False
    
    def _create_indexes(self, collection):
        """创建索引"""
        try:
            # 创建日期唯一索引（因为每个集合已经是按合约类型分开的）
            collection.create_index("date", unique=True)
            # 创建合约类型索引（虽然每个集合只有一个类型，但保留以便查询）
            collection.create_index("contract_type")
            logger.debug(f"✓ 已创建索引: {collection.name}")
        except Exception as e:
            logger.warning(f"创建索引时出现警告: {e}")
    
    def process_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        处理目录下的所有 Excel 文件
        
        Args:
            directory_path: 目录路径
            
        Returns:
            处理结果统计
        """
        if not os.path.exists(directory_path):
            logger.error(f"目录不存在: {directory_path}")
            return {'success': 0, 'failed': 0, 'total': 0}
        
        excel_files = [
            f for f in os.listdir(directory_path)
            if f.endswith(('.xlsx', '.xls'))
        ]
        
        if not excel_files:
            logger.warning(f"目录中没有找到 Excel 文件: {directory_path}")
            return {'success': 0, 'failed': 0, 'total': 0}
        
        logger.info(f"找到 {len(excel_files)} 个 Excel 文件")
        
        # 先解析所有文件
        all_parsed_data = []
        parse_results = {
            'success': 0,
            'failed': 0,
            'total': len(excel_files),
            'details': []
        }
        
        for filename in excel_files:
            file_path = os.path.join(directory_path, filename)
            
            # 解析文件
            parsed_data = self.parse_excel_file(file_path)
            
            if parsed_data is None:
                parse_results['failed'] += 1
                parse_results['details'].append({
                    'filename': filename,
                    'status': 'failed',
                    'reason': '解析失败'
                })
            else:
                parse_results['success'] += 1
                all_parsed_data.append(parsed_data)
                parse_results['details'].append({
                    'filename': filename,
                    'status': 'parsed',
                    'contract_type': parsed_data['contract_type'],
                    'forecast_days': parsed_data['forecast_days'],
                    'records': parsed_data['total_records']
                })
        
        logger.info(f"解析完成: 成功 {parse_results['success']}, 失败 {parse_results['failed']}")
        
        # 按合约类型合并并存储
        if all_parsed_data:
            logger.info("开始按合约类型合并数据并存储...")
            store_results = self.merge_and_store_by_contract(all_parsed_data)
            
            # 合并结果
            results = {
                'parse': parse_results,
                'store': store_results,
                'total_files': len(excel_files),
                'success': store_results['success'],
                'failed': store_results['failed']
            }
        else:
            results = {
                'parse': parse_results,
                'store': {'success': 0, 'failed': 0},
                'total_files': len(excel_files),
                'success': 0,
                'failed': 0
            }
        
        return results
    
    def close(self):
        """关闭 MongoDB 连接"""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB 连接已关闭")


def load_mongo_config_from_env() -> Dict[str, Any]:
    """从环境变量加载 MongoDB 配置"""
    import os
    
    return {
        'host': os.getenv('MONGO_HOST', '153.35.96.86'),
        'port': int(os.getenv('MONGO_PORT', 27017)),
        'database': os.getenv('MONGO_DB', 'aquabridge'),
        'username': os.getenv('MONGO_USER', 'aquabridge'),
        'password': os.getenv('MONGO_PASSWORD', 'Aquabridge#2025')
    }


def main():
    """主函数"""
    # 加载配置
    config = load_mongo_config_from_env()
    
    # 确定数据目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_directory = os.path.join(script_dir, '回测数据')
    
    logger.info("=" * 60)
    logger.info("开始处理回测数据")
    logger.info("=" * 60)
    logger.info(f"MongoDB 地址: {config['host']}:{config['port']}")
    logger.info(f"数据库: {config['database']}")
    logger.info(f"数据目录: {data_directory}")
    logger.info("=" * 60)
    
    processor = None
    try:
        # 创建处理器
        processor = BacktestDataProcessor(
            mongo_host=config['host'],
            mongo_port=config['port'],
            mongo_db=config['database'],
            mongo_user=config['username'],
            mongo_password=config['password']
        )
        
        # 处理目录
        results = processor.process_directory(data_directory)
        
        # 输出结果
        logger.info("=" * 60)
        logger.info("处理完成")
        logger.info("=" * 60)
        logger.info(f"总文件数: {results['total_files']}")
        
        # 解析结果
        parse_results = results.get('parse', {})
        logger.info(f"\n解析结果:")
        logger.info(f"  成功: {parse_results.get('success', 0)}")
        logger.info(f"  失败: {parse_results.get('failed', 0)}")
        
        # 存储结果
        store_results = results.get('store', {})
        logger.info(f"\n存储结果:")
        logger.info(f"  成功: {store_results.get('success', 0)} 个合约类型")
        logger.info(f"  失败: {store_results.get('failed', 0)} 个合约类型")
        logger.info("=" * 60)
        
        # 输出解析详细信息
        if parse_results.get('details'):
            logger.info("\n文件解析详情:")
            for detail in parse_results['details']:
                if detail['status'] == 'parsed':
                    logger.info(
                        f"  ✓ {detail['filename']} - "
                        f"合约: {detail['contract_type']}, "
                        f"预测天数: {detail['forecast_days']}天, "
                        f"记录数: {detail['records']}"
                    )
                else:
                    logger.error(f"  ✗ {detail['filename']}: {detail.get('reason', '未知错误')}")
        
        # 输出存储详细信息
        if store_results.get('details'):
            logger.info("\n数据存储详情:")
            for detail in store_results['details']:
                if detail['status'] == 'success':
                    logger.info(
                        f"  ✓ 合约 {detail['contract_type']} -> "
                        f"{detail['collection']} ({detail['records_count']} 条记录)"
                    )
                else:
                    logger.error(
                        f"  ✗ 合约 {detail['contract_type']}: "
                        f"{detail.get('error', '存储失败')}"
                    )
        
        return 0 if (parse_results.get('failed', 0) == 0 and store_results.get('failed', 0) == 0) else 1
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        return 1
        
    finally:
        if processor:
            processor.close()


if __name__ == "__main__":
    sys.exit(main())

