"""
数据抓取器 - 重构版本
支持配置化的多页面数据获取，支持多浏览器环境
"""
from playwright.sync_api import Playwright, sync_playwright, FrameLocator
import json
from datetime import datetime
import sys
import time
import os
from typing import List, Optional, Dict, Any
try:
    from .page_config import PageConfig, get_page_config, get_page_info
    from .browser_config import (
        BrowserConfig, BrowserType, get_browser_config,
        list_available_browsers
    )
except ImportError:
    from page_config import PageConfig, get_page_config, get_page_info
    from browser_config import (
        BrowserConfig, BrowserType, get_browser_config,
        list_available_browsers
    )


class DataScraper:
    """数据抓取器类
    
    支持多种浏览器：Chromium（生产环境）、Firefox（测试环境）、WebKit（可选）
    """
    
    def __init__(
        self,
        headless: bool = True,
        environment: str = None,
        browser_type: str = None
    ):
        """初始化数据抓取器
        
        Args:
            headless: 是否无头模式
            environment: 环境名称 ("production", "testing", "development")
            browser_type: 浏览器类型 ("chromium", "firefox", "webkit")
                         如果指定，会覆盖环境配置
        """
        self.browser_config = get_browser_config(
            environment=environment,
            browser_type=browser_type,
            headless=headless
        )
        self.browser = None
        self.context = None
        self.page = None
        self.report_frame = None
        
    def create_browser(self, playwright: Playwright):
        """创建浏览器实例
        
        根据配置自动选择合适的浏览器（Chromium/Firefox/WebKit）
        """
        browser_type = self.browser_config.browser_type
        
        # 根据浏览器类型选择对应的启动器
        if browser_type == BrowserType.CHROMIUM:
            launcher = playwright.chromium
        elif browser_type == BrowserType.FIREFOX:
            launcher = playwright.firefox
        elif browser_type == BrowserType.WEBKIT:
            launcher = playwright.webkit
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
        
        # 启动浏览器
        self.browser = launcher.launch(
            headless=self.browser_config.headless,
            args=self.browser_config.args,
            slow_mo=self.browser_config.slow_mo
        )
        
        # 创建浏览器上下文
        self.context = self.browser.new_context(
            viewport=self.browser_config.viewport,
            ignore_https_errors=self.browser_config.ignore_https_errors
        )
        
        print(f"✓ 浏览器已启动: {browser_type.value} (headless={self.browser_config.headless})")
        
    def try_click(self, frame: FrameLocator, selectors: List[str], operation: str = "click", 
                  text: str = None, timeout: int = 3000) -> bool:
        """尝试多个选择器直到成功
        
        Args:
            frame: iframe 定位器
            selectors: 选择器列表
            operation: 操作类型 ("click" 或 "fill")
            text: 当 operation="fill" 时作为填充内容；当 operation="click" 时被忽略
            timeout: 超时时间
        """
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            try:
                # 使用选择器定位元素
                element = frame.locator(selector).first
                element.wait_for(state="visible", timeout=timeout)
                
                # 根据操作类型执行不同动作
                if operation == "fill" and text:
                    element.fill(text)
                else:
                    element.click()
                
                time.sleep(0.3)
                return True
            except Exception:
                continue
        return False
    
    def extract_table_data(self, frame: FrameLocator, max_rows: int = 100, max_cells: int = 20) -> List[Dict]:
        """提取表格数据 - 支持多种数据格式"""
        all_data = []
        
        # 方法1: 尝试提取传统table标签
        try:
            tables = frame.locator("table")
            table_count = tables.count()
            
            if table_count > 0:
                
                for i in range(table_count):
                    try:
                        rows = tables.nth(i).locator("tr")
                        row_count = rows.count()
                        limit = min(row_count, max_rows)
                        
                        table_data = []
                        for j in range(limit):
                            try:
                                cells = rows.nth(j).locator("td, th")
                                cell_count = min(cells.count(), max_cells)
                                
                                row_data = []
                                for k in range(cell_count):
                                    try:
                                        text = cells.nth(k).inner_text(timeout=1000).strip()[:200]
                                        row_data.append(text)
                                    except:
                                        row_data.append("")
                                
                                if any(row_data):  # 只保存有内容的行
                                    table_data.append(row_data)
                            except Exception:
                                continue
                        
                        if table_data:
                            all_data.append({
                                "table_index": i,
                                "total_rows": row_count,
                                "extracted_rows": len(table_data),
                                "rows": table_data,
                                "data_type": "table"
                            })
                    except Exception as e:
                        print(f"  表格 {i+1} 失败: {e}")
                        continue
                
                if all_data:
                    return all_data
        except Exception as e:
            print(f"提取table标签失败: {e}")
        
        # 方法2: 尝试提取div/span等元素中的数据（卡片式布局）
        try:
            # 查找可能包含数据的容器
            containers = frame.locator("div[class*='card'], div[class*='data'], div[class*='content'], div[class*='table'], div[class*='grid']")
            container_count = containers.count()
            
            if container_count > 0:
                # 提取所有可见文本内容
                page_text = frame.locator("body").inner_text(timeout=5000)
                
                if page_text and len(page_text.strip()) > 50:  # 确保有足够的内容
                    # 将文本按行分割
                    lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                    
                    # 过滤掉太短或明显是UI元素的文本
                    filtered_lines = []
                    for line in lines:
                        # 跳过明显的UI文本
                        if any(skip in line for skip in ['查询', '重置', '导出', '打印', '首页', '返回']):
                            continue
                        # 保留包含数据特征的文本（数字、日期、百分比等）
                        if any(char.isdigit() for char in line) or '%' in line or '-' in line:
                            filtered_lines.append(line)
                    
                    if filtered_lines:
                        # 将文本组织成行数据
                        table_data = []
                        current_row = []
                        
                        for line in filtered_lines[:max_rows]:
                            # 尝试将行分割成多个单元格（按空格、制表符等）
                            cells = [cell.strip() for cell in line.split() if cell.strip()]
                            if cells:
                                # 限制单元格数量
                                cells = cells[:max_cells]
                                table_data.append(cells)
                        
                        if table_data:
                            all_data.append({
                                "table_index": 0,
                                "total_rows": len(table_data),
                                "extracted_rows": len(table_data),
                                "rows": table_data,
                                "data_type": "text_content"
                            })
                            return all_data
        except Exception as e:
            pass
        
        # 方法3: 提取所有可见的文本内容作为备用方案
        try:
            # 获取页面所有文本
            page_text = frame.locator("body").inner_text(timeout=5000)
            
            if page_text and len(page_text.strip()) > 50:
                # 按行分割并过滤
                lines = [line.strip() for line in page_text.split('\n') if line.strip() and len(line.strip()) > 2]
                
                if lines:
                    # 组织成表格格式
                    table_data = []
                    for line in lines[:max_rows]:
                        # 尝试分割成单元格
                        cells = [cell.strip() for cell in line.split('\t') if cell.strip()]
                        if not cells:
                            # 如果没有制表符，按多个空格分割
                            cells = [cell.strip() for cell in line.split('  ') if cell.strip()]
                        if not cells:
                            # 如果还是没有，整行作为一个单元格
                            cells = [line]
                        
                        # 限制单元格数量
                        cells = cells[:max_cells]
                        if cells:
                            table_data.append(cells)
                    
                    if table_data:
                        all_data.append({
                            "table_index": 0,
                            "total_rows": len(table_data),
                            "extracted_rows": len(table_data),
                            "rows": table_data,
                            "data_type": "fallback_text"
                        })
                        return all_data
        except Exception as e:
            pass
        
        # 如果所有方法都失败
        if not all_data:
            pass
        
        return all_data
    
    def extract_trading_opportunity_14d_data(self, frame: FrameLocator) -> List[Dict]:
        """专门提取14天后单边交易机会汇总页面的数据
        使用行的完整文本（inner_text）提取数据，类似42天页面的方法
        
        Args:
            frame: 目标iframe定位器
            
        Returns:
            提取的表格数据列表
        """
        all_data = []
        table_data = []
        
        try:
            # 方法1: 通过table标签提取，使用行的完整文本解析数据
            try:
                tables = frame.locator("table")
                table_count = tables.count()
                
                if table_count > 0:
                    import re
                    # 项目标识列表，按长度排序（长的在前，避免短标识误匹配）
                    project_ids = ['P3A', 'S1C', 'C14', 'C10', 'C5', 'P6', 'C3', 'P5', 'S5', 'S2', 'S10']
                    
                    for i in range(table_count):
                        rows = tables.nth(i).locator("tr")
                        row_count = rows.count()
                        
                        # 提取每一行的数据
                        for j in range(min(row_count, 100)):
                            try:
                                row = rows.nth(j)
                                row_text = row.inner_text(timeout=1000).strip()
                                
                                # 跳过空行和标题行
                                if not row_text or row_text in ['现货', '期货'] or len(row_text) < 2:
                                    continue
                                
                                # 检查这一行是否包含项目标识（按长度排序，先匹配长的）
                                matched_project_id = None
                                for project_id in project_ids:
                                    # 使用单词边界确保精确匹配
                                    escaped_id = re.escape(project_id)
                                    project_pattern = rf'\b{escaped_id}\b'
                                    if re.search(project_pattern, row_text):
                                        matched_project_id = project_id
                                        break
                                
                                if matched_project_id:
                                    # 从行的完整文本中提取数据
                                    row_data = []
                                    
                                    # 提取项目标识（使用匹配到的完整标识）
                                    row_data.append(matched_project_id)
                                    
                                    # 提取交易方向
                                    if '做多' in row_text:
                                        row_data.append('做多')
                                    elif '做空' in row_text:
                                        row_data.append('做空')
                                    else:
                                        row_data.append('')
                                    
                                    # 提取盈亏比（支持整数和小数）
                                    ratio_match = re.search(r'(\d+\.?\d+)\s*[:：]\s*1', row_text)
                                    if ratio_match:
                                        row_data.append(ratio_match.group(1))
                                    else:
                                        row_data.append('')
                                    
                                    if len(row_data) >= 2:
                                        table_data.append(row_data)
                            except Exception as e:
                                continue
            except Exception as e:
                pass
            
            # 方法2: 如果方法1失败，尝试从页面文本中提取
            if not table_data:
                try:
                    # 项目标识列表
                    project_ids = ['P3A', 'S1C', 'C14', 'C10', 'C5', 'P6', 'C3', 'P5', 'S5', 'S2', 'S10']
                    
                    # 获取页面所有文本
                    page_text = frame.locator("body").inner_text(timeout=5000)
                    
                    # 按行分割
                    lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                    
                    import re
                    # 查找包含项目标识的行
                    for line in lines:
                        for project_id in project_ids:
                            # 使用单词边界确保精确匹配
                            escaped_id = re.escape(project_id)
                            project_pattern = rf'\b{escaped_id}\b'
                            if re.search(project_pattern, line):
                                # 检查这一行是否包含交易方向和盈亏比
                                has_direction = '做多' in line or '做空' in line
                                has_ratio = re.search(r'\d+\.?\d+\s*[:：]\s*1', line)
                                
                                if has_direction or has_ratio:
                                    # 尝试分割这一行
                                    cells = []
                                    
                                    # 提取项目标识
                                    cells.append(project_id)
                                    
                                    # 提取交易方向
                                    if '做多' in line:
                                        cells.append('做多')
                                    elif '做空' in line:
                                        cells.append('做空')
                                    else:
                                        cells.append('')
                                    
                                    # 提取盈亏比（使用正则表达式）
                                    ratio_match = re.search(r'(\d+\.?\d+)\s*[:：]\s*1', line)
                                    if ratio_match:
                                        cells.append(ratio_match.group(1))
                                    else:
                                        cells.append('')
                                    
                                    if len(cells) >= 2:  # 至少要有项目标识和一个其他字段
                                        table_data.append(cells)
                                        break
                except Exception as e:
                    pass
            
            # 如果找到了数据，组织成表格格式
            if table_data:
                all_data.append({
                    "table_index": 0,
                    "total_rows": len(table_data),
                    "extracted_rows": len(table_data),
                    "rows": table_data,
                    "data_type": "trading_opportunity_14d"
                })
                print(f"  ✓ 成功提取 {len(table_data)} 行数据")
            else:
                # 如果专门方法失败，回退到通用方法
                return self.extract_table_data(frame, max_rows=100, max_cells=20)
            
        except Exception as e:
            print(f"  ✗ 提取14天后交易机会汇总数据失败: {e}")
            # 回退到通用方法
            return self.extract_table_data(frame, max_rows=100, max_cells=20)
        
        return all_data
    
    def extract_trading_opportunity_42d_data(self, frame: FrameLocator) -> List[Dict]:
        """专门提取42天后单边交易机会汇总页面的数据
        深入分析DOM结构，找到项目标识、交易方向和盈亏比的完整数据
        
        Args:
            frame: 目标iframe定位器
            
        Returns:
            提取的表格数据列表
        """
        all_data = []
        table_data = []
        
        try:
            # 通过table标签提取，使用行的完整文本解析数据
            try:
                tables = frame.locator("table")
                table_count = tables.count()
                
                if table_count > 0:
                    import re
                    # 项目标识列表，按长度排序（长的在前，避免短标识误匹配）
                    project_ids = ['P4TC+1', 'C5TC+1', 'C5+1', 'C5TC', 'P4TC', 'S4B', 'P3A', 'S1C', 
                                  'S15', 'S4A', 'S1B', 'P1A', 'C16', 'C10', 'S10', 'C14', 'C9', 'C8', 
                                  'C5', 'P6', 'P4', 'C3', 'P5', 'P2', 'S5', 'P0', 'S8', 'S9', 'S2', 'S3']
                    
                    for i in range(table_count):
                        rows = tables.nth(i).locator("tr")
                        row_count = rows.count()
                        
                        # 提取每一行的数据
                        for j in range(min(row_count, 100)):
                            try:
                                row = rows.nth(j)
                                row_text = row.inner_text(timeout=1000).strip()
                                
                                # 跳过空行和标题行
                                if not row_text or row_text in ['现货', '期货'] or len(row_text) < 2:
                                    continue
                                
                                # 检查这一行是否包含项目标识（按长度排序，先匹配长的）
                                matched_project_id = None
                                for project_id in project_ids:
                                    # 使用单词边界确保精确匹配，但+需要转义
                                    escaped_id = re.escape(project_id)
                                    project_pattern = rf'\b{escaped_id}\b'
                                    if re.search(project_pattern, row_text):
                                        matched_project_id = project_id
                                        break
                                
                                if matched_project_id:
                                    # 从行的完整文本中提取数据
                                    row_data = []
                                    
                                    # 提取项目标识（使用匹配到的完整标识）
                                    row_data.append(matched_project_id)
                                    
                                    # 提取交易方向
                                    if '做多' in row_text:
                                        row_data.append('做多')
                                    elif '做空' in row_text:
                                        row_data.append('做空')
                                    else:
                                        row_data.append('')
                                    
                                    # 提取盈亏比（支持整数和小数）
                                    ratio_match = re.search(r'(\d+\.?\d+)\s*[:：]\s*1', row_text)
                                    if ratio_match:
                                        row_data.append(ratio_match.group(1))
                                    else:
                                        row_data.append('')
                                    
                                    if len(row_data) >= 2:
                                        table_data.append(row_data)
                            except Exception as e:
                                continue
            except Exception as e:
                pass
            
            # 如果找到了数据，组织成表格格式
            if table_data:
                all_data.append({
                    "table_index": 0,
                    "total_rows": len(table_data),
                    "extracted_rows": len(table_data),
                    "rows": table_data,
                    "data_type": "trading_opportunity_42d"
                })
                print(f"  ✓ 成功提取 {len(table_data)} 行数据")
            else:
                # 如果专门方法失败，回退到通用方法
                return self.extract_table_data(frame, max_rows=200, max_cells=20)
            
        except Exception as e:
            print(f"  ✗ 提取42天后交易机会汇总数据失败: {e}")
            # 回退到通用方法
            return self.extract_table_data(frame, max_rows=200, max_cells=20)
        
        return all_data
    
    def extract_bilateral_trading_opportunity_data(self, frame: FrameLocator) -> List[Dict]:
        """专门提取双边交易机会汇总页面的数据
        深入分析DOM结构，找到资产对比、交易方向和盈亏比的完整数据
        
        Args:
            frame: 目标iframe定位器
            
        Returns:
            提取的表格数据列表
        """
        all_data = []
        table_data = []
        
        try:
            # 通过table标签提取，使用行的完整文本解析数据
            try:
                tables = frame.locator("table")
                table_count = tables.count()
                
                if table_count > 0:
                    import re
                    
                    for i in range(table_count):
                        rows = tables.nth(i).locator("tr")
                        row_count = rows.count()
                        
                        # 提取每一行的数据
                        for j in range(min(row_count, 100)):
                            try:
                                row = rows.nth(j)
                                row_text = row.inner_text(timeout=1000).strip()
                                
                                # 跳过空行和标题行
                                if not row_text or ('现货VS期货' in row_text or '现货VS现货' in row_text or 
                                                   '期货VS期货' in row_text) and len(row_text.strip()) <= 20:
                                    continue
                                
                                # 检查这一行是否包含"VS"关键词（表示是交易机会行）
                                if "VS" not in row_text and "vs" not in row_text.lower():
                                    continue
                                
                                # 从行的完整文本中提取数据
                                row_data = []
                                
                                # 提取资产对比（如 "P3A VS P4TC+1M"）
                                vs_pattern = r'([A-Z]\d+[A-Z]*[+\d]*M?)\s+VS\s+([A-Z]\d+[A-Z]*[+\d]*M?)'
                                vs_match = re.search(vs_pattern, row_text, re.IGNORECASE)
                                if vs_match:
                                    asset1 = vs_match.group(1)
                                    asset2 = vs_match.group(2)
                                    asset_pair = f"{asset1} VS {asset2}"
                                    row_data.append(asset_pair)
                                else:
                                    # 如果没找到，尝试从单元格中提取
                                    cells = row.locator("td, th")
                                    cell_count = cells.count()
                                    if cell_count >= 3:
                                        # 尝试从单元格中组合资产对比
                                        cell_texts = []
                                        for k in range(min(cell_count, 5)):
                                            try:
                                                text = cells.nth(k).inner_text(timeout=1000).strip()
                                                if text and text not in ['VS', 'vs']:
                                                    cell_texts.append(text)
                                            except:
                                                pass
                                        
                                        # 查找包含VS的行
                                        if 'VS' in ' '.join(cell_texts) or 'vs' in ' '.join(cell_texts).lower():
                                            row_data.extend(cell_texts)
                                    else:
                                        continue
                                
                                # 提取交易方向（从行文本中）
                                combined_direction = None
                                if '做多' in row_text or '做空' in row_text:
                                    # 尝试提取完整的交易方向描述
                                    direction_pattern = r'([A-Z]\d+[A-Z]*[+\d]*M?做[多空])\s*([A-Z]\d+[A-Z]*[+\d]*M?做[多空])'
                                    direction_match = re.search(direction_pattern, row_text)
                                    if direction_match:
                                        combined_direction = f"{direction_match.group(1)} {direction_match.group(2)}"
                                    else:
                                        # 如果没找到完整格式，尝试提取所有做多/做空相关的文本
                                        direction_parts = re.findall(r'[A-Z]\d+[A-Z]*[+\d]*M?做[多空]', row_text)
                                        if direction_parts:
                                            combined_direction = " ".join(direction_parts)
                                
                                if combined_direction:
                                    row_data.append(combined_direction)
                                else:
                                    row_data.append('')
                                
                                # 提取盈亏比（支持整数和小数）
                                ratio_match = re.search(r'(\d+\.?\d+)\s*[:：]\s*1', row_text)
                                if ratio_match:
                                    row_data.append(ratio_match.group(1))
                                else:
                                    row_data.append('')
                                
                                if len(row_data) >= 2:
                                    table_data.append(row_data)
                            except Exception as e:
                                continue
            except Exception as e:
                pass
            
            # 如果找到了数据，组织成表格格式
            if table_data:
                all_data.append({
                    "table_index": 0,
                    "total_rows": len(table_data),
                    "extracted_rows": len(table_data),
                    "rows": table_data,
                    "data_type": "bilateral_trading_opportunity"
                })
                print(f"  ✓ 成功提取 {len(table_data)} 行数据")
            else:
                # 如果专门方法失败，回退到通用方法
                return self.extract_table_data(frame, max_rows=200, max_cells=20)
            
        except Exception as e:
            print(f"  ✗ 提取双边交易机会汇总数据失败: {e}")
            # 回退到通用方法
            return self.extract_table_data(frame, max_rows=200, max_cells=20)
        
        return all_data
    
    def navigate_to_page(self, page_config: PageConfig) -> bool:
        """根据配置导航到指定页面"""
        print(f"4. 导航到目标页面: {page_config.name}")
        
        # 对于P4TC页面，使用精确的文本匹配导航，确保点击"单边策略研究"而不是"基差研究"
        if page_config.name == "P4TC现货应用决策":
            print("  使用精确导航路径: AquaBridge -> 单边策略研究 -> 现货策略 -> P4TC现货 -> 现货应用决策")
            
            # 步骤1: 展开主菜单（AquaBridge）
            print("  步骤1: 展开主菜单...")
            if not self.try_click(self.report_frame, [
                ".bi-f-c > .bi-icon-change-button > .x-icon",
                "*:has-text('AquaBridge') .bi-icon-change-button",
                ".bi-icon-change-button:first"
            ]):
                print("  ⚠ 主菜单可能已展开")
            time.sleep(0.5)
            
            # 步骤2: 点击"单边策略研究"（关键步骤，必须精确匹配，排除基差研究）
            print("  步骤2: 点击'单边策略研究'（排除基差研究）...")
            success = False
            # 首先尝试精确的文本匹配
            try:
                # 查找所有包含"单边策略研究"的元素
                single_strategy_items = self.report_frame.locator("text='单边策略研究'").all()
                for item in single_strategy_items:
                    try:
                        # 验证元素文本不包含"基差研究"
                        item_text = item.inner_text(timeout=500)
                        # 确保不包含"基差研究"
                        if "基差研究" not in item_text:
                            item.click()
                            success = True
                            print("  ✓ 成功点击'单边策略研究'")
                            break
                    except:
                        continue
            except:
                pass
            
            # 如果精确匹配失败，尝试其他选择器
            if not success:
                success = self.try_click(self.report_frame, [
                    "*:has-text('单边策略研究'):not(:has-text('基差研究'))",
                    ".bi-list-item:has-text('单边策略研究'):not(:has-text('基差研究'))",
                    ".bi-button-tree:has-text('单边策略研究'):not(:has-text('基差研究'))"
                ])
            
            if not success:
                print("  ✗ 未找到'单边策略研究'菜单项")
                # 输出当前可见的菜单项用于调试
                try:
                    print("  调试: 查找所有菜单项...")
                    menu_items = self.report_frame.locator(".bi-list-item, .bi-button-tree").all()
                    print(f"  当前可见菜单项数量: {len(menu_items)}")
                    for i, item in enumerate(menu_items[:15]):  # 显示前15个
                        try:
                            text = item.inner_text(timeout=1000)
                            if text and len(text.strip()) > 0:
                                print(f"    菜单项 {i+1}: {text[:80]}")
                        except:
                            pass
                except Exception as e:
                    print(f"  调试信息获取失败: {e}")
                return False
            
            # 验证是否点击了正确的菜单项
            time.sleep(1)
            try:
                # 检查是否出现了"价格信号"或"现货策略"等子菜单（单边策略研究的子菜单）
                has_price_signal = self.report_frame.locator("text='价格信号'").count() > 0
                has_spot_strategy = self.report_frame.locator("text='现货策略'").count() > 0
                has_basis_research = self.report_frame.locator("text='基差研究'").count() > 0
                
                if has_price_signal or has_spot_strategy:
                    print(f"  ✓ 验证通过: 找到子菜单（价格信号={has_price_signal}, 现货策略={has_spot_strategy}）")
                elif has_basis_research:
                    print("  ✗ 验证失败: 点击了'基差研究'而不是'单边策略研究'")
                    return False
                else:
                    print("  ⚠ 警告: 未找到预期的子菜单，但继续尝试")
            except:
                pass
            
            # 步骤3: 展开"现货策略"菜单
            print("  步骤3: 展开'现货策略'菜单...")
            if not self.try_click(self.report_frame, [
                "text='现货策略'",
                "*:has-text('现货策略') .bi-icon-change-button",
                ".bi-icon-change-button:has-text('现货策略')"
            ]):
                print("  ⚠ '现货策略'菜单可能已展开或不存在")
            time.sleep(0.5)
            
            # 步骤4: 展开"P4TC现货"菜单
            print("  步骤4: 展开'P4TC现货'菜单...")
            if not self.try_click(self.report_frame, [
                "text='P4TC现货'",
                "*:has-text('P4TC现货') .bi-icon-change-button",
                ".bi-icon-change-button:has-text('P4TC现货')"
            ]):
                print("  ⚠ 'P4TC现货'菜单可能已展开或不存在")
            time.sleep(0.5)
            
            # 步骤5: 点击"现货应用决策"
            print("  步骤5: 点击'现货应用决策'...")
            if not self.try_click(self.report_frame, [
                "text='现货应用决策'",
                "*:has-text('现货应用决策')",
                ".bi-list-item:has-text('现货应用决策')"
            ]):
                print("  ✗ 未找到'现货应用决策'菜单项")
                return False
            
            print("✓ 导航完成")
            time.sleep(2)  # 增加等待时间，让页面完全加载
            return True
        else:
            # 对于其他页面，使用配置化的导航
            for step in page_config.navigation_path:
                print(f"  {step.description}")
                # 直接使用选择器（选择器中已包含 text='...' 格式）
                success = self.try_click(
                    self.report_frame, 
                    step.selectors
                )
                
                if not success:
                    print(f"  ✗ 导航步骤失败: {step.description}")
                    return False
                
                time.sleep(step.wait_time)
            
            print("✓ 导航完成")
            return True
    
    def find_target_frame(self) -> Optional[FrameLocator]:
        """找到目标iframe"""
        print("5. 等待数据加载...")
        time.sleep(3)  # 等待页面稳定
        
        try:
            # 重新获取report_frame，确保它是最新的
            if self.page:
                try:
                    # 确保页面仍然有效
                    if not self.page.is_closed():
                        # 重新获取report_frame
                        self.report_frame = self.page.frame_locator("#reportFrame")
                        print("  ✓ 重新获取report_frame")
                    else:
                        print("  ✗ 页面已关闭")
                        return None
                except Exception as e:
                    print(f"  ⚠ 检查页面状态时出错: {e}，继续尝试...")
            
            # 检查report_frame是否有效
            if not self.report_frame:
                print("✗ report_frame无效")
                return None
            
            # 尝试访问report_frame来验证它是否有效
            try:
                # 尝试查找一个简单的元素来验证frame是否可访问
                test_element = self.report_frame.locator("body").first
                test_element.wait_for(state="attached", timeout=3000)
            except Exception as e:
                print(f"✗ report_frame不可访问: {e}")
                return None
            
            inner_frames = self.report_frame.locator("iframe")
            frame_count = inner_frames.count()
            
            if frame_count == 0:
                # 如果没有iframe，直接使用report_frame
                return self.report_frame
            
            target_frame = None
            
            # 尝试找到可见的iframe
            for i in range(frame_count):
                try:
                    frame_locator = inner_frames.nth(i)
                    if frame_locator.is_visible(timeout=3000):
                        target_frame = self.report_frame.frame_locator("iframe").nth(i)
                        break
                except Exception as e:
                    continue
            
            # 如果没有找到可见的iframe，使用第一个
            if not target_frame and frame_count > 0:
                try:
                    target_frame = self.report_frame.frame_locator("iframe").first
                except Exception as e:
                    pass
            
            # 如果还是没有找到，尝试直接使用report_frame
            if not target_frame:
                target_frame = self.report_frame
            
            return target_frame
            
        except Exception as e:
            print(f"✗ 查找iframe失败: {e}")
            import traceback
            traceback.print_exc()
            # 最后尝试直接返回report_frame
            try:
                if self.report_frame:
                    return self.report_frame
            except:
                pass
            return None
    
    def extract_swap_date_from_page(self, target_frame: FrameLocator) -> Optional[str]:
        """从页面顶部提取掉期日期"""
        try:
            # 尝试多种选择器来找到掉期日期
            selectors = [
                "text='掉期日期'",
                "*:has-text('掉期日期')",
                "[class*='date']",
                "[class*='swap']",
                "div:has-text('2025-')",
                "*:has-text('2025-10-15')",
                "*:has-text('2025-10-14')"
            ]
            
            for selector in selectors:
                try:
                    element = target_frame.locator(selector).first
                    if element.is_visible(timeout=2000):
                        text = element.inner_text(timeout=1000)
                        # 使用正则表达式提取日期
                        import re
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                        if date_match:
                            return date_match.group(1)
                except Exception:
                    continue
            
            # 如果上述方法都失败，尝试在整个页面中搜索日期
            try:
                page_text = target_frame.locator("body").inner_text(timeout=3000)
                import re
                # 查找所有日期格式
                dates = re.findall(r'(\d{4}-\d{2}-\d{2})', page_text)
                if dates:
                    # 返回最后一个找到的日期（通常是最新的）
                    return dates[-1]
            except Exception:
                pass
                
            return None
        except Exception as e:
            print(f"提取掉期日期失败: {e}")
            return None
    
    def screenshot_element(self, target_frame: FrameLocator, screenshot_config: dict, page_key: str, report_frame: FrameLocator = None) -> Optional[str]:
        """截图整个页面 - 简化流程，直接截图完整页面
        
        Args:
            target_frame: 目标iframe定位器
            screenshot_config: 截图配置字典
            page_key: 页面键，用于生成文件名
            report_frame: reportFrame定位器，用于点击pin按钮
            
        Returns:
            截图文件路径，如果失败则返回None
        """
        try:
            print("开始截图...")
            
            # 确保输出目录存在
            output_dir = screenshot_config.get("output_dir", "output/screenshots")
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{page_key}_screenshot_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)
            
            # 等待页面加载
            print("  等待页面加载...")
            time.sleep(3)
            
            # 处理弹窗（如果有）
            try:
                print("  检查并关闭弹窗...")
                if self.page:
                    dialog_selectors = [
                        "button:has-text('OK')",
                        "button:has-text('确定')",
                        "button:has-text('关闭')",
                        ".modal button",
                        "[class*='dialog'] button"
                    ]
                    
                    for selector in dialog_selectors:
                        try:
                            dialog_button = self.page.locator(selector).first
                            if dialog_button.is_visible(timeout=2000):
                                dialog_button.click()
                                print("  ✓ 已关闭弹窗")
                                time.sleep(1)
                                break
                        except Exception:
                            continue
            except Exception:
                pass
            
            # 点击pin按钮（图钉按钮）确保页面显示正确
            try:
                print("  点击pin按钮确保页面显示正确...")
                # 使用传入的report_frame或self.report_frame
                frame_to_use = report_frame if report_frame else self.report_frame
                
                if frame_to_use:
                    # 尝试多种选择器找到pin按钮（在左侧导航栏）
                    pin_xpath = "//*[@id='wrapper']/div[1]/div[2]/div[2]/div/div[2]/div[2]/div[1]/div[2]/i"
                    pin_selectors = [
                        f"xpath={pin_xpath}",
                        "//i[contains(@class, 'pin')]",
                        "//i[contains(@class, 'Pin')]",
                        "i[class*='pin']",
                        "i[class*='Pin']",
                        "[class*='pin']",
                        "[class*='Pin']",
                        "button[class*='pin']",
                        "button[class*='Pin']",
                        "[data-icon='pin']",
                        "svg[class*='pin']"
                    ]
                    
                    pin_clicked = False
                    for selector in pin_selectors:
                        try:
                            pin_button = frame_to_use.locator(selector).first
                            if pin_button.is_visible(timeout=3000):
                                pin_button.click()
                                print("  ✓ 已点击pin按钮")
                                time.sleep(2)  # 等待页面布局调整
                                pin_clicked = True
                                break
                        except Exception:
                            continue
                    
                    if not pin_clicked:
                        print("  ⚠ 未找到pin按钮，继续尝试")
                elif self.page:
                    # 如果report_frame不可用，尝试在主页面查找
                    try:
                        pin_xpath = "//*[@id='wrapper']/div[1]/div[2]/div[2]/div/div[2]/div[2]/div[1]/div[2]/i"
                        pin_button = self.page.locator(f"xpath={pin_xpath}").first
                        if pin_button.is_visible(timeout=3000):
                            pin_button.click()
                            print("  ✓ 已点击pin按钮（主页面）")
                            time.sleep(2)
                    except Exception:
                        pass
            except Exception as e:
                pass
            
            # 调整浏览器视口，使用更大的高度确保完整截图
            if self.page:
                try:
                    # 设置更大的视口高度，确保能容纳所有内容
                    self.page.set_viewport_size({"width": 1920, "height": 5000})
                    time.sleep(0.5)
                except Exception as e:
                    pass
            
            # 再等待一下确保内容渲染
            time.sleep(2)
            
            # 操作现货和期货模块的滚动容器，确保数据完整加载
            try:
                # 现货模块滚动容器
                spot_scroll_xpath = "//*[@id='wrapper']/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/div/div[2]/div[2]/div/div[1]/div[2]/div/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/div"
                # 期货模块滚动容器
                futures_scroll_xpath = "//*[@id='wrapper']/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/div/div[3]/div[2]/div/div[1]/div[2]/div/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/div"
                
                if self.page:
                    # 操作现货模块滚动容器
                    try:
                        spot_scroll_element = self.page.locator(f"xpath={spot_scroll_xpath}").first
                        if spot_scroll_element.is_visible(timeout=5000):
                            # 多次滚动到底部，确保所有数据加载
                            last_scroll_top = -1
                            for i in range(20):  # 最多滚动20次
                                try:
                                    # 滚动到底部
                                    current_scroll_top = spot_scroll_element.evaluate("""
                                        (el) => {
                                            el.scrollTop = el.scrollHeight;
                                            return el.scrollTop;
                                        }
                                    """)
                                    time.sleep(0.5)  # 等待内容加载
                                    
                                    # 检查是否已经滚动到底部
                                    if current_scroll_top == last_scroll_top and current_scroll_top > 0:
                                        break
                                    
                                    last_scroll_top = current_scroll_top
                                except Exception as e:
                                    break
                    except Exception as e:
                        pass
                    
                    # 操作期货模块滚动容器
                    try:
                        futures_scroll_element = self.page.locator(f"xpath={futures_scroll_xpath}").first
                        if futures_scroll_element.is_visible(timeout=5000):
                            # 多次滚动到底部，确保所有数据加载
                            last_scroll_top = -1
                            for i in range(20):  # 最多滚动20次
                                try:
                                    # 滚动到底部
                                    current_scroll_top = futures_scroll_element.evaluate("""
                                        (el) => {
                                            el.scrollTop = el.scrollHeight;
                                            return el.scrollTop;
                                        }
                                    """)
                                    time.sleep(0.5)  # 等待内容加载
                                    
                                    # 检查是否已经滚动到底部
                                    if current_scroll_top == last_scroll_top and current_scroll_top > 0:
                                        break
                                    
                                    last_scroll_top = current_scroll_top
                                except Exception as e:
                                    break
                    except Exception as e:
                        pass
                    
                    # 等待内容加载
                    time.sleep(2)
            except Exception as e:
                pass
            
            # 滚动页面确保所有内容加载（多次滚动触发懒加载）
            try:
                # 方法1: 在target_frame（iframe）内多次滚动（最重要）
                try:
                    body_locator = target_frame.locator("body")
                    
                    # 获取初始高度
                    try:
                        initial_height = body_locator.evaluate("""
                            () => Math.max(
                                document.body.scrollHeight,
                                document.documentElement.scrollHeight,
                                document.body.offsetHeight,
                                document.documentElement.offsetHeight
                            )
                        """)
                        print(f"  初始iframe内容高度: {initial_height}px")
                    except:
                        initial_height = 0
                    
                    # 多次滚动到底部，触发懒加载
                    max_scrolls = 5
                    last_height = initial_height
                    for scroll_attempt in range(max_scrolls):
                        try:
                            # 滚动到底部
                            body_locator.evaluate("""
                                () => {
                                    const scrollHeight = Math.max(
                                        document.body.scrollHeight,
                                        document.documentElement.scrollHeight,
                                        document.body.offsetHeight,
                                        document.documentElement.offsetHeight
                                    );
                                    window.scrollTo({
                                        top: scrollHeight,
                                        behavior: 'smooth'
                                    });
                                }
                            """)
                            time.sleep(3)  # 等待内容加载
                            
                            # 检查高度是否增加
                            try:
                                current_height = body_locator.evaluate("""
                                    () => Math.max(
                                        document.body.scrollHeight,
                                        document.documentElement.scrollHeight,
                                        document.body.offsetHeight,
                                        document.documentElement.offsetHeight
                                    )
                                """)
                                if current_height > last_height:
                                    last_height = current_height
                                else:
                                    time.sleep(2)  # 再等待一下确保渲染完成
                                    break
                            except:
                                pass
                        except Exception as e:
                            pass
                    
                    # 滚动回顶部
                    body_locator.evaluate("window.scrollTo(0, 0)")
                    time.sleep(1)
                except Exception as e:
                    pass
                    
                # 方法2: 通过page.frames找到frame对象并滚动
                if self.page:
                    try:
                        all_frames = self.page.frames
                        if len(all_frames) >= 2:
                            content_frame = all_frames[1]
                            
                            # 多次滚动
                            for scroll_attempt in range(3):
                                try:
                                    content_frame.evaluate("""
                                        () => {
                                            const scrollHeight = Math.max(
                                                document.body.scrollHeight,
                                                document.documentElement.scrollHeight
                                            );
                                            window.scrollTo(0, scrollHeight);
                                        }
                                    """)
                                    time.sleep(2)
                                except:
                                    pass
                            
                            # 滚动回顶部
                            content_frame.evaluate("window.scrollTo(0, 0)")
                            time.sleep(1)
                            print("  ✓ 通过frame对象滚动完成")
                    except Exception as e:
                        print(f"  ⚠ frame对象滚动失败: {e}")
                
                # 方法3: 在主页面滚动
                if self.page:
                    try:
                        page_height = self.page.evaluate("""
                            () => Math.max(
                                document.body.scrollHeight,
                                document.documentElement.scrollHeight
                            )
                        """)
                        print(f"  主页面高度: {page_height}px")
                        
                        # 滚动到底部
                        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(2)
                        
                        # 滚动回顶部
                        self.page.evaluate("window.scrollTo(0, 0)")
                        time.sleep(1)
                    except Exception as e:
                        print(f"  ⚠ 主页面滚动失败: {e}")
                
                print("  ✓ 页面滚动完成")
            except Exception as e:
                print(f"  ⚠ 页面滚动失败: {e}")
            
            # 滚动后再次点击pin按钮，确保布局正确
            try:
                frame_to_use = report_frame if report_frame else self.report_frame
                if frame_to_use:
                    pin_xpath = "//*[@id='wrapper']/div[1]/div[2]/div[2]/div/div[2]/div[2]/div[1]/div[2]/i"
                    try:
                        pin_button = frame_to_use.locator(f"xpath={pin_xpath}").first
                        if pin_button.is_visible(timeout=2000):
                            pin_button.click()
                            time.sleep(1)
                            print("  ✓ 滚动后再次点击pin按钮")
                    except Exception:
                        pass
            except Exception:
                pass
            
            # 方法1: 分别截图现货和期货模块，然后截图整个页面
            if self.page:
                try:
                    # 先分别截图现货和期货模块
                    spot_scroll_xpath = "//*[@id='wrapper']/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/div/div[2]/div[2]/div/div[1]/div[2]/div/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/div"
                    futures_scroll_xpath = "//*[@id='wrapper']/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/div/div[3]/div[2]/div/div[1]/div[2]/div/div/div/div/div[2]/div/div[2]/div/div/div[2]/div/div"
                    
                    # 尝试分别截图现货和期货模块
                    spot_screenshot_path = None
                    futures_screenshot_path = None
                    
                    try:
                        # 现货模块截图
                        spot_container_xpath = "//*[@id='wrapper']/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/div/div[2]"
                        spot_element = self.page.locator(f"xpath={spot_container_xpath}").first
                        if spot_element.is_visible(timeout=3000):
                            spot_filepath = filepath.replace(".png", "_spot.png")
                            spot_element.screenshot(path=spot_filepath)
                            if os.path.exists(spot_filepath) and os.path.getsize(spot_filepath) > 0:
                                spot_screenshot_path = spot_filepath
                    except Exception as e:
                        pass
                    
                    try:
                        # 期货模块截图
                        futures_container_xpath = "//*[@id='wrapper']/div/div/div[2]/div/div[2]/div/div/div[1]/div[2]/div/div[3]"
                        futures_element = self.page.locator(f"xpath={futures_container_xpath}").first
                        if futures_element.is_visible(timeout=3000):
                            futures_filepath = filepath.replace(".png", "_futures.png")
                            futures_element.screenshot(path=futures_filepath)
                            if os.path.exists(futures_filepath) and os.path.getsize(futures_filepath) > 0:
                                futures_screenshot_path = futures_filepath
                    except Exception as e:
                        pass
                    
                    # 然后截图整个页面（主要截图）
                    
                    # 使用full_page=True确保截图完整，会自动捕获所有滚动区域
                    # 等待一下确保页面稳定
                    time.sleep(1)
                    self.page.screenshot(path=filepath, full_page=True)
                    
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                        file_size_kb = os.path.getsize(filepath) / 1024
                        
                        # 验证截图尺寸（通过PIL检查）
                        try:
                            from PIL import Image
                            img = Image.open(filepath)
                            img_width, img_height = img.size
                            print(f"  截图尺寸: {img_width}x{img_height}px")
                            
                            # 验证截图是否完整
                            if final_page_height > 0:
                                expected_height = final_page_height
                                if img_height < expected_height * 0.9:  # 允许10%的误差
                                    print(f"  ⚠ 警告: 截图高度({img_height}px)可能小于页面高度({final_page_height}px)")
                                else:
                                    print(f"  ✓ 截图高度验证通过: {img_height}px >= {expected_height}px")
                            
                            img.close()
                        except ImportError:
                            print("  ⚠ PIL未安装，跳过截图尺寸验证")
                        except Exception as e:
                            print(f"  ⚠ 验证截图尺寸失败: {e}")
                        
                        print(f"✓ 截图成功: {filepath} (大小: {file_size_kb:.2f} KB)")
                        if spot_screenshot_path:
                            print(f"  现货模块截图: {spot_screenshot_path}")
                        if futures_screenshot_path:
                            print(f"  期货模块截图: {futures_screenshot_path}")
                        return filepath
                    else:
                        print("  ✗ 截图文件为空或不存在")
                except Exception as e:
                    print(f"  ⚠ 页面截图失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 方法2: 如果页面截图失败，尝试截图iframe元素
            if self.page:
                try:
                    print("  尝试截图iframe元素...")
                    iframe_locator = self.page.locator("#reportFrame iframe")
                    iframe_count = iframe_locator.count()
                    
                    if iframe_count > 0:
                        # 使用最后一个iframe（通常是内容iframe）
                        iframe_element = iframe_locator.nth(iframe_count - 1)
                        iframe_element.screenshot(path=filepath)
                        
                        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                            file_size_kb = os.path.getsize(filepath) / 1024
                            print(f"✓ 截图成功 (iframe): {filepath} (大小: {file_size_kb:.2f} KB)")
                            return filepath
                except Exception as e:
                    print(f"  ⚠ iframe截图失败: {e}")
            
            print("✗ 截图失败")
            return None
                
        except Exception as e:
            print(f"✗ 截图失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def extract_metadata_from_page(self, target_frame: FrameLocator) -> Dict[str, Any]:
        """从页面提取元数据（日期、标题等）
        
        Args:
            target_frame: 目标iframe定位器
            
        Returns:
            包含元数据的字典
        """
        metadata = {}
        
        try:
            # 提取日期
            date = self.extract_swap_date_from_page(target_frame)
            if date:
                metadata["swap_date"] = date
            else:
                # 如果没有找到掉期日期，使用当前日期
                current_date = datetime.now().strftime("%Y-%m-%d")
                metadata["swap_date"] = current_date
                print(f"⚠ 未找到掉期日期，使用当前日期: {current_date}")
            
            # 尝试提取页面标题
            try:
                # 查找包含"42天后"或"交易机会汇总"的文本
                title_selectors = [
                    "text='42天后'",
                    "*:has-text('42天后')",
                    "*:has-text('交易机会汇总')",
                    "h1, h2, h3",
                    "[class*='title']",
                    "[class*='header']"
                ]
                
                for selector in title_selectors:
                    try:
                        element = target_frame.locator(selector).first
                        if element.is_visible(timeout=2000):
                            text = element.inner_text(timeout=1000)
                            if text and ("42天后" in text or "交易机会汇总" in text):
                                metadata["page_title"] = text.strip()
                                print(f"✓ 提取到标题: {text.strip()}")
                                break
                    except Exception:
                        continue
                
                # 如果没有找到标题，设置默认值
                if "page_title" not in metadata:
                    metadata["page_title"] = "42天后单边交易机会汇总"
                    
            except Exception as e:
                print(f"⚠ 提取标题失败: {e}")
                metadata["page_title"] = "42天后单边交易机会汇总"
            
        except Exception as e:
            print(f"⚠ 提取元数据时出错: {e}")
        
        return metadata
    
    def wait_for_data_load(self, target_frame: FrameLocator, page_config: PageConfig) -> bool:
        """等待页面数据加载（优化版本：不需要点击查询按钮）"""
        print("6. 等待页面数据加载...")
        
        # 获取配置的等待时间
        config = page_config.data_extraction_config
        wait_time = config.get("wait_after_query", 5)  # 使用配置的等待时间
        
        # 对于P4TC页面，使用更智能的等待逻辑
        if page_config.name == "P4TC现货应用决策":
            print("  检测到P4TC页面，智能等待数据加载...")
            # 动态等待数据加载（检查页面是否有数据出现）
            for i in range(10):  # 最多等待10秒
                try:
                    # 检查是否有数据出现（检查是否有数字、日期等）
                    page_text = target_frame.locator("body").inner_text(timeout=2000)
                    # 检查是否包含P4TC相关的关键词或数据
                    if any(keyword in page_text for keyword in ["做多", "做空", "盈亏比", "价差比", "预测值", "正收益", "负收益"]):
                        print(f"  ✓ 数据已加载（等待了 {i+1} 秒）")
                        return True
                    time.sleep(1)
                except:
                    time.sleep(1)
            else:
                print("  ⚠ 数据加载超时，继续尝试提取")
                # 即使超时也等待一下，确保页面稳定
                time.sleep(2)
        else:
            # 其他页面：等待固定时间，然后检查数据是否出现
            print(f"  等待 {wait_time} 秒让页面数据加载...")
            time.sleep(wait_time)
            
            # 尝试检查数据是否已加载
            try:
                page_text = target_frame.locator("body").inner_text(timeout=2000)
                if page_text and len(page_text.strip()) > 50:
                    print("  ✓ 页面内容已加载")
                    return True
            except:
                print("  ⚠ 无法验证数据加载状态，继续尝试提取")
        
        return True
    
    def scrape_page_data(self, page_key: str) -> Optional[List[Dict]]:
        """抓取指定页面的数据"""
        page_config = get_page_config(page_key)
        if not page_config:
            print(f"✗ 未找到页面配置: {page_key}")
            return None
        
        try:
            print(f"\n开始抓取: {page_config.name}")
            
            # 1. 访问网站
            print("1. 访问网站...")
            self.page.goto("https://jinzhengny.com/", wait_until="domcontentloaded")
            self.page.locator("#reportFrame").wait_for(state="visible")
            
            self.report_frame = self.page.frame_locator("#reportFrame")
            
            # 2. 登录
            print("2. 登录...")
            self.try_click(self.report_frame, [
                "input[placeholder*='Username']",
                "input[placeholder*='用户名']",
                "input[type='text']"
            ], "fill", "15152627161")
            
            self.try_click(self.report_frame, "input[type='password']", "fill", "lsls12")
            
            self.try_click(self.report_frame, [
                ".bi-h-o > .bi-basic-button",
                "button[type='submit']",
                "button"
            ])
            
            # 3. 等待登录完成
            print("3. 等待登录...")
            # 等待导航图标出现，确认登录成功
            self.report_frame.locator(".bi-f-c > .bi-icon-change-button").first.wait_for(
                state="visible", timeout=10000
            )
            
            # 4. 导航到目标页面
            if not self.navigate_to_page(page_config):
                return None
            
            # 5. 找到目标iframe
            target_frame = self.find_target_frame()
            if not target_frame:
                print("✗ 未找到目标iframe")
                return None
            
            # 6. 等待数据加载（优化：不需要点击查询按钮）
            if not self.wait_for_data_load(target_frame, page_config):
                print("✗ 等待数据加载失败")
                return None
            
            # 7. 提取数据
            print("7. 提取数据...")
            config = page_config.data_extraction_config
            table_data = self.extract_table_data(
                target_frame, 
                config.get("max_rows", 100),
                config.get("max_cells", 20)
            )
            
            # 8. 提取掉期日期（从页面顶部）
            print("8. 提取掉期日期...")
            swap_date = self.extract_swap_date_from_page(target_frame)
            if swap_date:
                print(f"✓ 掉期日期: {swap_date}")
                # 将掉期日期添加到第一个表格的元数据中
                if table_data and len(table_data) > 0:
                    table_data[0]["swap_date"] = swap_date
            else:
                # 如果没有找到掉期日期，使用当前日期
                from datetime import datetime
                current_date = datetime.now().strftime("%Y-%m-%d")
                print(f"⚠ 未找到掉期日期，使用当前日期: {current_date}")
                if table_data and len(table_data) > 0:
                    table_data[0]["swap_date"] = current_date
            
            print(f"✓ 数据抓取完成: {len(table_data)} 个表格")
            return table_data
            
        except Exception as e:
            print(f"✗ 抓取失败: {e}")
            return None
    
    def save_data(self, data: List[Dict], page_key: str, browser_name: str = "chromium") -> bool:
        """保存提取的数据到 output 文件夹"""
        if not data:
            print("✗ 无数据可保存")
            return False
        
        page_config = get_page_config(page_key)
        page_name = page_config.name if page_config else page_key
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_rows = sum(t.get("extracted_rows", 0) for t in data)
        
        # 确保 output 文件夹存在
        import os
        os.makedirs("output", exist_ok=True)
        
        # 保存JSON文件到 output 文件夹
        json_filename = f"output/{page_key}_data_{timestamp}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump({
                "timestamp": timestamp,
                "browser": browser_name,
                "page_key": page_key,
                "page_name": page_name,
                "statistics": {
                    "total_tables": len(data),
                    "total_rows": total_rows
                },
                "tables": data
            }, f, ensure_ascii=False, indent=2)
        
        # 保存TXT文件到 output 文件夹
        txt_filename = f"output/{page_key}_data_{timestamp}.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            for table in data:
                rows = table.get("rows", [])
                for row in rows:
                    f.write("\t".join(row) + "\n")
                f.write("\n")  # 表格之间空行
        
        print(f"\n✓ 数据已保存到 output 文件夹:")
        print(f"  - JSON: {json_filename}")
        print(f"  - TXT:  {txt_filename}")
        print(f"✓ {len(data)} 个表格, {total_rows} 行数据")
        return True
    
    def cleanup(self):
        """清理资源"""
        for obj in [self.page, self.context, self.browser]:
            if obj:
                try:
                    obj.close()
                except Exception:
                    pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def main():
    """主函数
    
    命令行参数:
        python data_scraper.py [page_key] [--browser TYPE] [--env ENV] [--headless/--no-headless]
    
    示例:
        # 使用默认配置（生产环境 Chromium）
        python data_scraper.py
        
        # 指定页面
        python data_scraper.py ffa_price_signals
        
        # 使用 Firefox 测试
        python data_scraper.py ffa_price_signals --browser firefox --no-headless
        
        # 使用测试环境配置
        python data_scraper.py --env testing
        
        # 显示浏览器窗口
        python data_scraper.py --no-headless
    """
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="AquaBridge 数据抓取器 - 支持多浏览器环境",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "page_key",
        nargs="?",
        default="p4tc_spot_decision",
        help="页面键 (默认: p4tc_spot_decision)"
    )
    
    parser.add_argument(
        "--browser", "-b",
        choices=list_available_browsers(),
        help="浏览器类型 (chromium/firefox/webkit)"
    )
    
    parser.add_argument(
        "--env", "-e",
        choices=["production", "testing", "development"],
        help="环境类型 (production: Chromium, testing: Firefox)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        help="无头模式"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="显示浏览器窗口"
    )
    
    args = parser.parse_args()
    
    # 处理 headless 参数
    headless = True  # 默认无头模式
    if args.no_headless:
        headless = False
    elif args.headless:
        headless = True
    
    # 显示标题和配置
    print("=== AquaBridge 数据抓取器 ===")
    
    # 显示浏览器配置信息
    if args.env:
        print(f"环境: {args.env}")
    if args.browser:
        print(f"浏览器: {args.browser}")
    print(f"显示模式: {'窗口' if not headless else '无头'}")
    print()
    
    print("可用页面:")
    page_info = get_page_info()
    for key, info in page_info.items():
        print(f"  {key}: {info['name']} - {info['description']}")
    
    page_key = args.page_key
    
    if page_key not in page_info:
        print(f"\n✗ 无效的页面键: {page_key}")
        print(f"可用页面: {list(page_info.keys())}")
        return
    
    try:
        with sync_playwright() as playwright:
            # 创建抓取器，使用新的浏览器配置系统
            scraper = DataScraper(
                headless=headless,
                environment=args.env,
                browser_type=args.browser
            )
            scraper.create_browser(playwright)
            scraper.page = scraper.context.new_page()
            scraper.page.set_default_timeout(12000)
            scraper.page.set_default_navigation_timeout(15000)
            
            # 抓取数据
            data = scraper.scrape_page_data(page_key)
            
            if data:
                # 保存数据
                scraper.save_data(data, page_key)
                print(f"\n✓ 执行完成: {page_info[page_key]['name']}")
            else:
                print(f"\n✗ 数据抓取失败")
            
            # 等待用户
            try:
                input("\n按回车键关闭...")
            except EOFError:
                time.sleep(2)
                
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
