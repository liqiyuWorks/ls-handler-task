"""
数据抓取器 - 重构版本
支持配置化的多页面数据获取
"""
from playwright.sync_api import Playwright, sync_playwright, FrameLocator
import json
from datetime import datetime
import sys
import time
from typing import List, Optional, Dict
from page_config import PageConfig, get_page_config, get_page_info


class DataScraper:
    """数据抓取器类"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self.report_frame = None
        
    def create_browser(self, playwright: Playwright):
        """创建浏览器实例"""
        args = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor,TranslateUI',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-extensions',
            '--disable-sync',
            '--disable-translate',
            '--memory-pressure-off'
        ]
        
        self.browser = playwright.chromium.launch(headless=self.headless, args=args)
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            ignore_https_errors=True
        )
        
    def try_click(self, frame: FrameLocator, selectors: List[str], operation: str = "click", 
                  text: str = None, timeout: int = 3000) -> bool:
        """尝试多个选择器直到成功"""
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            try:
                if text:
                    # 文本匹配
                    element = frame.locator(f"text='{text}'").first
                else:
                    element = frame.locator(selector).first
                    
                element.wait_for(state="visible", timeout=timeout)
                
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
                success = self.try_click(
                    self.report_frame, 
                    step.selectors, 
                    text=step.text
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
            # 直接使用原始脚本的逻辑，不等待特定元素
            time.sleep(2)  # 给登录一些时间
            
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
        """保存提取的数据"""
        if not data:
            print("✗ 无数据可保存")
            return False
        
        page_config = get_page_config(page_key)
        page_name = page_config.name if page_config else page_key
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        total_rows = sum(t.get("extracted_rows", 0) for t in data)
        
        # 保存JSON文件
        json_filename = f"{page_key}_data_{timestamp}.json"
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
        
        # 保存TXT文件
        txt_filename = f"{page_key}_data_{timestamp}.txt"
        with open(txt_filename, "w", encoding="utf-8") as f:
            for table in data:
                rows = table.get("rows", [])
                for row in rows:
                    f.write("\t".join(row) + "\n")
                f.write("\n")  # 表格之间空行
        
        print(f"\n✓ 数据已保存:")
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
    """主函数"""
    print("=== AquaBridge 数据抓取器 ===")
    print("可用页面:")
    
    page_info = get_page_info()
    for key, info in page_info.items():
        print(f"  {key}: {info['name']} - {info['description']}")
    
    # 默认抓取P4TC现货应用决策
    page_key = "p4tc_spot_decision"
    
    # 可以通过命令行参数指定页面
    if len(sys.argv) > 1:
        page_key = sys.argv[1]
    
    if page_key not in page_info:
        print(f"\n✗ 无效的页面键: {page_key}")
        print(f"可用页面: {list(page_info.keys())}")
        return
    
    try:
        with sync_playwright() as playwright:
            scraper = DataScraper(headless=True)
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
        sys.exit(1)


if __name__ == "__main__":
    main()
