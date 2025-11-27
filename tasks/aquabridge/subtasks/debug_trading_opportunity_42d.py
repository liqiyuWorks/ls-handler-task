#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试42天后单边交易机会汇总页面数据抓取
使用浏览器实际查看页面结构，特别是现货和期货数据的定位
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


def debug_trading_opportunity_42d():
    """调试42天后单边交易机会汇总页面"""
    print("=" * 80)
    print("42天后单边交易机会汇总页面数据抓取调试")
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
            print("步骤 2: 抓取 unilateral_trading_opportunity_42d 页面数据...")
            raw_data = session.scrape_page("unilateral_trading_opportunity_42d")
            
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
            
            print()
            
            # 步骤 4: 分析页面DOM结构
            print("步骤 4: 分析页面DOM结构...")
            try:
                target_frame = session.scraper.find_target_frame()
                if target_frame:
                    # 获取页面所有文本
                    print("  获取页面所有文本...")
                    page_text = target_frame.locator("body").inner_text(timeout=10000)
                    print(f"  页面文本长度: {len(page_text)} 字符")
                    
                    # 查找"现货"和"期货"的位置
                    print("  查找'现货'和'期货'标签...")
                    try:
                        spot_elements = target_frame.locator("*:has-text('现货')").all()
                        futures_elements = target_frame.locator("*:has-text('期货')").all()
                        print(f"  找到 {len(spot_elements)} 个包含'现货'的元素")
                        print(f"  找到 {len(futures_elements)} 个包含'期货'的元素")
                        
                        # 分析现货和期货元素的结构
                        for idx, elem in enumerate(spot_elements[:3]):
                            try:
                                elem_id = elem.get_attribute("id")
                                text = elem.inner_text(timeout=1000)
                                print(f"    现货元素 {idx+1}: id={elem_id}, text={text[:100]}")
                            except:
                                pass
                        
                        for idx, elem in enumerate(futures_elements[:3]):
                            try:
                                elem_id = elem.get_attribute("id")
                                text = elem.inner_text(timeout=1000)
                                print(f"    期货元素 {idx+1}: id={elem_id}, text={text[:100]}")
                            except:
                                pass
                    except Exception as e:
                        print(f"  ⚠ 查找现货/期货标签失败: {e}")
                    
                    # 查找所有包含项目标识的元素
                    print("  查找所有包含项目标识的元素...")
                    project_ids = ['C5', 'P6', 'P4', 'C5TC', 'S4B', 'C10', 'S10', 'C3', 'P4TC', 
                                  'P3A', 'S15', 'C14', 'P5', 'P2', 'C9', 'S5', 'P0', 'C16', 
                                  'S8', 'S9', 'S1C', 'S2', 'P1A', 'S1B', 'S4A', 'C8', 'S3',
                                  'P4TC+1', 'C5TC+1', 'C5+1']
                    
                    for project_id in project_ids[:10]:  # 只检查前10个
                        try:
                            elements = target_frame.locator(f"text='{project_id}'").all()
                            if elements:
                                print(f"    找到 {len(elements)} 个包含'{project_id}'的元素")
                                for idx, elem in enumerate(elements[:2]):
                                    try:
                                        elem_id = elem.get_attribute("id")
                                        # 获取父元素信息
                                        parent_info = elem.evaluate("""
                                            el => {
                                                const parent = el.parentElement;
                                                if (parent) {
                                                    return {
                                                        parentId: parent.id || '',
                                                        parentTag: parent.tagName || '',
                                                        siblings: Array.from(parent.children).map(c => ({
                                                            id: c.id || '',
                                                            tag: c.tagName || '',
                                                            text: (c.innerText || c.textContent || '').substring(0, 50)
                                                        }))
                                                    };
                                                }
                                                return null;
                                            }
                                        """)
                                        if parent_info:
                                            print(f"      元素 {idx+1}: id={elem_id}")
                                            print(f"        父元素: id={parent_info.get('parentId')}, tag={parent_info.get('parentTag')}")
                                            siblings = parent_info.get('siblings', [])[:5]
                                            print(f"        兄弟元素 (前5个): {[s.get('text', '') for s in siblings]}")
                                    except Exception as e:
                                        print(f"      ⚠ 分析元素失败: {e}")
                        except:
                            pass
                    
                    # 查找所有包含"做多"或"做空"的元素
                    print("  查找所有包含'做多'或'做空'的元素...")
                    try:
                        direction_elements = target_frame.locator("*:has-text('做多'), *:has-text('做空')").all()
                        print(f"  找到 {len(direction_elements)} 个包含交易方向的元素")
                        
                        for idx, elem in enumerate(direction_elements[:10]):
                            try:
                                elem_id = elem.get_attribute("id")
                                text = elem.inner_text(timeout=1000)
                                print(f"    方向元素 {idx+1}: id={elem_id}, text={text[:50]}")
                            except:
                                pass
                    except Exception as e:
                        print(f"  ⚠ 查找交易方向元素失败: {e}")
                    
                    # 查找所有包含数字和冒号的元素（可能是盈亏比）
                    print("  查找所有包含数字和冒号的元素（可能是盈亏比）...")
                    try:
                        # 使用JavaScript查找所有包含 ": 1" 或 ":1" 的元素
                        ratio_elements = target_frame.evaluate("""
                            () => {
                                const allElements = document.querySelectorAll('*');
                                const results = [];
                                for (let el of allElements) {
                                    const text = el.innerText || el.textContent || '';
                                    if (text.match(/\\d+\\.?\\d*\\s*[:：]\\s*1/)) {
                                        results.push({
                                            id: el.id || '',
                                            tag: el.tagName || '',
                                            text: text.substring(0, 100)
                                        });
                                    }
                                }
                                return results.slice(0, 20);
                            }
                        """)
                        print(f"  找到 {len(ratio_elements)} 个可能包含盈亏比的元素")
                        for idx, elem_info in enumerate(ratio_elements[:10]):
                            print(f"    盈亏比元素 {idx+1}: id={elem_info.get('id')}, tag={elem_info.get('tag')}, text={elem_info.get('text', '')[:50]}")
                    except Exception as e:
                        print(f"  ⚠ 查找盈亏比元素失败: {e}")
                    
                    # 分析表格结构
                    print("  分析表格结构...")
                    try:
                        tables = target_frame.locator("table")
                        table_count = tables.count()
                        print(f"  找到 {table_count} 个table标签")
                        
                        if table_count > 0:
                            for i in range(min(table_count, 3)):
                                print(f"    表格 {i+1}:")
                                try:
                                    rows = tables.nth(i).locator("tr")
                                    row_count = rows.count()
                                    print(f"      行数: {row_count}")
                                    
                                    # 显示所有行，特别是包含C5的行
                                    for j in range(min(row_count, 50)):
                                        try:
                                            row = rows.nth(j)
                                            row_text = row.inner_text(timeout=1000)
                                            
                                            # 如果这一行包含C5，详细分析
                                            if 'C5' in row_text and '做多' in row_text:
                                                print(f"      找到C5行 {j+1}:")
                                                print(f"        完整文本: {row_text[:200]}")
                                                
                                                # 获取所有单元格
                                                cells = row.locator("td, th")
                                                cell_count = cells.count()
                                                print(f"        单元格数量: {cell_count}")
                                                
                                                for k in range(min(cell_count, 15)):
                                                    try:
                                                        cell = cells.nth(k)
                                                        cell_text = cell.inner_text(timeout=1000).strip()
                                                        cell_id = cell.get_attribute("id")
                                                        print(f"          单元格 {k+1}: id={cell_id}, text={cell_text[:50]}")
                                                    except:
                                                        pass
                                                
                                                # 获取行的HTML结构
                                                try:
                                                    row_html = row.evaluate("el => el.innerHTML.substring(0, 500)")
                                                    print(f"        HTML片段: {row_html[:300]}")
                                                except:
                                                    pass
                                            
                                            # 显示前15行和包含数据的行
                                            if j < 15 or any(keyword in row_text for keyword in ['C5', 'P6', '做多', '做空', '14:', '11.18:']):
                                                cells = rows.nth(j).locator("td, th")
                                                cell_count = cells.count()
                                                cell_texts = []
                                                for k in range(min(cell_count, 15)):
                                                    try:
                                                        cell_text = cells.nth(k).inner_text(timeout=1000).strip()
                                                        cell_texts.append(cell_text)
                                                    except:
                                                        cell_texts.append("")
                                                if any(cell_texts):
                                                    print(f"        行 {j+1}: {cell_texts}")
                                        except:
                                            pass
                                except Exception as e:
                                    print(f"      ⚠ 分析表格 {i+1} 失败: {e}")
                    except Exception as e:
                        print(f"  ⚠ 分析表格结构失败: {e}")
                    
                    # 尝试提取完整的页面HTML结构（部分）
                    print("  尝试提取页面HTML结构（部分）...")
                    try:
                        html_snippet = target_frame.evaluate("""
                            () => {
                                const body = document.body;
                                if (body) {
                                    // 查找包含"现货"的容器
                                    const spotContainer = Array.from(body.querySelectorAll('*')).find(el => 
                                        el.innerText && el.innerText.includes('现货') && 
                                        el.innerText.includes('C5') && el.innerText.includes('做多')
                                    );
                                    if (spotContainer) {
                                        return {
                                            tag: spotContainer.tagName,
                                            id: spotContainer.id || '',
                                            className: spotContainer.className || '',
                                            childrenCount: spotContainer.children.length,
                                            sampleText: spotContainer.innerText.substring(0, 500)
                                        };
                                    }
                                }
                                return null;
                            }
                        """)
                        if html_snippet:
                            print(f"  找到现货容器: tag={html_snippet.get('tag')}, id={html_snippet.get('id')}, className={html_snippet.get('className')}")
                            print(f"    子元素数量: {html_snippet.get('childrenCount')}")
                            print(f"    示例文本: {html_snippet.get('sampleText', '')[:200]}")
                    except Exception as e:
                        print(f"  ⚠ 提取HTML结构失败: {e}")
                    
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
                time.sleep(10)
            
            return True
                
    except Exception as e:
        print(f"✗ 调试过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    debug_trading_opportunity_42d()

