#!/usr/bin/env python3
"""
调试P4TC页面导航问题
"""

import sys
import os
sys.path.insert(0, '../..')

from data_scraper import DataScraper
from session_manager import SessionManager
from page_config import PAGE_CONFIGS
import time

def debug_p4tc_navigation():
    """调试P4TC页面导航"""
    print("=== 调试P4TC页面导航 ===")
    
    # 创建会话管理器
    session_manager = SessionManager()
    
    try:
        # 启动会话
        print("1. 启动浏览器会话...")
        if not session_manager.start_session():
            print("✗ 启动会话失败")
            return False
        
        # 获取数据抓取器
        scraper = session_manager.scraper
        
        # 登录
        print("2. 登录...")
        if not session_manager.login_once():
            print("✗ 登录失败")
            return False
        
        print("3. 开始导航到P4TC页面...")
        
        # 获取P4TC页面配置
        p4tc_config = PAGE_CONFIGS["p4tc_spot_decision"]
        print(f"页面名称: {p4tc_config.name}")
        print(f"导航步骤数: {len(p4tc_config.navigation_path)}")
        
        # 手动导航到P4TC页面
        if not scraper.navigate_to_page(p4tc_config):
            print("✗ 导航失败")
            return False
        
        print("4. 等待页面加载...")
        time.sleep(5)
        
        # 查找目标iframe
        print("5. 查找目标iframe...")
        target_frame = scraper.find_target_frame()
        if not target_frame:
            print("✗ 未找到目标iframe")
            return False
        
        print("6. 检查页面内容...")
        # 检查页面标题和内容
        try:
            page_title = scraper.page.title()
            print(f"页面标题: {page_title}")
        except Exception as e:
            print(f"获取页面标题失败: {e}")
        
        # 检查iframe内容
        try:
            # 获取所有表格
            tables = target_frame.locator("table")
            table_count = tables.count()
            print(f"发现 {table_count} 个表格")
            
            for i in range(table_count):
                table = tables.nth(i)
                rows = table.locator("tr")
                row_count = rows.count()
                print(f"表格 {i+1}: {row_count} 行")
                
                # 显示前几行内容
                for j in range(min(5, row_count)):
                    try:
                        row = rows.nth(j)
                        cells = row.locator("td, th")
                        cell_count = cells.count()
                        row_text = []
                        for k in range(cell_count):
                            cell_text = cells.nth(k).text_content().strip()
                            if cell_text:
                                row_text.append(cell_text)
                        print(f"  行 {j+1}: {row_text}")
                    except Exception as e:
                        print(f"  行 {j+1}: 读取失败 - {e}")
                
                if row_count > 5:
                    print(f"  ... 还有 {row_count - 5} 行")
                print()
                
        except Exception as e:
            print(f"检查表格内容失败: {e}")
        
        print("7. 提取数据...")
        # 尝试提取数据
        raw_data = scraper.extract_table_data(target_frame)
        if raw_data:
            print(f"✓ 成功提取数据: {len(raw_data)} 个表格")
            
            # 显示数据内容
            total_rows = 0
            for i, table in enumerate(raw_data):
                rows = table.get('rows', [])
                total_rows += len(rows)
                print(f"表格 {i+1}: {len(rows)} 行")
                
                # 显示前几行
                for j, row in enumerate(rows[:3]):
                    non_empty_cells = [cell.strip() for cell in row if cell.strip()]
                    if non_empty_cells:
                        print(f"  行 {j+1}: {non_empty_cells}")
                
                if len(rows) > 3:
                    print(f"  ... 还有 {len(rows) - 3} 行")
                print()
            
            print(f"总行数: {total_rows}")
            
            # 检查是否包含FFA格式数据
            all_text = " ".join([" ".join(row) for table in raw_data for row in table.get('rows', [])])
            if "C5TC＋1" in all_text or "P4TC＋1" in all_text:
                print("⚠ 检测到FFA格式数据")
            else:
                print("✓ 未检测到FFA格式数据，应该是P4TC数据")
        else:
            print("✗ 未能提取到数据")
        
        print("8. 等待用户检查...")
        print("请在浏览器中检查页面是否正确导航到P4TC现货应用决策页面")
        input("按回车键继续...")
        
        return True
        
    except Exception as e:
        print(f"✗ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 关闭浏览器
        session_manager.close_session()
        print("✓ 浏览器已关闭")

if __name__ == "__main__":
    debug_p4tc_navigation()
