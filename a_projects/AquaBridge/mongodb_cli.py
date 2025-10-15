#!/usr/bin/env python3
"""
MongoDB 命令行工具
用于管理 AquaBridge 数据
"""

import json
import sys
from datetime import datetime
from mongodb_storage import MongoDBStorage, load_config


def list_data(limit: int = 10, page_key: str = None):
    """列出数据"""
    try:
        config = load_config()
        
        if page_key:
            # 列出特定页面的数据
            storage = MongoDBStorage(config, page_key)
            data_list = storage.list_ffa_data(limit)
            storage.close()
            
            print(f"=== {page_key} 数据列表 (最近{limit}条) ===")
            if not data_list:
                print("暂无数据")
                return
            
            for i, data in enumerate(data_list, 1):
                # 支持新的数据格式
                metadata = data.get('metadata', {})
                page_name = metadata.get('page_name', data.get('page_name', 'N/A'))
                swap_date = metadata.get('swap_date', data.get('swap_date', 'N/A'))
                timestamp = metadata.get('timestamp', data.get('timestamp', 'N/A'))
                
                print(f"\n{i}. 页面: {page_name}")
                print(f"   掉期日期: {swap_date}")
                print(f"   时间戳: {timestamp}")
                print(f"   存储时间: {data.get('stored_at', 'N/A')}")
                
                contracts = data.get('contracts', {})
                if 'table_data' in contracts:
                    print(f"   表格数据: {contracts['table_data'].get('total_rows', 0)} 行")
                else:
                    print(f"   合约数量: {len(contracts)} 个")
        else:
            # 列出所有页面的数据
            print(f"=== 所有页面数据列表 (最近{limit}条) ===")
            
            # 获取所有collection
            from pymongo import MongoClient
            client = MongoClient(f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}")
            db = client[config['database']]
            
            all_data = []
            collections = db.list_collection_names()
            
            for collection_name in collections:
                if collection_name.endswith('_data'):
                    collection = db[collection_name]
                    data_list = list(collection.find().sort("timestamp", -1).limit(limit))
                    for data in data_list:
                        data['collection'] = collection_name
                        all_data.append(data)
            
            # 按时间戳排序
            all_data.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            all_data = all_data[:limit]
            
            if not all_data:
                print("暂无数据")
                return
            
            for i, data in enumerate(all_data, 1):
                # 支持新的数据格式
                metadata = data.get('metadata', {})
                page_name = metadata.get('page_name', data.get('page_name', 'N/A'))
                swap_date = metadata.get('swap_date', data.get('swap_date', 'N/A'))
                timestamp = metadata.get('timestamp', data.get('timestamp', 'N/A'))
                
                print(f"\n{i}. 页面: {page_name}")
                print(f"   集合: {data.get('collection', 'N/A')}")
                print(f"   掉期日期: {swap_date}")
                print(f"   时间戳: {timestamp}")
                print(f"   存储时间: {data.get('stored_at', 'N/A')}")
                
                contracts = data.get('contracts', {})
                if 'table_data' in contracts:
                    print(f"   表格数据: {contracts['table_data'].get('total_rows', 0)} 行")
                else:
                    print(f"   合约数量: {len(contracts)} 个")
            
            client.close()
                
    except Exception as e:
        print(f"✗ 列出数据失败: {e}")


def get_data(swap_date: str, page_key: str = None):
    """获取指定日期的数据"""
    try:
        config = load_config()
        
        if page_key:
            # 从特定页面获取数据
            storage = MongoDBStorage(config, page_key)
            data = storage.get_ffa_data(swap_date)
            storage.close()
            
            if data:
                print(f"=== {page_key} 数据详情: {swap_date} ===")
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print(f"✗ 未找到数据: swap_date={swap_date}, page_key={page_key}")
        else:
            # 从所有页面搜索数据
            from pymongo import MongoClient
            client = MongoClient(f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}")
            db = client[config['database']]
            
            found = False
            collections = db.list_collection_names()
            
            for collection_name in collections:
                if collection_name.endswith('_data'):
                    collection = db[collection_name]
                    data = collection.find_one({"swap_date": swap_date})
                    if data:
                        data.pop('_id', None)
                        print(f"=== {collection_name} 数据详情: {swap_date} ===")
                        print(json.dumps(data, ensure_ascii=False, indent=2))
                        found = True
                        break
            
            if not found:
                print(f"✗ 未找到数据: swap_date={swap_date}")
            
            client.close()
            
    except Exception as e:
        print(f"✗ 获取数据失败: {e}")


def delete_data(swap_date: str, page_key: str = None):
    """删除指定日期的数据"""
    try:
        config = load_config()
        
        if page_key:
            # 删除特定页面的数据
            storage = MongoDBStorage(config, page_key)
            success = storage.delete_ffa_data(swap_date)
            storage.close()
            
            if success:
                print(f"✓ 数据删除成功: swap_date={swap_date}, page_key={page_key}")
            else:
                print(f"✗ 数据删除失败: swap_date={swap_date}, page_key={page_key}")
        else:
            # 从所有页面删除数据
            from pymongo import MongoClient
            client = MongoClient(f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}")
            db = client[config['database']]
            
            deleted_count = 0
            collections = db.list_collection_names()
            
            for collection_name in collections:
                if collection_name.endswith('_data'):
                    collection = db[collection_name]
                    result = collection.delete_one({"swap_date": swap_date})
                    if result.deleted_count > 0:
                        deleted_count += result.deleted_count
                        print(f"✓ 从 {collection_name} 删除数据: swap_date={swap_date}")
            
            if deleted_count > 0:
                print(f"✓ 总共删除 {deleted_count} 条数据")
            else:
                print(f"✗ 未找到要删除的数据: swap_date={swap_date}")
            
            client.close()
            
    except Exception as e:
        print(f"✗ 删除数据失败: {e}")


def show_stats(page_key: str = None):
    """显示统计信息"""
    try:
        config = load_config()
        
        if page_key:
            # 显示特定页面的统计信息
            storage = MongoDBStorage(config, page_key)
            stats = storage.get_collection_stats()
            storage.close()
            
            print(f"=== {page_key} 统计信息 ===")
            print(f"文档数量: {stats.get('count', 0)}")
            print(f"集合大小: {stats.get('size', 0):,} bytes")
            print(f"平均文档大小: {stats.get('avgObjSize', 0):,} bytes")
            print(f"存储大小: {stats.get('storageSize', 0):,} bytes")
        else:
            # 显示所有页面的统计信息
            from pymongo import MongoClient
            client = MongoClient(f"mongodb://{config['username']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}")
            db = client[config['database']]
            
            print("=== 所有页面统计信息 ===")
            total_docs = 0
            total_size = 0
            
            collections = db.list_collection_names()
            for collection_name in collections:
                if collection_name.endswith('_data'):
                    collection = db[collection_name]
                    stats = db.command("collStats", collection_name)
                    
                    doc_count = stats.get('count', 0)
                    collection_size = stats.get('size', 0)
                    
                    print(f"\n{collection_name}:")
                    print(f"  文档数量: {doc_count}")
                    print(f"  集合大小: {collection_size:,} bytes")
                    print(f"  平均文档大小: {stats.get('avgObjSize', 0):,} bytes")
                    
                    total_docs += doc_count
                    total_size += collection_size
            
            print(f"\n总计:")
            print(f"  总文档数量: {total_docs}")
            print(f"  总集合大小: {total_size:,} bytes")
            
            client.close()
        
    except Exception as e:
        print(f"✗ 获取统计信息失败: {e}")


def test_connection():
    """测试连接"""
    try:
        config = load_config()
        storage = MongoDBStorage(config)
        print("=== 连接测试 ===")
        print(f"主机: {config['host']}:{config['port']}")
        print(f"数据库: {config['database']}")
        print(f"集合: {config['collection']}")
        print("✓ 连接成功")
        storage.close()
        
    except Exception as e:
        print(f"✗ 连接失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB 命令行工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出数据
    list_parser = subparsers.add_parser('list', help='列出数据')
    list_parser.add_argument('--limit', '-l', type=int, default=10, help='显示数量限制')
    list_parser.add_argument('--page', '-p', choices=['ffa_price_signals', 'p4tc_spot_decision'], 
                           help='指定页面')
    
    # 获取数据
    get_parser = subparsers.add_parser('get', help='获取指定日期的数据')
    get_parser.add_argument('swap_date', help='掉期日期 (YYYY-MM-DD)')
    get_parser.add_argument('--page', '-p', choices=['ffa_price_signals', 'p4tc_spot_decision'], 
                           help='指定页面')
    
    # 删除数据
    delete_parser = subparsers.add_parser('delete', help='删除指定日期的数据')
    delete_parser.add_argument('swap_date', help='掉期日期 (YYYY-MM-DD)')
    delete_parser.add_argument('--page', '-p', choices=['ffa_price_signals', 'p4tc_spot_decision'], 
                              help='指定页面')
    
    # 统计信息
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    stats_parser.add_argument('--page', '-p', choices=['ffa_price_signals', 'p4tc_spot_decision'], 
                             help='指定页面')
    
    # 测试连接
    subparsers.add_parser('test', help='测试连接')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'list':
        list_data(args.limit, args.page)
    elif args.command == 'get':
        get_data(args.swap_date, args.page)
    elif args.command == 'delete':
        delete_data(args.swap_date, args.page)
    elif args.command == 'stats':
        show_stats(args.page)
    elif args.command == 'test':
        test_connection()


if __name__ == "__main__":
    main()
