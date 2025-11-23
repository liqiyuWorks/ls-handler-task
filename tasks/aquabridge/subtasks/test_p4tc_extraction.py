#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的P4TC数据提取测试脚本
直接测试数据提取功能，不依赖复杂的导入
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


def test_p4tc_extraction():
    """测试P4TC数据提取"""
    print("=" * 80)
    print("P4TC现货应用决策数据提取测试")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        with SessionManager(browser_type="chromium", headless=False) as session:
            # 登录
            print("步骤 1: 登录...")
            if not session.login_once():
                print("✗ 登录失败")
                return False
            print("✓ 登录成功")
            print()
            
            # 抓取数据
            print("步骤 2: 抓取 p4tc_spot_decision 页面数据...")
            raw_data = session.scrape_page("p4tc_spot_decision")
            
            if not raw_data:
                print("✗ 数据抓取失败")
                return False
            
            print(f"✓ 成功抓取到 {len(raw_data)} 个数据块")
            print()
            
            # 分析数据
            print("步骤 3: 分析数据...")
            total_rows = 0
            for i, data_block in enumerate(raw_data):
                rows = data_block.get('rows', [])
                row_count = len(rows)
                total_rows += row_count
                data_type = data_block.get('data_type', 'unknown')
                print(f"  数据块 {i+1}: {row_count} 行, 类型: {data_type}")
                
                # 显示前几行数据
                if rows:
                    print(f"    前3行示例:")
                    for j, row in enumerate(rows[:3]):
                        print(f"      行 {j+1}: {row[:5]}")  # 只显示前5个单元格
            
            print(f"\n总计: {total_rows} 行数据")
            print()
            
            # 检查数据质量
            print("步骤 4: 检查数据质量...")
            all_text = ""
            for data_block in raw_data:
                for row in data_block.get('rows', []):
                    all_text += " ".join([str(cell) for cell in row]) + " "
            
            # 检查P4TC关键词
            p4tc_keywords = ["做多", "做空", "盈亏比", "价差比", "预测值", "正收益", "负收益", "P4TC"]
            found_keywords = [kw for kw in p4tc_keywords if kw in all_text]
            
            print(f"  找到关键词: {', '.join(found_keywords) if found_keywords else '无'}")
            print(f"  关键词覆盖率: {len(found_keywords)}/{len(p4tc_keywords)}")
            
            if len(found_keywords) >= 3:
                print("  ✓ 数据质量良好")
            else:
                print("  ⚠ 数据质量可能有问题")
            
            print()
            
            # 保存数据
            print("步骤 5: 保存数据...")
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(output_dir, f"p4tc_test_data_{timestamp}.json")
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": timestamp,
                    "page_key": "p4tc_spot_decision",
                    "total_blocks": len(raw_data),
                    "total_rows": total_rows,
                    "found_keywords": found_keywords,
                    "data": raw_data
                }, f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ 数据已保存到: {filename}")
            print()
            
            # 字段映射检查
            print("步骤 6: 检查字段映射...")
            check_field_mapping(raw_data)
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
    # P4TC页面应该包含的字段
    expected_fields = {
        "交易方向": ["做多", "做空"],
        "盈亏比": ["盈亏比"],
        "日期": ["日期", "2025-", "2026-"],
        "当期值": ["当期值", "当前值"],
        "价差比": ["价差比", "%"],
        "预测值": ["预测值"],
        "出现概率": ["出现概率", "概率"],
        "正收益": ["正收益"],
        "负收益": ["负收益"]
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
    if total_rows >= 20:
        print(f"    ✓ 数据行数: {total_rows} (充足)")
    else:
        print(f"    ⚠ 数据行数: {total_rows} (可能不足)")


if __name__ == "__main__":
    success = test_p4tc_extraction()
    sys.exit(0 if success else 1)

