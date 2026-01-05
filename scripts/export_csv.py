#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理教育数据导出脚本
从 MongoDB 导出数据，按经济区分类导出为 CSV 文件
"""

import os
import sys
import csv
import logging
from collections import defaultdict
from typing import Dict, List, Any
import pymongo
from pymongo import MongoClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 八大经济区省份映射
ECONOMIC_ZONES = {
    "东北地区经济区": ["吉林", "辽宁", "黑龙江"],
    "北部沿海经济区": ["北京", "天津", "河北", "山东"],
    "东部沿海经济区": ["江苏", "浙江", "上海"],
    "南部沿海经济区": ["广东", "福建", "海南"],
    "黄河中游经济区": ["陕西", "山西", "内蒙古", "河南"],
    "长江中游经济区": ["湖北", "湖南", "江西", "安徽"],
    "西南地区经济区": ["云南", "贵州", "四川", "重庆", "广西"],
    "西北地区经济区": ["甘肃", "青海", "宁夏", "西藏", "新疆"]
}

# 创建省份到经济区的反向映射
PROVINCE_TO_ZONE = {}
for zone, provinces in ECONOMIC_ZONES.items():
    for province in provinces:
        PROVINCE_TO_ZONE[province] = zone


def get_location_zone(location: str) -> str:
    """
    根据 location 字段判断所属经济区
    
    Args:
        location: 位置字符串，如 "江苏"、"北京" 等
        
    Returns:
        经济区名称，如果无法匹配则返回 None
    """
    if not location or location == "无坐标":
        return None
    
    # 直接匹配省份名称
    if location in PROVINCE_TO_ZONE:
        return PROVINCE_TO_ZONE[location]
    
    # 尝试部分匹配（处理可能包含更多信息的情况，如 "江苏南京"）
    for province, zone in PROVINCE_TO_ZONE.items():
        if province in location:
            return zone
    
    return None


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


def fetch_data_from_mongodb(db, collection_name: str = "weibo_geography_education"):
    """
    从 MongoDB 获取所有数据
    
    Args:
        db: MongoDB 数据库对象
        collection_name: 集合名称
        
    Returns:
        List[Dict]: 数据列表
    """
    try:
        collection = db[collection_name]
        
        # 获取总数据量
        total_count = collection.count_documents({})
        logger.info(f"集合 {collection_name} 总数据量: {total_count}")
        
        # 查询所有数据
        cursor = collection.find({})
        data = list(cursor)
        
        logger.info(f"成功获取 {len(data)} 条数据")
        return data
    except Exception as e:
        logger.error(f"从 MongoDB 获取数据失败: {e}")
        return []


def group_data_by_zone(data: List[Dict]) -> Dict[str, List[Dict]]:
    """
    按经济区对数据进行分组
    
    Args:
        data: 原始数据列表
        
    Returns:
        Dict[str, List[Dict]]: 按经济区分组的数据字典
    """
    grouped = defaultdict(list)
    unclassified = []
    
    for item in data:
        location = item.get('location', '')
        zone = get_location_zone(location)
        
        if zone:
            grouped[zone].append(item)
        else:
            unclassified.append(item)
    
    # 统计每个经济区的数据量
    logger.info("\n数据分组统计:")
    for zone in ECONOMIC_ZONES.keys():
        count = len(grouped[zone])
        logger.info(f"  {zone}: {count} 条")
    
    if unclassified:
        logger.warning(f"  未分类数据: {len(unclassified)} 条")
        # 显示一些未分类的 location 示例
        sample_locations = set([item.get('location', '') for item in unclassified[:10]])
        logger.warning(f"  未分类 location 示例: {list(sample_locations)}")
    
    return dict(grouped)


def ensure_minimum_data(grouped_data: Dict[str, List[Dict]], min_count: int = 1600):
    """
    确保每个经济区至少有指定数量的数据
    如果某个经济区数据不足，会记录警告
    
    Args:
        grouped_data: 按经济区分组的数据
        min_count: 每个经济区最少数据量
        
    Returns:
        Dict[str, List[Dict]]: 处理后的数据（可能包含不足的数据）
    """
    result = {}
    for zone in ECONOMIC_ZONES.keys():
        data = grouped_data.get(zone, [])
        count = len(data)
        
        if count < min_count:
            logger.warning(f"⚠️  {zone} 数据量不足: {count} < {min_count}")
            # 仍然导出，但记录警告
        else:
            logger.info(f"✓ {zone} 数据量充足: {count} >= {min_count}")
        
        result[zone] = data
    
    return result


def convert_to_csv_row(item: Dict) -> Dict[str, Any]:
    """
    将 MongoDB 文档转换为 CSV 行数据
    
    Args:
        item: MongoDB 文档
        
    Returns:
        Dict: CSV 行数据
    """
    return {
        '_id': str(item.get('_id', '')),
        'id': str(item.get('id', '')),
        'coordinates': item.get('coordinates', ''),
        'date': item.get('date', ''),
        'location': item.get('location', ''),
        'text': item.get('text', ''),
        'updated_at': item.get('updated_at', ''),
        'user': item.get('user', '')
    }


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
        
        # CSV 字段名
        fieldnames = ['_id', 'id', 'coordinates', 'date', 'location', 'text', 'updated_at', 'user']
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in data:
                row = convert_to_csv_row(item)
                writer.writerow(row)
        
        logger.info(f"✓ 成功导出 {len(data)} 条数据到 {filepath}")
    except Exception as e:
        logger.error(f"导出 CSV 失败 {filename}: {e}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始导出地理教育数据")
    logger.info("=" * 60)
    
    # 连接 MongoDB
    client, db = connect_mongodb()
    if not client or not db:
        logger.error("无法连接到 MongoDB，请检查环境变量配置")
        sys.exit(1)
    
    try:
        # 获取数据
        logger.info("\n正在从 MongoDB 获取数据...")
        data = fetch_data_from_mongodb(db, "weibo_geography_education")
        
        if not data:
            logger.error("未获取到任何数据")
            sys.exit(1)
        
        # 按经济区分组
        logger.info("\n正在按经济区分组数据...")
        grouped_data = group_data_by_zone(data)
        
        # 确保每个经济区至少有 1600 条数据
        logger.info("\n检查数据量...")
        final_data = ensure_minimum_data(grouped_data, min_count=1600)
        
        # 导出每个经济区的数据
        logger.info("\n开始导出 CSV 文件...")
        for zone, zone_data in final_data.items():
            if zone_data:
                filename = f"地理教育_{zone}.csv"
                export_to_csv(zone_data, filename)
        
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
