#!/usr/bin/env python3
"""
查询P4TC现货应用决策数据的MongoDB存储
"""

import json
from datetime import datetime
from mongodb_storage import MongoDBStorage, load_config


def query_p4tc_core_data():
    """查询P4TC核心数据"""
    print("=== P4TC现货应用决策核心数据查询 ===")
    
    # 加载配置
    config = load_config()
    if not config.get('enabled', False):
        print("✗ MongoDB存储已禁用")
        return False
    
    try:
        # 创建存储实例
        storage = MongoDBStorage(config, "p4tc_spot_decision")
        
        # 查询最新的核心数据
        print("1. 查询最新的P4TC核心数据...")
        core_data_list = storage.list_p4tc_core_data(limit=3)
        
        if not core_data_list:
            print("✗ 未找到P4TC核心数据")
            return False
        
        print(f"✓ 找到 {len(core_data_list)} 条P4TC核心数据")
        
        for i, data in enumerate(core_data_list, 1):
            print(f"\n=== 第 {i} 条数据 ===")
            print(f"掉期日期: {data.get('swap_date')}")
            print(f"时间戳: {data.get('timestamp')}")
            print(f"存储时间: {data.get('stored_at')}")
            
            core_data = data.get('core_data', {})
            
            # 显示交易建议
            trading_rec = core_data.get('trading_recommendation', {})
            print(f"\n📊 交易建议:")
            print(f"  盈亏比: {trading_rec.get('profit_loss_ratio')}")
            print(f"  建议方向: {trading_rec.get('recommended_direction')}")
            print(f"  方向信心: {trading_rec.get('direction_confidence')}")
            
            # 显示当前预测
            current_forecast = core_data.get('current_forecast', {})
            print(f"\n🔮 当前预测:")
            print(f"  日期: {current_forecast.get('date')}")
            print(f"  高期值: {current_forecast.get('high_expected_value')}")
            print(f"  价差比: {current_forecast.get('price_difference_ratio')}")
            print(f"  价差比区间: {current_forecast.get('price_difference_range')}")
            print(f"  预测值: {current_forecast.get('forecast_value')}")
            print(f"  概率: {current_forecast.get('probability')}%")
            
            # 显示统计信息
            statistics = core_data.get('statistics', {})
            print(f"\n📈 统计信息:")
            print(f"  数据行数: {statistics.get('total_rows')}")
            print(f"  数据质量: {statistics.get('data_quality')}")
        
        # 查询特定日期的数据
        print(f"\n2. 查询特定日期的数据...")
        latest_swap_date = core_data_list[0].get('swap_date')
        specific_data = storage.get_p4tc_core_data(latest_swap_date)
        
        if specific_data:
            print(f"✓ 成功查询到 {latest_swap_date} 的核心数据")
            print("\n=== 完整JSON结构 ===")
            print(json.dumps(specific_data, ensure_ascii=False, indent=2))
        else:
            print(f"✗ 未找到 {latest_swap_date} 的核心数据")
        
        # 获取集合统计
        print(f"\n3. 集合统计信息...")
        stats = storage.get_collection_stats()
        print(f"✓ 文档总数: {stats.get('count', 0)}")
        print(f"✓ 集合大小: {stats.get('size', 0)} bytes")
        print(f"✓ 平均文档大小: {stats.get('avgObjSize', 0)} bytes")
        
        storage.close()
        print("\n✓ P4TC核心数据查询完成")
        return True
        
    except Exception as e:
        print(f"✗ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    query_p4tc_core_data()
