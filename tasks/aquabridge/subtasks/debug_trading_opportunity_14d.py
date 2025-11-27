#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试14天后单边交易机会汇总页面数据抓取
使用浏览器实际查看页面结构，特别是盈亏比数据的定位
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


def debug_trading_opportunity_14d():
    """调试14天后单边交易机会汇总页面"""
    print("=" * 80)
    print("14天后单边交易机会汇总页面数据抓取调试")
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
                
                # 显示前10行数据
                if rows:
                    print(f"    前10行示例:")
                    for j, row in enumerate(rows[:10]):
                        non_empty = [cell.strip() for cell in row if cell.strip()]
                        if non_empty:
                            print(f"      行 {j+1}: {non_empty}")
            
            print()
            
            # 步骤 4: 使用XPath查找盈亏比元素
            print("步骤 4: 使用XPath查找盈亏比元素...")
            try:
                target_frame = session.scraper.find_target_frame()
                if target_frame:
                    # 尝试查找用户提供的XPath
                    xpath = "//*[@id='BF11-0-0']"
                    print(f"  尝试查找: {xpath}")
                    
                    try:
                        element = target_frame.locator(f"xpath={xpath}").first
                        if element.is_visible(timeout=3000):
                            text = element.inner_text(timeout=1000)
                            print(f"  ✓ 找到元素，文本内容: {text}")
                            
                            # 获取元素的更多信息
                            try:
                                tag_name = element.evaluate("el => el.tagName")
                                class_name = element.evaluate("el => el.className")
                                print(f"    标签名: {tag_name}")
                                print(f"    类名: {class_name}")
                            except:
                                pass
                        else:
                            print(f"  ✗ 元素不可见")
                    except Exception as e:
                        print(f"  ✗ 查找元素失败: {e}")
                    
                    # 尝试查找所有包含"BF11"的ID
                    print("  查找所有包含'BF11'的ID...")
                    try:
                        # 使用JavaScript查找所有包含BF11的元素
                        elements_with_bf11 = target_frame.locator("[id*='BF11']").all()
                        print(f"  找到 {len(elements_with_bf11)} 个包含'BF11'的元素")
                        
                        for idx, elem in enumerate(elements_with_bf11[:20]):  # 只显示前20个
                            try:
                                elem_id = elem.get_attribute("id")
                                text = elem.inner_text(timeout=1000)
                                print(f"    元素 {idx+1}: id={elem_id}, text={text[:50]}")
                            except:
                                pass
                    except Exception as e:
                        print(f"  ⚠ 查找BF11元素失败: {e}")
                    
                    # 查找所有包含盈亏比的元素
                    print("  查找所有包含'盈亏比'的元素...")
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
                    
                    # 查找所有包含数字和冒号的元素（可能是盈亏比）
                    print("  查找所有包含数字和冒号的元素（可能是盈亏比）...")
                    try:
                        # 获取页面所有文本
                        page_text = target_frame.locator("body").inner_text(timeout=5000)
                        
                        # 查找所有匹配 "数字: 1" 或 "数字:1" 模式的文本
                        import re
                        patterns = [
                            r'\d+\.?\d*\s*[：:]\s*1',
                            r'\d+\.?\d*\s*[：:]1',
                        ]
                        
                        for pattern in patterns:
                            matches = re.findall(pattern, page_text)
                            if matches:
                                print(f"  找到匹配 '{pattern}' 的文本:")
                                for match in matches[:20]:  # 只显示前20个
                                    print(f"    {match}")
                    except Exception as e:
                        print(f"  ⚠ 查找盈亏比模式失败: {e}")
                    
                    # 查找表格结构
                    print("  分析表格结构...")
                    try:
                        # 查找所有table
                        tables = target_frame.locator("table")
                        table_count = tables.count()
                        print(f"  找到 {table_count} 个table标签")
                        
                        if table_count > 0:
                            for i in range(min(table_count, 3)):  # 只分析前3个表格
                                print(f"    表格 {i+1}:")
                                try:
                                    rows = tables.nth(i).locator("tr")
                                    row_count = rows.count()
                                    print(f"      行数: {row_count}")
                                    
                                    # 显示前5行
                                    for j in range(min(5, row_count)):
                                        try:
                                            cells = rows.nth(j).locator("td, th")
                                            cell_count = cells.count()
                                            cell_texts = []
                                            for k in range(min(cell_count, 10)):
                                                try:
                                                    cell_text = cells.nth(k).inner_text(timeout=1000).strip()
                                                    cell_texts.append(cell_text)
                                                except:
                                                    cell_texts.append("")
                                            print(f"        行 {j+1}: {cell_texts}")
                                        except:
                                            pass
                                except Exception as e:
                                    print(f"      ⚠ 分析表格 {i+1} 失败: {e}")
                    except Exception as e:
                        print(f"  ⚠ 分析表格结构失败: {e}")
                    
                    # 查找所有包含项目标识（C5, C10等）的元素
                    print("  查找所有包含项目标识（C5, C10等）的元素...")
                    try:
                        project_patterns = ['C5', 'C10', 'P6', 'C3', 'P5', 'P3A', 'S5', 'S1C', 'S2', 'C14', 'S10']
                        
                        for pattern in project_patterns[:5]:  # 只检查前5个
                            try:
                                elements = target_frame.locator(f"text='{pattern}'").all()
                                if elements:
                                    print(f"    找到 {len(elements)} 个包含'{pattern}'的元素")
                                    for idx, elem in enumerate(elements[:3]):
                                        try:
                                            # 获取父元素和兄弟元素
                                            parent = elem.evaluate_handle("el => el.parentElement")
                                            if parent:
                                                parent_text = parent.inner_text() if hasattr(parent, 'inner_text') else ""
                                                print(f"      元素 {idx+1}: 父元素文本={parent_text[:100]}")
                                        except:
                                            pass
                            except:
                                pass
                    except Exception as e:
                        print(f"  ⚠ 查找项目标识失败: {e}")
                    
            except Exception as e:
                print(f"  ✗ 分析页面结构失败: {e}")
                import traceback
                traceback.print_exc()
            
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
    debug_trading_opportunity_14d()

