"""
数据抓取器 - 重构版本
支持配置化的多页面数据获取，支持多浏览器环境
"""
from playwright.sync_api import Playwright, sync_playwright, FrameLocator
import json
from datetime import datetime
import sys
import time
from typing import List, Optional, Dict
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
                print(f"发现 {table_count} 个table标签")
                
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
                            print(f"  表格 {i+1}: {len(table_data)}/{row_count} 行")
                    except Exception as e:
                        print(f"  表格 {i+1} 失败: {e}")
                        continue
                
                if all_data:
                    return all_data
        except Exception as e:
            print(f"提取table标签失败: {e}")
        
        # 方法2: 尝试提取div/span等元素中的数据（卡片式布局）
        try:
            print("未找到table标签，尝试提取div/span等元素...")
            
            # 查找可能包含数据的容器
            containers = frame.locator("div[class*='card'], div[class*='data'], div[class*='content'], div[class*='table'], div[class*='grid']")
            container_count = containers.count()
            
            if container_count > 0:
                print(f"发现 {container_count} 个可能的容器")
                
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
                            print(f"  从文本内容提取: {len(table_data)} 行")
                            return all_data
        except Exception as e:
            print(f"提取div/span元素失败: {e}")
        
        # 方法3: 提取所有可见的文本内容作为备用方案
        try:
            print("尝试提取所有可见文本内容...")
            
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
                        print(f"  从备用文本提取: {len(table_data)} 行")
                        return all_data
        except Exception as e:
            print(f"提取备用文本失败: {e}")
        
        # 如果所有方法都失败
        if not all_data:
            print("未找到表格或数据")
            # 输出页面结构信息用于调试
            try:
                # 统计页面元素
                div_count = frame.locator("div").count()
                span_count = frame.locator("span").count()
                p_count = frame.locator("p").count()
                print(f"  页面元素统计: div={div_count}, span={span_count}, p={p_count}")
            except:
                pass
        
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
            print(f"发现 {frame_count} 个iframe")
            
            if frame_count == 0:
                print("  ⚠ 未找到iframe，尝试直接使用report_frame")
                # 如果没有iframe，直接使用report_frame
                return self.report_frame
            
            target_frame = None
            
            # 尝试找到可见的iframe
            for i in range(frame_count):
                try:
                    frame_locator = inner_frames.nth(i)
                    if frame_locator.is_visible(timeout=3000):
                        target_frame = self.report_frame.frame_locator("iframe").nth(i)
                        print(f"✓ 找到可见iframe: {i}")
                        
                        # 输出iframe内容诊断信息
                        try:
                            iframe_text = target_frame.locator("body").inner_text(timeout=2000)
                            text_length = len(iframe_text) if iframe_text else 0
                            print(f"  iframe内容长度: {text_length} 字符")
                            if text_length > 0:
                                # 检查是否包含关键词
                                keywords = ["做多", "做空", "盈亏比", "价差比", "预测值", "正收益", "负收益", "P4TC"]
                                found_keywords = [kw for kw in keywords if kw in iframe_text]
                                if found_keywords:
                                    print(f"  ✓ 找到关键词: {', '.join(found_keywords[:5])}")
                        except Exception as e:
                            print(f"  ⚠ 获取iframe内容时出错: {e}")
                        
                        break
                except Exception as e:
                    print(f"  iframe {i} 检查失败: {e}")
                    continue
            
            # 如果没有找到可见的iframe，使用第一个
            if not target_frame and frame_count > 0:
                try:
                    target_frame = self.report_frame.frame_locator("iframe").first
                    print("✓ 使用第一个iframe")
                except Exception as e:
                    print(f"✗ 无法访问第一个iframe: {e}")
            
            # 如果还是没有找到，尝试直接使用report_frame
            if not target_frame:
                print("  ⚠ 未找到有效iframe，使用report_frame作为目标")
                target_frame = self.report_frame
            
            return target_frame
            
        except Exception as e:
            print(f"✗ 查找iframe失败: {e}")
            import traceback
            traceback.print_exc()
            # 最后尝试直接返回report_frame
            try:
                if self.report_frame:
                    print("  ⚠ 尝试使用report_frame作为备用方案")
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
    
    def query_data(self, target_frame: FrameLocator, page_config: PageConfig) -> bool:
        """执行数据查询"""
        # 对于P4TC页面，使用原始脚本的查询逻辑
        if page_config.name == "P4TC现货应用决策":
            if self.try_click(target_frame, [
                "button:has-text('查询')",
                "button[type='submit']",
                "button:has-text('Query')",
                "[class*='query']",
                "[class*='search']"
            ]):
                print("6. 查询执行，等待响应...")
                # 增加等待时间，确保数据加载完成
                time.sleep(5)
                
                # 动态等待数据加载（检查页面是否有数据出现）
                print("  等待数据加载...")
                for i in range(10):  # 最多等待10秒
                    try:
                        # 检查是否有数据出现（检查是否有数字、日期等）
                        page_text = target_frame.locator("body").inner_text(timeout=2000)
                        # 检查是否包含P4TC相关的关键词或数据
                        if any(keyword in page_text for keyword in ["做多", "做空", "盈亏比", "价差比", "预测值", "正收益", "负收益"]):
                            print(f"  ✓ 数据已加载（等待了 {i+1} 秒）")
                            break
                        time.sleep(1)
                    except:
                        time.sleep(1)
                else:
                    print("  ⚠ 数据加载超时，继续尝试提取")
            else:
                print("  未找到查询按钮，可能页面已自动加载数据")
                time.sleep(2)  # 即使没有查询按钮，也等待一下
            return True
        else:
            # 其他页面的查询逻辑
            config = page_config.data_extraction_config
            wait_time = config.get("wait_after_query", 5)  # 默认增加到5秒
            
            if self.try_click(target_frame, page_config.query_button_selectors):
                print("查询执行，等待响应...")
                time.sleep(wait_time)
                return True
            
            print("未找到查询按钮，可能页面已自动加载数据")
            time.sleep(2)  # 即使没有查询按钮，也等待一下
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
            
            # 6. 查询数据
            if not self.query_data(target_frame, page_config):
                print("✗ 查询失败")
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
