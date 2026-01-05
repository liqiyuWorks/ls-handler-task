#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
船舶信息导出脚本
从 MongoDB 的 global_vessels 集合导出散货船和杂货船的数据
筛选条件：type 是散货船或杂货船，且 imo 和 mmsi 都存在
"""

import os
import sys
import csv
import logging
from typing import Dict, List, Any
import pymongo
from pymongo import MongoClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def connect_mongodb():
    """
    连接 MongoDB 数据库
    
    Returns:
        tuple: (client, db) 或 (None, None) 如果连接失败
    """
    mongo_host = os.getenv('MONGO_HOST', '153.35.13.226')
    mongo_port = int(os.getenv('MONGO_PORT', '27017'))
    mongo_db = os.getenv('MONGO_DB', 'navgreen')
    mongo_user = os.getenv('MONGO_USER', 'navgreen')
    mongo_password = os.getenv('MONGO_PASSWORD', 'Navgreen#0817')
    
    try:
        # 构建连接字符串
        if mongo_user and mongo_password:
            url = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource={mongo_db}"
        else:
            url = f"mongodb://{mongo_host}:{mongo_port}/{mongo_db}"
        
        client = MongoClient(url, serverSelectionTimeoutMS=10000)
        # 测试连接
        client.admin.command('ping')
        db = client[mongo_db]
        
        logger.info(f"成功连接到 MongoDB: {mongo_host}:{mongo_port}/{mongo_db}")
        return client, db
    except Exception as e:
        logger.error(f"MongoDB 连接失败: {e}")
        return None, None


def fetch_vessel_data(db):
    """
    从 MongoDB 获取符合条件的船舶数据
    筛选条件：
    - type 是"散货船"或"杂货船"
    - imo 和 mmsi 都存在且不为空
    
    Args:
        db: MongoDB 数据库对象
        
    Returns:
        List[Dict]: 数据列表
    """
    try:
        collection = db['global_vessels']
        
        # 构建查询条件
        query = {
            'type': {'$in': ['散货船', '杂货船']},
            'imo': {'$exists': True, '$ne': None, '$ne': ''},
            'mmsi': {'$exists': True, '$ne': None, '$ne': ''}
        }
        
        # 获取总数据量
        total_count = collection.count_documents(query)
        logger.info(f"符合条件的船舶数据量: {total_count}")
        
        if total_count == 0:
            logger.warning("未找到符合条件的数据")
            return []
        
        # 查询数据
        cursor = collection.find(query)
        data = list(cursor)
        
        logger.info(f"成功获取 {len(data)} 条数据")
        
        # 进一步过滤，确保 imo 和 mmsi 都不为空字符串
        filtered_data = []
        for item in data:
            imo = item.get('imo')
            mmsi = item.get('mmsi')
            # 检查 imo 和 mmsi 是否真实存在（不为 None、空字符串或仅包含空白字符）
            if imo and str(imo).strip() and mmsi and str(mmsi).strip():
                filtered_data.append(item)
        
        logger.info(f"过滤后有效数据量: {len(filtered_data)}")
        return filtered_data
        
    except Exception as e:
        logger.error(f"从 MongoDB 获取数据失败: {e}")
        return []


def get_all_fieldnames(data: List[Dict]) -> List[str]:
    """
    从数据中提取所有字段名
    
    Args:
        data: 数据列表
        
    Returns:
        List[str]: 字段名列表
    """
    fieldnames = set()
    for item in data:
        fieldnames.update(item.keys())
    
    # 将 _id 放在最前面，其他字段按字母顺序排序
    sorted_fields = ['_id'] + sorted([f for f in fieldnames if f != '_id'])
    return sorted_fields


def convert_to_csv_row(item: Dict, fieldnames: List[str]) -> Dict[str, Any]:
    """
    将 MongoDB 文档转换为 CSV 行数据
    
    Args:
        item: MongoDB 文档
        fieldnames: CSV 字段名列表
        
    Returns:
        Dict: CSV 行数据
    """
    row = {}
    for field in fieldnames:
        value = item.get(field, '')
        # 处理特殊类型
        if isinstance(value, (dict, list)):
            import json
            value = json.dumps(value, ensure_ascii=False)
        elif value is None:
            value = ''
        else:
            value = str(value)
        row[field] = value
    return row


def export_to_csv(data: List[Dict], filename: str):
    """
    导出数据到 CSV 文件
    
    Args:
        data: 要导出的数据列表
        filename: 输出文件名
    """
    if not data:
        logger.warning(f"没有数据可导出到 {filename}")
        return
    
    try:
        # 确保输出目录存在
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        
        # 获取所有字段名
        fieldnames = get_all_fieldnames(data)
        logger.info(f"CSV 字段数: {len(fieldnames)}")
        logger.info(f"字段列表: {', '.join(fieldnames[:10])}..." if len(fieldnames) > 10 else f"字段列表: {', '.join(fieldnames)}")
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                row = convert_to_csv_row(item, fieldnames)
                writer.writerow(row)
        
        logger.info(f"✓ 成功导出 {len(data)} 条数据到 {filepath}")
        logger.info(f"✓ 文件路径: {os.path.abspath(filepath)}")
        
    except Exception as e:
        logger.error(f"导出 CSV 失败 {filename}: {e}", exc_info=True)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始导出船舶信息数据")
    logger.info("=" * 60)
    
    # 连接 MongoDB
    client, db = connect_mongodb()
    if not client or not db:
        logger.error("无法连接到 MongoDB，请检查环境变量配置")
        sys.exit(1)
    
    try:
        # 获取数据
        logger.info("\n正在从 MongoDB 获取数据...")
        data = fetch_vessel_data(db)
        
        if not data:
            logger.error("未获取到任何符合条件的数据")
            sys.exit(1)
        
        # 统计信息
        logger.info("\n数据统计:")
        bulk_carrier_count = sum(1 for item in data if item.get('type') == '散货船')
        general_cargo_count = sum(1 for item in data if item.get('type') == '杂货船')
        logger.info(f"  散货船: {bulk_carrier_count} 条")
        logger.info(f"  杂货船: {general_cargo_count} 条")
        logger.info(f"  总计: {len(data)} 条")
        
        # 导出 CSV
        logger.info("\n开始导出 CSV 文件...")
        export_to_csv(data, "vessels_dry_cargo.csv")
        
        logger.info("\n" + "=" * 60)
        logger.info("导出完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 关闭连接
        if client:
            client.close()
            logger.info("已关闭 MongoDB 连接")


if __name__ == "__main__":
    main()
