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
        
        # 🚀 优化：精简浏览器启动参数，提高启动速度
        self.browser_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio',
            '--force-device-scale-factor=2',  # 保留高DPI
            '--disable-web-security',  # 加速加载
            '--disable-background-networking',  # 减少后台网络
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # 浏览器上下文配置 - 优化截图质量
        self.context_config = {
            'viewport': {'width': 1920, 'height': 1080},
            'device_scale_factor': 2,  # 2倍DPR，提高截图清晰度
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
            
            # 🚀 优化：减少超时时间，提高响应速度
            self.page.set_default_timeout(15000)  # 15秒
            self.page.set_default_navigation_timeout(20000)  # 20秒
            
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
            
            # 设置高质量截图选项
            screenshot_options = {
                'path': screenshot_path,
                'full_page': full_page,
                'type': 'png',
                'omit_background': False,  # 保留背景
                'scale': 'device'  # 使用设备缩放，利用device_scale_factor
            }
            
            # 等待页面完全渲染，确保所有内容加载完成
            await self.page.wait_for_timeout(3000)  # 增加等待时间
            
            # 等待所有图片加载完成
            await self.page.wait_for_load_state('networkidle')
            
            # 截图
            await self.page.screenshot(**screenshot_options)
            
            logger.info(f"截图已保存: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None
    
    async def save_page_as_image(self, prefix: str = "page_save") -> Optional[str]:
        """保存页面为图片，类似右击保存页面的效果"""
        if not self.page:
            logger.error("页面未初始化，无法截图")
            return None
        
        try:
            from datetime import datetime
            import re
            
            # 获取页面标题作为文件名的一部分
            page_title = await self.page.title()
            if page_title:
                # 清理标题中的特殊字符，只保留中文、英文、数字
                clean_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', page_title)
                clean_title = re.sub(r'\s+', '_', clean_title.strip())
                if len(clean_title) > 20:
                    clean_title = clean_title[:20]
            else:
                clean_title = "page"
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建更友好的文件名
            filename = f"{clean_title}_{prefix}_{timestamp}.png"
            screenshot_path = f"static/screenshots/{filename}"
            
            # 确保目录存在
            os.makedirs("static/screenshots", exist_ok=True)
            
            # 等待页面完全加载和渲染
            await self.page.wait_for_timeout(3000)  # 增加等待时间
            
            # 等待所有资源加载完成
            await self.page.wait_for_load_state('networkidle')
            
            # 获取页面尺寸
            viewport = self.page.viewport_size
            page_height = await self.page.evaluate("document.documentElement.scrollHeight")
            
            # 设置高质量截图选项
            screenshot_options = {
                'path': screenshot_path,
                'full_page': True,
                'type': 'png',
                'omit_background': False,  # 包含背景
                'scale': 'device'  # 使用设备缩放获得更高清晰度
            }
            
            # 截图
            await self.page.screenshot(**screenshot_options)
            
            # 获取文件大小
            file_size = os.path.getsize(screenshot_path)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"页面已保存为图片: {screenshot_path} (大小: {file_size_mb:.2f}MB)")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"保存页面为图片失败: {e}")
            return None
    
    async def capture_full_page_report(self, prefix: str = "full_page_report") -> Optional[str]:
        """
        实现类似getfireshot.com的整页捕获功能
        1. 确保所有内容都已加载
        2. 滚动到页面顶部
        3. 捕获整个页面
        """
        if not self.page:
            logger.error("页面未初始化，无法截图")
            return None
        
        try:
            from datetime import datetime
            import re
            
            logger.info("开始执行整页捕获，类似getfireshot.com方式...")
            
            # 获取页面标题作为文件名的一部分
            page_title = await self.page.title()
            if page_title:
                clean_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', page_title)
                clean_title = re.sub(r'\s+', '_', clean_title.strip())
                if len(clean_title) > 20:
                    clean_title = clean_title[:20]
            else:
                clean_title = "page"
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建更友好的文件名
            filename = f"{clean_title}_{prefix}_{timestamp}.png"
            screenshot_path = f"static/screenshots/{filename}"
            
            # 确保目录存在
            os.makedirs("static/screenshots", exist_ok=True)
            
            # 1. 确保所有内容都已加载完成
            logger.info("等待所有内容加载完成...")
            await self.page.wait_for_load_state('networkidle')
            
            # 等待动态内容加载
            await self.page.wait_for_timeout(3000)
            
            # 等待所有图片、CSS和JavaScript完全加载
            await self.page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        // 等待所有资源加载完成
                        const images = document.querySelectorAll('img');
                        const stylesheets = document.querySelectorAll('link[rel="stylesheet"]');
                        const scripts = document.querySelectorAll('script[src]');
                        
                        let loadedImages = 0;
                        let loadedStylesheets = 0;
                        let loadedScripts = 0;
                        
                        const totalImages = images.length;
                        const totalStylesheets = stylesheets.length;
                        const totalScripts = scripts.length;
                        
                        function checkAllLoaded() {
                            if (loadedImages === totalImages && 
                                loadedStylesheets === totalStylesheets && 
                                loadedScripts === totalScripts) {
                                resolve();
                            }
                        }
                        
                        // 加载图片
                        if (totalImages === 0) {
                            loadedImages = 0;
                        } else {
                            images.forEach(img => {
                                if (img.complete) {
                                    loadedImages++;
                                } else {
                                    img.onload = () => {
                                        loadedImages++;
                                        checkAllLoaded();
                                    };
                                    img.onerror = () => {
                                        loadedImages++;
                                        checkAllLoaded();
                                    };
                                }
                            });
                        }
                        
                        // 检查样式表
                        if (totalStylesheets === 0) {
                            loadedStylesheets = 0;
                        } else {
                            stylesheets.forEach(link => {
                                if (link.sheet) {
                                    loadedStylesheets++;
                                } else {
                                    link.onload = () => {
                                        loadedStylesheets++;
                                        checkAllLoaded();
                                    };
                                    link.onerror = () => {
                                        loadedStylesheets++;
                                        checkAllLoaded();
                                    };
                                }
                            });
                        }
                        
                        // 检查脚本
                        if (totalScripts === 0) {
                            loadedScripts = 0;
                        } else {
                            scripts.forEach(script => {
                                if (script.readyState === 'loaded' || script.readyState === 'complete') {
                                    loadedScripts++;
                                } else {
                                    script.onload = () => {
                                        loadedScripts++;
                                        checkAllLoaded();
                                    };
                                    script.onerror = () => {
                                        loadedScripts++;
                                        checkAllLoaded();
                                    };
                                }
                            });
                        }
                        
                        // 初始检查
                        checkAllLoaded();
                        
                        // 15秒超时
                        setTimeout(resolve, 15000);
                    });
                }
            """)
            
            # 2. 滚动到页面最顶部（关键步骤）
            logger.info("滚动到页面顶部...")
            await self.page.evaluate("window.scrollTo(0, 0)")
            await self.page.wait_for_timeout(1000)  # 等待滚动完成
            
            # 确保页面已经回到顶部
            scroll_position = await self.page.evaluate("window.pageYOffset")
            logger.info(f"当前滚动位置: {scroll_position}")
            
            # 3. 获取完整页面尺寸
            page_metrics = await self.page.evaluate("""
                () => {
                    return {
                        scrollWidth: document.documentElement.scrollWidth,
                        scrollHeight: document.documentElement.scrollHeight,
                        clientWidth: document.documentElement.clientWidth,
                        clientHeight: document.documentElement.clientHeight,
                        viewportWidth: window.innerWidth,
                        viewportHeight: window.innerHeight
                    };
                }
            """)
            
            logger.info(f"页面尺寸信息: {page_metrics}")
            
            # 4. 进行整页截图（类似getfireshot.com的处理方式）
            logger.info("开始整页截图...")
            
            # 设置高质量截图选项（类似getfireshot.com的质量标准）
            screenshot_options = {
                'path': screenshot_path,
                'full_page': True,  # 关键：启用整页截图
                'type': 'png',
                'omit_background': False,  # 保留背景
                'scale': 'device',  # 使用设备缩放，利用device_scale_factor获得更高清晰度
                'clip': None,  # 不裁剪，捕获整个页面
                'animations': 'disabled'  # 禁用动画，确保截图稳定
                # 注意：quality参数仅适用于JPEG格式，PNG格式不支持此参数
            }
            
            # 在截图前禁用页面动画和过渡效果，提高截图质量
            await self.page.add_style_tag(content="""
                *, *::before, *::after {
                    animation-duration: 0s !important;
                    animation-delay: 0s !important;
                    transition-duration: 0s !important;
                    transition-delay: 0s !important;
                    scroll-behavior: auto !important;
                }
            """)
            
            # 执行截图
            await self.page.screenshot(**screenshot_options)
            
            # 获取文件信息
            file_size = os.path.getsize(screenshot_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # 验证截图是否成功
            if file_size > 0:
                logger.info(f"✅ 整页截图已成功保存: {screenshot_path}")
                logger.info(f"📊 文件大小: {file_size_mb:.2f}MB")
                logger.info(f"📏 页面尺寸: {page_metrics['scrollWidth']}x{page_metrics['scrollHeight']}px")
                logger.info(f"🔧 使用getfireshot.com类似的整页捕获技术")
            else:
                logger.error("❌ 截图文件大小为0，可能截图失败")
                return None
            
            return screenshot_path
            
        except Exception as e:
            logger.error(f"整页截图失败: {e}")
            return None

    async def save_element_as_image(self, element_selector: str, prefix: str = "element_save") -> Optional[str]:
        """保存特定元素为图片，确保包含完整内容"""
        if not self.page:
            logger.error("页面未初始化，无法截图")
            return None
        
        try:
            from datetime import datetime
            import re
            
            # 等待元素出现
            await self.page.wait_for_selector(element_selector, timeout=10000)
            
            # 获取元素
            element = await self.page.query_selector(element_selector)
            if not element:
                logger.error(f"未找到元素: {element_selector}")
                return None
            
            # 获取页面标题作为文件名的一部分
            page_title = await self.page.title()
            if page_title:
                # 清理标题中的特殊字符，只保留中文、英文、数字
                clean_title = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', '', page_title)
                clean_title = re.sub(r'\s+', '_', clean_title.strip())
                if len(clean_title) > 20:
                    clean_title = clean_title[:20]
            else:
                clean_title = "page"
            
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 创建更友好的文件名
            filename = f"{clean_title}_{prefix}_{timestamp}.png"
            screenshot_path = f"static/screenshots/{filename}"
            
            # 确保目录存在
            os.makedirs("static/screenshots", exist_ok=True)
            
            # 等待页面完全加载和渲染
            await self.page.wait_for_timeout(3000)  # 增加等待时间
            
            # 等待所有图片和内容加载完成
            await self.page.wait_for_load_state('networkidle')
            
            # 如果是reportRef元素，先滚动到页面顶部，然后再滚动到元素
            if "reportRef" in element_selector:
                logger.info("检测到reportRef元素，先滚动到页面顶部...")
                await self.page.evaluate("window.scrollTo(0, 0)")
                await self.page.wait_for_timeout(500)
            
            # 滚动到元素位置，确保元素可见
            await element.scroll_into_view_if_needed()
            await self.page.wait_for_timeout(1000)  # 等待滚动完成
            
            # 检查是否为reportRef元素，如果是，执行特殊处理确保包含完整内容
            if "reportRef" in element_selector:
                logger.info("检测到reportRef元素，执行完整内容确保逻辑...")
                
                # 检查特定内容区域是否存在
                specific_content_exists = False
                try:
                    specific_content = await self.page.query_selector('//*[@id="reportRef"]/div[2]/div/div[1]/div/div/div')
                    if specific_content:
                        specific_content_exists = True
                        logger.info("发现特定内容区域，将确保其在截图中")
                        # 滚动到特定内容区域
                        await specific_content.scroll_into_view_if_needed()
                        await self.page.wait_for_timeout(500)
                except:
                    logger.debug("特定内容区域不存在或无法访问")
                
                # 强制展开可能的折叠内容
                try:
                    await self.page.evaluate("""
                        () => {
                            // 展开可能的折叠内容
                            const reportRef = document.getElementById('reportRef');
                            if (reportRef) {
                                // 查找并展开所有可能的收缩元素
                                const expandableElements = reportRef.querySelectorAll('[style*="display: none"], .collapsed, .folded');
                                expandableElements.forEach(el => {
                                    el.style.display = 'block';
                                    el.classList.remove('collapsed', 'folded');
                                });
                                
                                // 触发可能的展开按钮
                                const expandButtons = reportRef.querySelectorAll('button, span, div');
                                expandButtons.forEach(btn => {
                                    const text = btn.textContent || '';
                                    if (text.includes('展开') || text.includes('详情') || text.includes('更多')) {
                                        btn.click();
                                    }
                                });
                            }
                        }
                    """)
                    await self.page.wait_for_timeout(1000)
                    logger.info("已尝试展开所有可能的折叠内容")
                except Exception as e:
                    logger.debug(f"展开内容时出错: {e}")
                
                # 等待内容重新渲染
                await self.page.wait_for_timeout(1000)
            
            # 在截图前禁用页面动画和过渡效果，提高截图质量
            await self.page.add_style_tag(content="""
                *, *::before, *::after {
                    animation-duration: 0s !important;
                    animation-delay: 0s !important;
                    transition-duration: 0s !important;
                    transition-delay: 0s !important;
                    scroll-behavior: auto !important;
                }
            """)
            
            # 设置高质量截图选项
            screenshot_options = {
                'path': screenshot_path,
                'type': 'png',
                'omit_background': False,  # 包含背景
                'scale': 'device',  # 使用设备缩放，利用device_scale_factor获得更高清晰度
                'animations': 'disabled'  # 禁用动画，确保截图稳定
            }
            
            # 截取元素
            await element.screenshot(**screenshot_options)
            
            # 获取文件大小
            file_size = os.path.getsize(screenshot_path)
            file_size_mb = file_size / (1024 * 1024)
            
            logger.info(f"元素已保存为图片: {screenshot_path} (大小: {file_size_mb:.2f}MB)")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"保存元素为图片失败: {e}")
            return None
    
    async def save_element_as_image_optimized(self, element_selector: str, prefix: str = "element_save") -> Optional[str]:
        """优化版本：快速元素截图"""
        if not self.page:
            logger.error("页面未初始化，无法截图")
            return None
        
        try:
            from datetime import datetime
            import re
            
            logger.info(f"⚡ 快速截图元素: {element_selector}")
            
            # 🚀 优化：减少等待时间
            await self.page.wait_for_selector(element_selector, timeout=5000)
            element = await self.page.query_selector(element_selector)
            
            if not element:
                logger.error(f"未找到元素: {element_selector}")
                return None
            
            # 🚀 优化：简化文件名生成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"static/screenshots/{prefix}_{timestamp}.png"
            
            # 确保目录存在
            os.makedirs("static/screenshots", exist_ok=True)
            
            # 🚀 优化：只做必要的等待
            await self.page.wait_for_timeout(800)
            
            # 🚀 优化：并行处理滚动和样式
            if "reportRef" in element_selector:
                scroll_task = self.page.evaluate("window.scrollTo(0, 0)")
                style_task = self.page.add_style_tag(content="*{animation:none!important;transition:none!important}")
                
                await scroll_task
                await style_task
                await self.page.wait_for_timeout(300)
            
            # 滚动到元素
            await element.scroll_into_view_if_needed()
            
            # 🚀 优化：快速截图设置
            screenshot_options = {
                'path': screenshot_path,
                'type': 'png',
                'omit_background': False,
                'scale': 'device'
            }
            
            # 截图
            await element.screenshot(**screenshot_options)
            
            # 验证文件
            file_size = os.path.getsize(screenshot_path)
            if file_size > 0:
                logger.info(f"⚡ 快速截图完成: {screenshot_path} ({file_size/1024/1024:.1f}MB)")
                return screenshot_path
            else:
                return None
            
        except Exception as e:
            logger.error(f"快速截图失败: {e}")
            return None
    
    async def navigate_to_page(self, url: str, wait_until: str = "networkidle") -> bool:
        """导航到页面"""
        if not self.page:
            logger.error("页面未初始化")
            return False
        
        try:
            logger.info(f"正在导航到页面: {url}")
            
            # 🚀 优化：减少导航超时
            response = await self.page.goto(url, wait_until=wait_until, timeout=20000)
            
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
        """🚀 优化版本：快速查找元素"""
        if not self.page:
            logger.error("页面未初始化")
            return None
        
        # 🚀 优化：并行查找多个选择器
        for selector in selectors:
            try:
                # 使用短超时快速尝试
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    logger.info(f"⚡ 快速找到元素: {selector}")
                    return element
            except Exception:
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