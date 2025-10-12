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
        """提取表格数据"""
        try:
            tables = frame.locator("table")
            table_count = tables.count()
            
            if table_count == 0:
                print("未找到表格")
                return []
            
            print(f"发现 {table_count} 个表格")
            all_data = []
            
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
                            "rows": table_data
                        })
                        print(f"  表格 {i+1}: {len(table_data)}/{row_count} 行")
                except Exception as e:
                    print(f"  表格 {i+1} 失败: {e}")
                    continue
            
            return all_data
        except Exception as e:
            print(f"数据提取失败: {e}")
            return []
    
    def navigate_to_page(self, page_config: PageConfig) -> bool:
        """根据配置导航到指定页面"""
        print(f"4. 导航到目标页面: {page_config.name}")
        
        # 对于P4TC页面，使用原始脚本的精确逻辑
        if page_config.name == "P4TC现货应用决策":
            # 使用原始脚本的导航选择器
            nav_selectors = [
                ".bi-f-c > .bi-icon-change-button > .x-icon",
                "div:nth-child(2) > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
                "div:nth-child(2) > div > div:nth-child(2) > .bi-custom-tree > .bi-button-tree > div:nth-child(2) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon",
                "div:nth-child(3) > div > div:nth-child(2) > .bi-icon-change-button > .x-icon"
            ]
            
            for selector in nav_selectors:
                self.try_click(self.report_frame, selector)
            
            self.try_click(self.report_frame, "text='现货应用决策'")
            print("✓ 导航完成")
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
        time.sleep(2)
        
        inner_frames = self.report_frame.locator("iframe")
        target_frame = None
        
        for i in range(inner_frames.count()):
            try:
                if inner_frames.nth(i).is_visible(timeout=2000):
                    target_frame = self.report_frame.frame_locator("iframe").nth(i)
                    break
            except Exception:
                continue
        
        if not target_frame:
            target_frame = self.report_frame.frame_locator("iframe").first
        
        return target_frame
    
    def query_data(self, target_frame: FrameLocator, page_config: PageConfig) -> bool:
        """执行数据查询"""
        # 对于P4TC页面，使用原始脚本的查询逻辑
        if page_config.name == "P4TC现货应用决策":
            if self.try_click(target_frame, [
                "button:has-text('查询')",
                "button[type='submit']"
            ]):
                print("6. 查询执行，等待响应...")
                time.sleep(3)
            return True
        else:
            # 其他页面的查询逻辑
            config = page_config.data_extraction_config
            wait_time = config.get("wait_after_query", 3)
            
            if self.try_click(target_frame, page_config.query_button_selectors):
                print("查询执行，等待响应...")
                time.sleep(wait_time)
                return True
            
            print("未找到查询按钮，可能页面已自动加载数据")
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
        python data_scraper.py --browser firefox
        
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
