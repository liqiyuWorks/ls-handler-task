#!/usr/bin/env python3
"""
浏览器会话管理器
支持多页面复用，避免重复登录
"""

import time
from typing import Dict, Any, Optional, List
from data_scraper import DataScraper
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page


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
            
            # 查询数据
            if not self.scraper.query_data(target_frame, page_config):
                print("✗ 查询失败")
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
