#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 配置类 - Docker 容器优化版本
"""

import os
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from typing import Optional, Dict, Any


class PlaywrightConfig:
    """Playwright 配置类，专门针对 Docker 容器环境优化"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Docker 容器中的浏览器启动参数
        self.browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceLogging',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--disable-extensions',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio',
            '--no-default-browser-check',
            '--safebrowsing-disable-auto-update',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--ignore-certificate-errors-spki-list',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # 浏览器上下文配置
        self.context_config = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'zh-CN',
            'timezone_id': 'Asia/Shanghai',
            'extra_http_headers': {
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
    
    async def start(self):
        """启动 Playwright 浏览器"""
        try:
            logger.info("启动 Playwright 浏览器...")
            
            self.playwright = await async_playwright().start()
            
            # 启动浏览器
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=self.browser_args,
                executable_path=None  # 使用系统安装的 Chromium
            )
            
            # 创建浏览器上下文
            self.context = await self.browser.new_context(**self.context_config)
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 设置页面超时
            self.page.set_default_timeout(30000)
            self.page.set_default_navigation_timeout(30000)
            
            logger.info("Playwright 浏览器启动成功")
            
        except Exception as e:
            logger.error(f"启动 Playwright 浏览器失败: {e}")
            await self.cleanup()
            raise
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
        except Exception as e:
            logger.warning(f"关闭页面时出错: {e}")
        
        try:
            if self.context:
                await self.context.close()
                self.context = None
        except Exception as e:
            logger.warning(f"关闭浏览器上下文时出错: {e}")
        
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
        except Exception as e:
            logger.warning(f"关闭浏览器时出错: {e}")
        
        try:
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"停止 Playwright 时出错: {e}")
    
    async def take_screenshot(self, prefix: str, full_page: bool = True) -> Optional[str]:
        """统一的截图方法"""
        if not self.page:
            logger.error("页面未初始化，无法截图")
            return None
        
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"static/screenshots/{prefix}_{timestamp}.png"
            
            # 确保目录存在
            os.makedirs("static/screenshots", exist_ok=True)
            
            # 设置截图选项
            screenshot_options = {
                'path': screenshot_path,
                'full_page': full_page,
                'type': 'png'
            }
            
            # 在 Docker 容器中，可能需要等待页面完全渲染
            await self.page.wait_for_timeout(1000)
            
            # 截图
            await self.page.screenshot(**screenshot_options)
            
            logger.info(f"截图已保存: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    async def navigate_to_page(self, url: str, wait_until: str = "networkidle") -> bool:
        """导航到页面"""
        if not self.page:
            logger.error("页面未初始化")
            return False
        
        try:
            logger.info(f"正在导航到页面: {url}")
            
            # 导航到页面
            response = await self.page.goto(url, wait_until=wait_until, timeout=30000)
            
            if not response or response.status >= 400:
                logger.error(f"页面加载失败，状态码: {response.status if response else 'None'}")
                return False
            
            # 等待页面完全加载
            await self.page.wait_for_timeout(5000)
            
            logger.info("页面加载成功")
            return True
            
        except Exception as e:
            logger.error(f"导航到页面失败: {e}")
            return False
    
    async def find_element(self, selectors: list) -> Optional[Any]:
        """查找元素"""
        if not self.page:
            logger.error("页面未初始化")
            return None
        
        for selector in selectors:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    logger.info(f"找到元素，使用选择器: {selector}")
                    return element
            except Exception as e:
                logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        logger.error("未找到指定元素")
        return None
    
    async def modify_element_text(self, element, new_text: str) -> bool:
        """修改元素文本"""
        if not element:
            logger.error("元素为空")
            return False
        
        try:
            # 使用更安全的 JavaScript 执行方式
            result = await self.page.evaluate(f"""
                (element) => {{
                    try {{
                        // 保存原始内容
                        const originalContent = element.textContent;
                        
                        // 更新文本内容
                        element.textContent = '{new_text}';
                        element.innerText = '{new_text}';
                        
                        // 如果是输入框，也更新值
                        if (element.tagName === 'INPUT') {{
                            element.value = '{new_text}';
                        }}
                        
                        // 触发事件
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        
                        // 强制重绘
                        element.style.transform = 'translateZ(0)';
                        
                        console.log('文本修改成功:', '{new_text}');
                        return true;
                    }} catch (error) {{
                        console.error('文本修改失败:', error);
                        return false;
                    }}
                }}
            """, element)
            
            # 验证修改是否成功
            await self.page.wait_for_timeout(1000)
            new_content = await element.text_content()
            if new_text in new_content:
                logger.info(f"文本修改成功: {new_content}")
                return True
            else:
                logger.warning(f"文本修改可能失败，当前内容: {new_content}")
                return False
                
        except Exception as e:
            logger.error(f"修改文本失败: {e}")
            return False


# 使用示例
async def example_usage():
    """使用示例"""
    async with PlaywrightConfig(headless=True) as config:
        # 导航到页面
        success = await config.navigate_to_page("https://example.com")
        if not success:
            return
        
        # 查找元素
        element = await config.find_element([
            "//span[contains(@class, 'date')]",
            "//div[contains(@class, 'date')]//span"
        ])
        
        if element:
            # 修改文本
            await config.modify_element_text(element, "2024-01-01")
            
            # 截图
            await config.take_screenshot("example")


if __name__ == "__main__":
    asyncio.run(example_usage()) 