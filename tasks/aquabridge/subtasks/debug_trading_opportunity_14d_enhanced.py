#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版调试14天后单边交易机会汇总页面数据抓取
使用浏览器实际查看页面结构，详细分析数据提取过程
"""

import os
import sys
import json
import re
from datetime import datetime

# 添加路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from modules.session_manager import SessionManager
from modules.enhanced_formatter import EnhancedFormatter


def debug_trading_opportunity_14d_enhanced():
    """增强版调试14天后单边交易机会汇总页面"""
    print("=" * 80)
    print("14天后单边交易机会汇总页面数据抓取调试（增强版）")
    print("=" * 80)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        with SessionManager(browser_type="firefox", headless=False) as session:
            # 登录
            print("步骤 1: 登录...")
            if not session.login_once():
                print("✗ 登录失败")
                return False
            print("✓ 登录成功")
            print()
            
            # 抓取原始数据
            print("步骤 2: 抓取 unilateral_trading_opportunity_14d 页面数据...")
            raw_data = session.scrape_page("unilateral_trading_opportunity_14d")
            
            if not raw_data:
                print("✗ 数据抓取失败")
                return False
            
            print(f"✓ 成功抓取到 {len(raw_data)} 个数据块")
            print()
            
            # 分析原始数据
            print("步骤 3: 分析原始数据...")
            for i, data_block in enumerate(raw_data):
                rows = data_block.get('rows', [])
                row_count = len(rows)
                print(f"  数据块 {i+1}: {row_count} 行")
                
                # 显示所有行数据
                if rows:
                    print(f"    所有行数据:")
                    for j, row in enumerate(rows):
                        non_empty = [cell.strip() for cell in row if cell.strip()]
                        if non_empty:
                            print(f"      行 {j+1}: {non_empty}")
                else:
                    print("    ⚠ 数据块为空！")
            
            print()
            
            # 步骤 4: 详细分析页面DOM结构
            print("步骤 4: 详细分析页面DOM结构...")
            try:
                target_frame = session.scraper.find_target_frame()
                if target_frame:
                    # 获取页面所有文本
                    print("  获取页面所有文本...")
                    page_text = target_frame.locator("body").inner_text(timeout=5000)
                    print(f"  页面文本长度: {len(page_text)} 字符")
                    print(f"  前500字符: {page_text[:500]}")
                    print()
                    
                    # 查找所有table标签
                    print("  查找所有table标签...")
                    tables = target_frame.locator("table")
                    table_count = tables.count()
                    print(f"  找到 {table_count} 个table标签")
                    
                    if table_count > 0:
                        for i in range(min(table_count, 3)):
                            print(f"    表格 {i+1}:")
                            rows = tables.nth(i).locator("tr")
                            row_count = rows.count()
                            print(f"      行数: {row_count}")
                            
                            # 分析每一行
                            for j in range(min(row_count, 20)):
                                try:
                                    row = rows.nth(j)
                                    row_text = row.inner_text(timeout=1000).strip()
                                    
                                    if row_text:
                                        print(f"        行 {j+1} 完整文本: {row_text[:200]}")
                                        
                                        # 检查是否包含项目标识
                                        project_ids = ['C5', 'C10', 'P6', 'C3', 'P5', 'P3A', 'S5', 'S1C', 'S2', 'C14', 'S10']
                                        for pid in project_ids:
                                            if pid in row_text:
                                                print(f"          ✓ 包含项目标识: {pid}")
                                        
                                        # 检查是否包含交易方向
                                        if '做多' in row_text or '做空' in row_text:
                                            print(f"          ✓ 包含交易方向")
                                        
                                        # 检查是否包含盈亏比
                                        ratio_match = re.search(r'\d+\.?\d+\s*[:：]\s*1', row_text)
                                        if ratio_match:
                                            print(f"          ✓ 包含盈亏比: {ratio_match.group(0)}")
                                        
                                        # 获取单元格数据
                                        cells = row.locator("td, th")
                                        cell_count = cells.count()
                                        if cell_count > 0:
                                            cell_texts = []
                                            for k in range(min(cell_count, 10)):
                                                try:
                                                    cell_text = cells.nth(k).inner_text(timeout=1000).strip()
                                                    cell_texts.append(cell_text)
                                                except:
                                                    cell_texts.append("")
                                            print(f"          单元格数据: {cell_texts}")
                                except Exception as e:
                                    print(f"        行 {j+1} 分析失败: {e}")
                    
                    # 查找包含项目标识的元素
                    print("  查找包含项目标识的元素...")
                    project_ids = ['C5', 'C10', 'P6', 'C3', 'P5', 'P3A', 'S5', 'S1C', 'S2', 'C14', 'S10']
                    for pid in project_ids[:5]:  # 只检查前5个
                        try:
                            elements = target_frame.locator(f"text='{pid}'").all()
                            if elements:
                                print(f"    找到 {len(elements)} 个包含'{pid}'的元素")
                                for idx, elem in enumerate(elements[:2]):  # 只显示前2个
                                    try:
                                        elem_text = elem.inner_text(timeout=1000).strip()
                                        # 获取父元素的文本
                                        parent = elem.locator("xpath=..")
                                        parent_text = parent.inner_text(timeout=1000).strip()
                                        print(f"      元素 {idx+1}: 自身文本='{elem_text}', 父元素文本='{parent_text[:100]}'")
                                    except:
                                        pass
                        except:
                            pass
                    
                    # 查找包含"盈亏比"的元素
                    print("  查找包含'盈亏比'的元素...")
                    try:
                        profit_loss_elements = target_frame.locator("*:has-text('盈亏比')").all()
                        print(f"  找到 {len(profit_loss_elements)} 个包含'盈亏比'的元素")
                        
                        for idx, elem in enumerate(profit_loss_elements[:10]):
                            try:
                                text = elem.inner_text(timeout=1000)
                                elem_id = elem.get_attribute("id")
                                print(f"    元素 {idx+1}: id={elem_id}, text={text[:100]}")
                            except:
                                pass
                    except Exception as e:
                        print(f"  ⚠ 查找盈亏比元素失败: {e}")
                    
            except Exception as e:
                print(f"  ✗ 分析页面结构失败: {e}")
                import traceback
                traceback.print_exc()
            
            print()
            
            # 步骤 5: 测试格式化器
            print("步骤 5: 测试数据格式化...")
            formatter = EnhancedFormatter()
            formatted_data = formatter.format_data({
                "page_name": "14天后单边交易机会汇总",
                "tables": raw_data
            })
            
            if formatted_data:
                print("✓ 格式化成功")
                print(f"  格式化后的数据结构:")
                print(json.dumps(formatted_data, ensure_ascii=False, indent=2))
                
                # 检查解析结果
                if 'contracts' in formatted_data:
                    contracts = formatted_data['contracts']
                    if 'trading_opportunity_14d_analysis' in contracts:
                        analysis = contracts['trading_opportunity_14d_analysis']
                        opportunities = analysis.get('trading_opportunities', [])
                        print(f"\n  解析到的交易机会数量: {len(opportunities)}")
                        for opp in opportunities:
                            print(f"    - {opp}")
                    else:
                        print("  ⚠ 未找到 trading_opportunity_14d_analysis")
                        if 'raw_table_data' in contracts:
                            raw_data_info = contracts['raw_table_data']
                            print(f"  原始表格数据: {raw_data_info.get('total_rows', 0)} 行")
            else:
                print("✗ 格式化失败")
            
            print()
            print("=" * 80)
            print("调试完成")
            print("=" * 80)
            
            # 等待用户查看
            try:
                input("\n按回车键关闭浏览器...")
            except EOFError:
                import time
                time.sleep(5)
            
            return True
                
    except Exception as e:
        print(f"✗ 调试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    debug_trading_opportunity_14d_enhanced()

