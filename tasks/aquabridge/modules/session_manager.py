#!/usr/bin/env python3
"""
浏览器会话管理器
支持多页面复用，避免重复登录
"""

import time
from typing import Dict, Any, Optional, List
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
# 导入data_scraper，注意这里是相对导入
try:
    from .data_scraper import DataScraper
except ImportError:
    from data_scraper import DataScraper


class SessionManager:
    """浏览器会话管理器"""
    
    def __init__(self, browser_type: str = "firefox", headless: bool = False):
        """初始化会话管理器
        
        Args:
            browser_type: 浏览器类型
            headless: 是否无头模式
        """
        self.browser_type = browser_type
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.scraper: Optional[DataScraper] = None
        self.is_logged_in = False
        self.current_page: Optional[Page] = None
    
    def start_session(self) -> bool:
        """启动浏览器会话"""
        try:
            print("=== 启动浏览器会话 ===")
            self.playwright = sync_playwright().start()
            self.scraper = DataScraper(headless=self.headless, browser_type=self.browser_type)
            self.scraper.create_browser(self.playwright)
            
            self.browser = self.scraper.browser
            self.context = self.scraper.context
            
            print(f"✓ 浏览器会话已启动: {self.browser_type}")
            return True
            
        except Exception as e:
            print(f"✗ 启动浏览器会话失败: {e}")
            return False
    
    def login_once(self) -> bool:
        """执行一次登录（如果尚未登录）"""
        if self.is_logged_in:
            print("✓ 用户已登录，跳过登录步骤")
            return True
        
        try:
            print("=== 执行登录 ===")
            if not self.scraper:
                print("✗ 浏览器会话未启动")
                return False
            
            # 创建新页面进行登录
            self.current_page = self.context.new_page()
            self.current_page.set_default_timeout(12000)
            self.current_page.set_default_navigation_timeout(15000)
            
            # 设置页面到scraper
            self.scraper.page = self.current_page
            
            # 执行登录流程（模拟scrape_page_data中的登录部分）
            print("1. 访问网站...")
            self.current_page.goto("https://jinzhengny.com/", wait_until="domcontentloaded")
            self.current_page.locator("#reportFrame").wait_for(state="visible")
            
            self.scraper.report_frame = self.current_page.frame_locator("#reportFrame")
            
            print("2. 登录...")
            self.scraper.try_click(self.scraper.report_frame, [
                "input[placeholder*='Username']",
                "input[placeholder*='用户名']",
                "input[type='text']"
            ], "fill", "15152627161")
            
            self.scraper.try_click(self.scraper.report_frame, "input[type='password']", "fill", "lsls12")
            
            self.scraper.try_click(self.scraper.report_frame, [
                ".bi-h-o > .bi-basic-button",
                "button[type='submit']",
                "button"
            ])
            
            print("3. 等待登录...")
            # 等待导航图标出现，确认登录成功
            self.scraper.report_frame.locator(".bi-f-c > .bi-icon-change-button").first.wait_for(
                state="visible", timeout=10000
            )
            
            self.is_logged_in = True
            print("✓ 登录成功")
            return True
                
        except Exception as e:
            print(f"✗ 登录异常: {e}")
            return False
    
    def scrape_page(self, page_key: str) -> Optional[List[Dict]]:
        """抓取指定页面的数据（复用登录状态）
        
        Args:
            page_key: 页面键
            
        Returns:
            抓取的原始数据或None
        """
        if not self.is_logged_in:
            print("✗ 用户未登录，无法抓取数据")
            return None
        
        try:
            print(f"=== 抓取页面: {page_key} ===")
            
            # 使用现有的页面或创建新页面
            if not self.current_page:
                self.current_page = self.context.new_page()
                self.current_page.set_default_timeout(12000)
                self.current_page.set_default_navigation_timeout(15000)
                self.scraper.page = self.current_page
            
            # 设置页面到scraper
            self.scraper.page = self.current_page
            
            # 获取页面配置
            try:
                from .page_config import get_page_config
            except ImportError:
                from page_config import get_page_config
            page_config = get_page_config(page_key)
            if not page_config:
                print(f"✗ 未找到页面配置: {page_key}")
                return None
            
            # 导航到目标页面
            success = self.scraper.navigate_to_page(page_config)
            if not success:
                print(f"✗ 导航到页面 {page_key} 失败")
                return None
            
            # 找到目标iframe
            target_frame = self.scraper.find_target_frame()
            if not target_frame:
                print("✗ 未找到目标iframe")
                return None
            
            # 检查是否需要截图
            screenshot_config = page_config.screenshot_config
            if screenshot_config and screenshot_config.get("enabled", False):
                # 截图模式：直接截图，不需要查询按钮
                print("检测到截图配置，切换到截图模式...")
                print("6. 等待页面加载...")
                # 等待页面完全加载 - 增加等待时间确保内容加载完成
                wait_time = screenshot_config.get("wait_before_screenshot", 5)
                print(f"  等待 {wait_time} 秒让页面内容加载...")
                time.sleep(wait_time)
                
                # 尝试等待iframe内容出现
                try:
                    print("  检查iframe内容...")
                    # 等待body元素出现
                    target_frame.locator("body").wait_for(state="attached", timeout=10000)
                    # 等待一些时间让内容渲染
                    time.sleep(2)
                    print("  ✓ iframe内容已就绪")
                except Exception as e:
                    print(f"  ⚠ iframe内容检查超时，继续尝试: {e}")
                
                # 处理弹窗（在截图前）
                try:
                    print("  检查并关闭弹窗...")
                    if self.current_page:
                        # 尝试关闭常见的弹窗
                        dialog_selectors = [
                            "button:has-text('OK')",
                            "button:has-text('确定')",
                            "button:has-text('关闭')",
                            ".modal button",
                            "[class*='dialog'] button",
                            "[class*='modal'] button[class*='close']"
                        ]
                        
                        for selector in dialog_selectors:
                            try:
                                dialog_button = self.current_page.locator(selector).first
                                if dialog_button.is_visible(timeout=2000):
                                    dialog_button.click()
                                    print("  ✓ 已关闭弹窗")
                                    time.sleep(1)
                                    break
                            except Exception:
                                continue
                except Exception as e:
                    print(f"  ⚠ 处理弹窗时出错: {e}")
                
                # 截图
                print("7. 截图页面元素...")
                # 传递report_frame以便点击pin按钮
                screenshot_path = self.scraper.screenshot_element(target_frame, screenshot_config, page_key, self.scraper.report_frame)
                
                if not screenshot_path:
                    print("✗ 截图失败")
                    return None
                
                # 提取元数据
                print("8. 提取元数据...")
                metadata = self.scraper.extract_metadata_from_page(target_frame)
                
                # 返回截图数据格式
                result = [{
                    "data_type": "screenshot",
                    "screenshot_path": screenshot_path,
                    "metadata": metadata,
                    "page_key": page_key,
                    "page_name": page_config.name
                }]
                
                print(f"✓ 页面 {page_key} 截图成功")
                return result
            else:
                # 普通数据提取模式（优化：不需要点击查询按钮）
                # 等待数据加载
                if not self.scraper.wait_for_data_load(target_frame, page_config):
                    print("✗ 等待数据加载失败")
                    return None
                
                # 提取数据
                print("7. 提取数据...")
                config = page_config.data_extraction_config
                data = self.scraper.extract_table_data(
                    target_frame, 
                    config.get("max_rows", 100),
                    config.get("max_cells", 20)
                )
                
                # 提取掉期日期（从页面顶部）
                print("8. 提取掉期日期...")
                swap_date = self.scraper.extract_swap_date_from_page(target_frame)
                if swap_date:
                    print(f"✓ 掉期日期: {swap_date}")
                    # 将掉期日期添加到第一个表格的元数据中
                    if data and len(data) > 0:
                        data[0]["swap_date"] = swap_date
                else:
                    # 如果没有找到掉期日期，使用当前日期
                    from datetime import datetime
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    print(f"⚠ 未找到掉期日期，使用当前日期: {current_date}")
                    if data and len(data) > 0:
                        data[0]["swap_date"] = current_date
                
                if data:
                    print(f"✓ 页面 {page_key} 数据抓取成功: {len(data)} 个表格")
                    return data
                else:
                    print(f"✗ 页面 {page_key} 数据抓取失败")
                    return None
                
        except Exception as e:
            print(f"✗ 抓取页面 {page_key} 异常: {e}")
            return None
    
    def scrape_multiple_pages(self, page_keys: List[str]) -> Dict[str, Optional[List[Dict]]]:
        """批量抓取多个页面
        
        Args:
            page_keys: 页面键列表
            
        Returns:
            各页面的抓取结果
        """
        results = {}
        
        print(f"\n=== 批量抓取 {len(page_keys)} 个页面 ===")
        
        for page_key in page_keys:
            try:
                data = self.scrape_page(page_key)
                results[page_key] = data
                
                if data:
                    print(f"✓ {page_key}: 成功")
                else:
                    print(f"✗ {page_key}: 失败")
                    
            except Exception as e:
                print(f"✗ {page_key}: 异常 - {e}")
                results[page_key] = None
        
        return results
    
    def reset_to_initial_state(self, max_retries: int = 2) -> bool:
        """重置页面到登录后的初始状态
        
        刷新页面，恢复到刚登录后的状态，确保菜单都折叠，为下一个页面的导航做准备。
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            是否成功重置
        """
        if not self.is_logged_in:
            print("  ⚠ 用户未登录，无法重置页面状态")
            return False
        
        if not self.current_page:
            print("  ⚠ 当前页面不存在，无法重置")
            return False
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"  [重置页面状态] 尝试 {attempt}/{max_retries}...")
                
                # 方法1: 尝试刷新页面（保持登录状态）
                try:
                    if not self.current_page.is_closed():
                        print("    刷新页面...")
                        self.current_page.reload(wait_until="domcontentloaded", timeout=15000)
                    else:
                        # 如果页面已关闭，重新导航
                        print("    页面已关闭，重新导航...")
                        self.current_page = self.context.new_page()
                        self.current_page.set_default_timeout(12000)
                        self.current_page.set_default_navigation_timeout(15000)
                        self.current_page.goto("https://jinzhengny.com/", wait_until="domcontentloaded")
                        self.scraper.page = self.current_page
                except Exception as e:
                    print(f"    ⚠ 刷新页面失败: {e}")
                    # 如果刷新失败，尝试重新导航
                    try:
                        print("    尝试重新导航到首页...")
                        if self.current_page and not self.current_page.is_closed():
                            self.current_page.goto("https://jinzhengny.com/", wait_until="domcontentloaded", timeout=15000)
                        else:
                            self.current_page = self.context.new_page()
                            self.current_page.set_default_timeout(12000)
                            self.current_page.set_default_navigation_timeout(15000)
                            self.current_page.goto("https://jinzhengny.com/", wait_until="domcontentloaded")
                            self.scraper.page = self.current_page
                    except Exception as e2:
                        print(f"    ✗ 重新导航也失败: {e2}")
                        if attempt < max_retries:
                            time.sleep(2)
                            continue
                        return False
                
                # 等待 iframe 加载
                print("    等待 iframe 加载...")
                try:
                    self.current_page.locator("#reportFrame").wait_for(state="visible", timeout=10000)
                    time.sleep(1)  # 额外等待确保 iframe 内容加载
                except Exception as e:
                    print(f"    ⚠ 等待 iframe 超时: {e}")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                
                # 重新获取 report_frame 引用
                print("    重新获取 report_frame...")
                try:
                    self.scraper.report_frame = self.current_page.frame_locator("#reportFrame")
                except Exception as e:
                    print(f"    ⚠ 获取 report_frame 失败: {e}")
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                
                # 验证登录状态（等待导航图标出现）
                print("    验证登录状态...")
                try:
                    self.scraper.report_frame.locator(".bi-f-c > .bi-icon-change-button").first.wait_for(
                        state="visible", timeout=10000
                    )
                    print("    ✓ 登录状态确认")
                except Exception as e:
                    print(f"    ⚠ 登录状态验证失败: {e}")
                    # 如果登录状态验证失败，可能需要重新登录
                    if attempt < max_retries:
                        print("    尝试重新登录...")
                        self.is_logged_in = False
                        if not self.login_once():
                            print("    ✗ 重新登录失败")
                            return False
                        continue
                    else:
                        print("    ✗ 无法确认登录状态")
                        return False
                
                # 等待页面完全稳定
                time.sleep(1)
                
                print("  ✓ 页面已重置到初始状态")
                return True
                
            except Exception as e:
                print(f"  ✗ 重置页面状态异常: {e}")
                if attempt < max_retries:
                    print(f"  ⚠ {2} 秒后重试...")
                    time.sleep(2)
                else:
                    print("  ✗ 重置失败，已达到最大重试次数")
                    return False
        
        return False
    
    def close_session(self):
        """关闭浏览器会话"""
        try:
            if self.current_page:
                self.current_page.close()
                self.current_page = None
            
            if self.scraper:
                self.scraper.cleanup()
                self.scraper = None
            
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            
            self.browser = None
            self.context = None
            self.is_logged_in = False
            
            print("✓ 浏览器会话已关闭")
            
        except Exception as e:
            print(f"⚠ 关闭浏览器会话时出现异常: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        if self.start_session():
            return self
        else:
            raise Exception("无法启动浏览器会话")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_session()
    
    def is_session_active(self) -> bool:
        """检查会话是否活跃"""
        return (self.playwright is not None and 
                self.browser is not None and 
                self.context is not None and 
                self.is_logged_in)


# 会话管理器主要用于内部调用，不提供独立的命令行接口
