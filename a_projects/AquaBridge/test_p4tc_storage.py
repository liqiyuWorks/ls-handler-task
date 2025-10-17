#!/usr/bin/env python3
"""
测试P4TC现货应用决策数据的MongoDB存储功能
"""

import json
from datetime import datetime
from mongodb_storage import MongoDBStorage, load_config


def test_p4tc_storage():
    """测试P4TC数据存储"""
    print("=== P4TC现货应用决策数据存储测试 ===")
    
    # 加载配置
    config = load_config()
    if not config.get('enabled', False):
        print("✗ MongoDB存储已禁用")
        return False
    
    try:
        # 创建存储实例
        storage = MongoDBStorage(config, "p4tc_spot_decision")
        
        # 模拟P4TC数据
        test_data = {
            "metadata": {
                "timestamp": "20251017_210000",
                "browser": "firefox",
                "page_name": "P4TC现货应用决策",
                "swap_date": "2025-10-17",
                "data_source": "AquaBridge",
                "version": "1.0"
            },
            "contracts": {
                "raw_table_data": {
                    "description": "P4TC现货应用决策原始数据",
                    "total_rows": 55,
                    "data": [
                        ["做空胜率统计", "盈亏比：", "3.33：1"],
                        ["做空", "2025-10-16", "15097", "-5%"],
                        ["建议交易方向", "-15% - 0%", "14418", "30%"]
                    ],
                    "last_updated": datetime.now().isoformat()
                },
                "p4tc_analysis": {
                    "metadata": {
                        "page_name": "P4TC现货应用决策",
                        "parsed_at": datetime.now().isoformat(),
                        "data_source": "AquaBridge"
                    },
                    "trading_recommendation": {
                        "profit_loss_ratio": 3.33,
                        "recommended_direction": "做空",
                        "direction_confidence": "高"
                    },
                    "current_forecast": {
                        "date": "2025-10-16",
                        "high_expected_value": 15097,
                        "price_difference_ratio": "-5%",
                        "price_difference_range": "-15% - 0%",
                        "forecast_value": 14418,
                        "probability": 30
                    },
                    "historical_forecasts": [],
                    "positive_returns": {
                        "final_positive_returns_percentage": None,
                        "final_positive_returns_average": None,
                        "distribution": {},
                        "statistics": {},
                        "timing_distribution": {}
                    },
                    "negative_returns": {
                        "final_negative_returns_percentage": None,
                        "final_negative_returns_average": None,
                        "distribution": {},
                        "statistics": {}
                    },
                    "model_evaluation": {
                        "current_price": None,
                        "forecast_42day_price_difference": None,
                        "forecast_42day_price": None,
                        "price_difference_ratio": "-5%",
                        "evaluation_ranges": []
                    }
                }
            }
        }
        
        # 存储数据
        print("1. 存储P4TC数据...")
        success = storage.store_ffa_data(test_data)
        if success:
            print("✓ P4TC数据存储成功")
        else:
            print("✗ P4TC数据存储失败")
            return False
        
        # 获取核心数据
        print("\n2. 获取P4TC核心数据...")
        core_data = storage.get_p4tc_core_data("2025-10-17")
        if core_data:
            print("✓ P4TC核心数据获取成功")
            print("\n=== 核心数据内容 ===")
            print(json.dumps(core_data, ensure_ascii=False, indent=2))
        else:
            print("✗ P4TC核心数据获取失败")
            return False
        
        # 列出核心数据
        print("\n3. 列出P4TC核心数据...")
        core_data_list = storage.list_p4tc_core_data(limit=5)
        if core_data_list:
            print(f"✓ 获取到 {len(core_data_list)} 条P4TC核心数据")
            for i, data in enumerate(core_data_list, 1):
                print(f"{i}. swap_date: {data.get('swap_date')}")
                core = data.get('core_data', {})
                trading_rec = core.get('trading_recommendation', {})
                print(f"   盈亏比: {trading_rec.get('profit_loss_ratio')}")
                print(f"   交易方向: {trading_rec.get('recommended_direction')}")
        else:
            print("✗ P4TC核心数据列表获取失败")
            return False
        
        # 获取统计信息
        print("\n4. 获取集合统计信息...")
        stats = storage.get_collection_stats()
        print(f"✓ 集合统计: {stats}")
        
        storage.close()
        print("\n✓ P4TC数据存储测试完成")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_p4tc_storage()
