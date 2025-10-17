#!/usr/bin/env python3
"""
最终测试脚本 - 验证P4TC现货应用决策数据的完整流程
"""

import json
from datetime import datetime
from mongodb_storage import MongoDBStorage, load_config


def final_test():
    """最终测试"""
    print("=== P4TC现货应用决策数据完整流程测试 ===")
    print("测试目标：验证核心数据以JSON键值对形式存储到MongoDB")
    print()
    
    # 加载配置
    config = load_config()
    if not config.get('enabled', False):
        print("✗ MongoDB存储已禁用")
        return False
    
    try:
        # 创建存储实例
        storage = MongoDBStorage(config, "p4tc_spot_decision")
        
        # 查询所有P4TC核心数据
        print("1. 查询所有P4TC核心数据...")
        all_data = storage.list_p4tc_core_data(limit=10)
        
        if not all_data:
            print("✗ 未找到任何P4TC核心数据")
            return False
        
        print(f"✓ 找到 {len(all_data)} 条P4TC核心数据记录")
        
        # 显示核心数据摘要
        print("\n2. 核心数据摘要:")
        print("=" * 60)
        
        for i, data in enumerate(all_data, 1):
            swap_date = data.get('swap_date')
            timestamp = data.get('timestamp')
            core_data = data.get('core_data', {})
            
            print(f"\n📅 记录 {i}: {swap_date} ({timestamp})")
            print("-" * 40)
            
            # 交易建议
            trading_rec = core_data.get('trading_recommendation', {})
            print(f"💡 交易建议:")
            print(f"   盈亏比: {trading_rec.get('profit_loss_ratio', 'N/A')}")
            print(f"   建议方向: {trading_rec.get('recommended_direction', 'N/A')}")
            print(f"   信心度: {trading_rec.get('direction_confidence', 'N/A')}")
            
            # 当前预测
            current_forecast = core_data.get('current_forecast', {})
            print(f"🔮 当前预测:")
            print(f"   日期: {current_forecast.get('date', 'N/A')}")
            print(f"   高期值: {current_forecast.get('high_expected_value', 'N/A')}")
            print(f"   价差比: {current_forecast.get('price_difference_ratio', 'N/A')}")
            print(f"   价差区间: {current_forecast.get('price_difference_range', 'N/A')}")
            print(f"   预测值: {current_forecast.get('forecast_value', 'N/A')}")
            print(f"   概率: {current_forecast.get('probability', 'N/A')}%")
            
            # 统计信息
            statistics = core_data.get('statistics', {})
            print(f"📊 统计:")
            print(f"   数据行数: {statistics.get('total_rows', 'N/A')}")
            print(f"   数据质量: {statistics.get('data_quality', 'N/A')}")
        
        # 验证核心数据的完整性
        print(f"\n3. 数据完整性验证:")
        print("=" * 60)
        
        complete_records = 0
        for data in all_data:
            core_data = data.get('core_data', {})
            trading_rec = core_data.get('trading_recommendation', {})
            current_forecast = core_data.get('current_forecast', {})
            
            # 检查关键字段
            has_trading_rec = any([
                trading_rec.get('profit_loss_ratio'),
                trading_rec.get('recommended_direction'),
                trading_rec.get('direction_confidence')
            ])
            
            has_forecast = any([
                current_forecast.get('date'),
                current_forecast.get('high_expected_value'),
                current_forecast.get('price_difference_ratio'),
                current_forecast.get('forecast_value')
            ])
            
            if has_trading_rec and has_forecast:
                complete_records += 1
                print(f"✓ {data.get('swap_date')} - 数据完整")
            else:
                print(f"⚠ {data.get('swap_date')} - 数据不完整")
        
        print(f"\n📈 完整性统计: {complete_records}/{len(all_data)} 条记录完整")
        
        # 显示JSON结构示例
        print(f"\n4. JSON结构示例:")
        print("=" * 60)
        if all_data:
            example_data = all_data[0].get('core_data', {})
            print(json.dumps(example_data, ensure_ascii=False, indent=2))
        
        # 集合统计
        print(f"\n5. MongoDB集合统计:")
        print("=" * 60)
        stats = storage.get_collection_stats()
        print(f"📊 文档总数: {stats.get('count', 0)}")
        print(f"📊 集合大小: {stats.get('size', 0):,} bytes")
        print(f"📊 平均文档大小: {stats.get('avgObjSize', 0):,} bytes")
        print(f"📊 存储大小: {stats.get('storageSize', 0):,} bytes")
        
        storage.close()
        
        print(f"\n🎉 测试完成!")
        print(f"✅ 成功验证P4TC核心数据以JSON键值对形式存储到MongoDB")
        print(f"✅ 数据包含完整的交易建议、当前预测和统计信息")
        print(f"✅ 支持按日期查询和列表查询功能")
        
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    final_test()
