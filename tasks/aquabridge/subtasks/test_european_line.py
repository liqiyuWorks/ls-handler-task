#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
欧线价格信号数据提取测试脚本
用于测试和调试欧线页面的数据抓取和解析功能
"""

import os
import sys
import json
from datetime import datetime

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from modules.session_manager import SessionManager
from subtasks.spider_jinzheng_pages2mgo import SpiderJinzhengPages2mgo


def test_european_line_extraction():
    """测试欧线数据提取"""
    print("=" * 80)
    print("欧线价格信号数据提取测试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 使用非无头模式以便调试
        with SessionManager(browser_type="chromium", headless=False) as session:
            # 登录
            print("步骤 1: 登录...")
            if not session.login_once():
                print("✗ 登录失败")
                return False
            print("✓ 登录成功")
            print()
            
            # 抓取原始数据
            print("步骤 2: 抓取 european_line_signals 页面数据...")
            raw_data = session.scrape_page("european_line_signals")
            
            if not raw_data:
                print("✗ 数据抓取失败")
                return False
            
            print(f"✓ 成功抓取到 {len(raw_data)} 个数据块")
            print()
            
            # 分析原始数据
            print("步骤 3: 分析原始数据...")
            total_rows = 0
            for i, data_block in enumerate(raw_data):
                rows = data_block.get('rows', [])
                row_count = len(rows)
                total_rows += row_count
                swap_date = data_block.get('swap_date', 'N/A')
                print(f"  数据块 {i+1}: {row_count} 行, 掉期日期: {swap_date}")
                
                # 显示前几行数据
                if rows:
                    print(f"    前5行示例:")
                    for j, row in enumerate(rows[:5]):
                        non_empty = [cell.strip() for cell in row if cell.strip()]
                        if non_empty:
                            print(f"      行 {j+1}: {non_empty[:8]}")  # 只显示前8个单元格
            
            print(f"\n总计: {total_rows} 行数据")
            print()
            
            # 检查数据质量
            print("步骤 4: 检查数据质量...")
            all_text = ""
            for data_block in raw_data:
                for row in data_block.get('rows', []):
                    all_text += " ".join([str(cell) for cell in row]) + " "
            
            # 检查欧线关键词
            european_line_keywords = [
                "预测值", "当前值", "偏离度", 
                "开空入场区间", "平空离场区间", "操作建议",
                "收盘价日期", "欧线", "平空", "开空"
            ]
            found_keywords = [kw for kw in european_line_keywords if kw in all_text]
            
            print(f"  找到关键词: {', '.join(found_keywords) if found_keywords else '无'}")
            print(f"  关键词覆盖率: {len(found_keywords)}/{len(european_line_keywords)}")
            
            if len(found_keywords) >= 5:
                print("  ✓ 数据质量良好")
            else:
                print("  ⚠ 数据质量可能有问题")
            
            print()
            
            # 使用SpiderJinzhengPages2mgo进行格式化
            print("步骤 5: 格式化数据...")
            spider = SpiderJinzhengPages2mgo()
            
            # format_data方法接受page_key和raw_data（List[Dict]）
            formatted_data = spider.format_data("european_line_signals", raw_data)
            
            if not formatted_data:
                print("  ✗ 数据格式化失败")
            else:
                print("  ✓ 数据格式化成功")
                print()
                
                # 显示格式化后的数据摘要
                print("步骤 6: 格式化数据摘要...")
                metadata = formatted_data.get('metadata', {})
                contracts = formatted_data.get('contracts', {})
                summary = formatted_data.get('summary', {})
                
                print(f"  页面名称: {metadata.get('page_name', 'N/A')}")
                print(f"  掉期日期: {metadata.get('swap_date', 'N/A')}")
                print(f"  数据源: {metadata.get('data_source', 'N/A')}")
                print()
                
                # 显示欧线分析数据
                if "european_line_analysis" in contracts:
                    analysis = contracts["european_line_analysis"]
                    print("  欧线分析数据:")
                    
                    # 价格信号
                    price_signals = analysis.get('price_signals', {})
                    if price_signals:
                        print(f"    预测值: {price_signals.get('predicted_value', 'N/A')}")
                        print(f"    当前值: {price_signals.get('current_value', 'N/A')}")
                        print(f"    偏离度: {price_signals.get('deviation', 'N/A')}")
                    
                    # 交易区间
                    trading_ranges = analysis.get('trading_ranges', {})
                    if trading_ranges:
                        print(f"    开空入场区间: {trading_ranges.get('short_entry_range', 'N/A')}")
                        print(f"    平空离场区间: {trading_ranges.get('short_exit_range', 'N/A')}")
                    
                    # 操作建议
                    operation = analysis.get('operation_suggestion')
                    if operation:
                        print(f"    操作建议: {operation}")
                    
                    # 收盘价日期
                    closing_date = analysis.get('closing_price_date')
                    if closing_date:
                        print(f"    收盘价日期: {closing_date}")
                
                print()
                print(f"  摘要信息:")
                print(f"    数据类型: {summary.get('data_type', 'N/A')}")
                print(f"    合约数量: {summary.get('total_contracts', 0)}")
                print(f"    数据质量: {summary.get('data_quality', 'N/A')}")
            
            print()
            
            # 保存数据
            print("步骤 7: 保存数据...")
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 保存原始数据
            raw_filename = os.path.join(output_dir, f"european_line_raw_data_{timestamp}.json")
            with open(raw_filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": timestamp,
                    "page_key": "european_line_signals",
                    "total_blocks": len(raw_data),
                    "total_rows": total_rows,
                    "found_keywords": found_keywords,
                    "data": raw_data
                }, f, ensure_ascii=False, indent=2)
            print(f"  ✓ 原始数据已保存到: {raw_filename}")
            
            # 保存格式化数据
            if formatted_data:
                formatted_filename = os.path.join(output_dir, f"european_line_formatted_data_{timestamp}.json")
                with open(formatted_filename, 'w', encoding='utf-8') as f:
                    json.dump(formatted_data, f, ensure_ascii=False, indent=2)
                print(f"  ✓ 格式化数据已保存到: {formatted_filename}")
            
            print()
            
            # 字段映射检查
            print("步骤 8: 检查字段映射...")
            check_field_mapping(raw_data)
            print()
            
            # 数据准确性验证
            print("步骤 9: 数据准确性验证...")
            validate_data_accuracy(formatted_data)
            print()
            
            print("=" * 80)
            print("✓ 测试完成")
            print("=" * 80)
            
            return True
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_field_mapping(data_blocks):
    """检查字段映射"""
    # 欧线页面应该包含的字段
    expected_fields = {
        "预测值": ["预测值"],
        "当前值": ["当前值"],
        "偏离度": ["偏离度", "%"],
        "开空入场区间": ["开空入场区间", ">"],
        "平空离场区间": ["平空离场区间", "<"],
        "操作建议": ["操作建议", "平空", "开空", "平多", "开多"],
        "收盘价日期": ["收盘价日期", "2025-", "2026-"]
    }
    
    all_text = ""
    for block in data_blocks:
        for row in block.get('rows', []):
            all_text += " ".join([str(cell) for cell in row]) + " "
    
    print("  字段映射检查:")
    for field_name, keywords in expected_fields.items():
        found = any(kw in all_text for kw in keywords)
        status = "✓" if found else "✗"
        print(f"    {status} {field_name}: {'找到' if found else '未找到'}")
    
    # 检查数据行数
    total_rows = sum(len(block.get('rows', [])) for block in data_blocks)
    if total_rows >= 5:
        print(f"    ✓ 数据行数: {total_rows} (充足)")
    else:
        print(f"    ⚠ 数据行数: {total_rows} (可能不足)")


def validate_data_accuracy(formatted_data):
    """验证数据准确性"""
    if not formatted_data:
        print("  ✗ 无格式化数据可验证")
        return
    
    contracts = formatted_data.get('contracts', {})
    analysis = contracts.get('european_line_analysis', {})
    
    if not analysis:
        print("  ✗ 未找到欧线分析数据")
        return
    
    print("  数据准确性检查:")
    
    # 检查价格信号
    price_signals = analysis.get('price_signals', {})
    checks = [
        ("预测值", price_signals.get('predicted_value')),
        ("当前值", price_signals.get('current_value')),
        ("偏离度", price_signals.get('deviation'))
    ]
    
    for name, value in checks:
        if value:
            print(f"    ✓ {name}: {value}")
        else:
            print(f"    ✗ {name}: 缺失")
    
    # 检查交易区间
    trading_ranges = analysis.get('trading_ranges', {})
    range_checks = [
        ("开空入场区间", trading_ranges.get('short_entry_range')),
        ("平空离场区间", trading_ranges.get('short_exit_range'))
    ]
    
    for name, value in range_checks:
        if value:
            print(f"    ✓ {name}: {value}")
        else:
            print(f"    ✗ {name}: 缺失")
    
    # 检查操作建议
    operation = analysis.get('operation_suggestion')
    if operation:
        print(f"    ✓ 操作建议: {operation}")
    else:
        print(f"    ✗ 操作建议: 缺失")
    
    # 检查收盘价日期
    closing_date = analysis.get('closing_price_date')
    if closing_date:
        print(f"    ✓ 收盘价日期: {closing_date}")
    else:
        print(f"    ✗ 收盘价日期: 缺失")
    
    # 总体评估
    all_fields = [
        price_signals.get('predicted_value'),
        price_signals.get('current_value'),
        price_signals.get('deviation'),
        trading_ranges.get('short_entry_range'),
        trading_ranges.get('short_exit_range'),
        operation,
        closing_date
    ]
    
    filled_count = sum(1 for field in all_fields if field)
    total_count = len(all_fields)
    accuracy = (filled_count / total_count * 100) if total_count > 0 else 0
    
    print(f"\n  数据完整性: {filled_count}/{total_count} ({accuracy:.1f}%)")
    
    if accuracy >= 80:
        print("    ✓ 数据准确性良好")
    elif accuracy >= 50:
        print("    ⚠ 数据准确性一般")
    else:
        print("    ✗ 数据准确性较差")


if __name__ == "__main__":
    success = test_european_line_extraction()
    sys.exit(0 if success else 1)

