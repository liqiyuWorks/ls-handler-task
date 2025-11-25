#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试C3现货应用决策数据解析
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules'))

from spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo

def test_c3_spot_decision():
    """测试C3现货应用决策数据解析"""
    print("="*60)
    print("C3现货应用决策数据解析测试")
    print("="*60)
    
    spider = SpiderJinzhengPages2mgo()
    page_key = 'c3_spot_decision'
    
    # 检查页面配置
    if page_key not in spider.supported_pages:
        print(f"✗ 页面 {page_key} 未在 supported_pages 中找到")
        return False
    
    page_info = spider.supported_pages[page_key]
    print(f"\n✓ 页面配置:")
    print(f"  名称: {page_info['name']}")
    print(f"  描述: {page_info['description']}")
    
    # 检查页面配置
    try:
        from modules.page_config import get_page_config
        page_config = get_page_config(page_key)
        if page_config:
            print(f"\n✓ 页面导航配置:")
            print(f"  名称: {page_config.name}")
            print(f"  导航步骤数: {len(page_config.navigation_path)}")
            print(f"  数据提取配置:")
            print(f"    max_rows: {page_config.data_extraction_config.get('max_rows')}")
            print(f"    max_cells: {page_config.data_extraction_config.get('max_cells')}")
            print(f"    wait_after_query: {page_config.data_extraction_config.get('wait_after_query')}")
        else:
            print(f"\n✗ 页面配置未找到")
            return False
    except Exception as e:
        print(f"\n✗ 检查页面配置时出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试解析器
    try:
        from modules.spot_decision_parser import SpotDecisionParser
        
        parser = SpotDecisionParser()
        
        # 模拟C3数据
        test_rows = [
            ['C3现货应用决策', '', '', ''],
            ['做多胜率统计', '', '', ''],
            ['盈亏比', '3.43:1', '', ''],
            ['建议交易方向', '做多', '', ''],
            ['日期', '2025-11-24', '', ''],
            ['当期值', '24.74', '', ''],
            ['综合价差比', '5%', '', ''],
            ['综合价差比区间', '0% - 15%', '', ''],
            ['2026-01-05预测值', '25.87', '', ''],
            ['在全部交易日期中出现概率', '19%', '', ''],
            ['C3盈亏比', '', '', ''],
            ['日期', '2025-11-24', '', ''],
            ['当前价格/元每吨', '24.74', '', ''],
            ['评估价格/元每吨', '24.25', '', ''],
            ['价差比', '-2%', '', ''],
            ['42天后盈利比例', '63%', '', ''],
            ['收益均值', '12%', '', ''],
            ['42天后亏损比例', '37%', '', ''],
            ['亏损均值/元每吨', '6%', '', ''],
            ['最大收益时间在各时间段的出现概率', '', '', ''],
            ['0~14天', '45%', '', ''],
            ['15天~28天', '27%', '', ''],
            ['29天~42天', '28%', '', ''],
            ['最大风险均值/元每吨', '-7%', '', ''],
            ['最大风险极值/元每吨', '-29%', '', ''],
            ['最大风险时间在各时间段的出现概率', '', '', ''],
            ['0~14天', '42%', '', ''],
            ['15天~28天', '29%', '', ''],
            ['29天~42天', '29%', '', ''],
        ]
        
        result = parser.parse_spot_decision_data(test_rows, 'C3现货应用决策')
        
        print(f"\n✓ 解析器测试:")
        print(f"  产品类型: {result.get('metadata', {}).get('product_type')}")
        print(f"  版本: {result.get('metadata', {}).get('version')}")
        
        # 验证关键字段
        c3_profit_loss = result.get('c3_profit_loss_ratio', {})
        required_fields = ['current_price', 'evaluated_price', 'price_difference_ratio', 
                          'profit_ratio_42d', 'profit_average_42d', 'loss_ratio_42d', 'loss_average_42d',
                          'max_risk_average', 'max_risk_extreme']
        missing_fields = [field for field in required_fields if not c3_profit_loss.get(field)]
        
        if missing_fields:
            print(f"  ⚠ 缺少字段: {missing_fields}")
            return False
        else:
            print(f"  ✓ 所有关键字段都已提取")
        
        # 验证交易建议
        trading_rec = result.get('trading_recommendation', {})
        if trading_rec.get('statistics_type') == '做多胜率统计':
            print(f"  ✓ 交易建议统计类型正确（做多胜率统计）")
        else:
            print(f"  ⚠ 交易建议统计类型: {trading_rec.get('statistics_type')}")
        
        # 验证时间分布
        max_profit_timing = c3_profit_loss.get('max_profit_timing_distribution', {})
        max_risk_timing = c3_profit_loss.get('max_risk_timing_distribution', {})
        if len(max_profit_timing) == 3 and len(max_risk_timing) == 3:
            print(f"  ✓ 时间分布数据完整")
        else:
            print(f"  ⚠ 时间分布数据不完整")
            print(f"    最大收益时间分布: {len(max_profit_timing)}/3")
            print(f"    最大风险时间分布: {len(max_risk_timing)}/3")
        
    except Exception as e:
        print(f"\n✗ 解析器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n✓ C3现货应用决策解析测试通过")
    return True

if __name__ == '__main__':
    success = test_c3_spot_decision()
    sys.exit(0 if success else 1)

