"""
智能等待策略
"""

import time
from typing import Callable, Optional, Any
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from config import config
from logger import logger
from exceptions import FISTimeoutException, FISElementNotFoundException


class WaitStrategies:
    """等待策略工具类"""
    
    @staticmethod
    def wait_for_element_with_strategies(
        page: Page,
        selector: str,
        timeout: Optional[int] = None,
        strategies: list = None
    ) -> Any:
        """
        使用多种策略等待元素出现
        
        Args:
            page: Playwright页面对象
            selector: 元素选择器
            timeout: 超时时间（秒）
            strategies: 等待策略列表
            
        Returns:
            找到的元素
        """
        if strategies is None:
            strategies = ['selector', 'text', 'role', 'placeholder']
        
        timeout_ms = (timeout or config.get('wait.element_timeout', 10)) * 1000
        
        for strategy in strategies:
            try:
                if strategy == 'selector':
                    element = page.wait_for_selector(selector, timeout=timeout_ms)
                    logger.debug(f"通过选择器策略找到元素: {selector}")
                    return element
                    
                elif strategy == 'text':
                    element = page.get_by_text(selector)
                    element.wait_for(timeout=timeout_ms)
                    logger.debug(f"通过文本策略找到元素: {selector}")
                    return element
                    
                elif strategy == 'role':
                    element = page.get_by_role(selector)
                    element.wait_for(timeout=timeout_ms)
                    logger.debug(f"通过角色策略找到元素: {selector}")
                    return element
                    
                elif strategy == 'placeholder':
                    element = page.get_by_placeholder(selector)
                    element.wait_for(timeout=timeout_ms)
                    logger.debug(f"通过占位符策略找到元素: {selector}")
                    return element
                    
            except PlaywrightTimeoutError:
                logger.debug(f"策略 {strategy} 超时，尝试下一个策略")
                continue
            except Exception as e:
                logger.debug(f"策略 {strategy} 失败: {str(e)}")
                continue
        
        raise FISElementNotFoundException(f"所有策略都无法找到元素: {selector}")
    
    @staticmethod
    def wait_for_page_load(page: Page, timeout: Optional[int] = None):
        """
        等待页面完全加载
        
        Args:
            page: Playwright页面对象
            timeout: 超时时间（秒）
        """
        timeout_ms = (timeout or config.get('wait.page_load', 5)) * 1000
        
        try:
            logger.debug("等待页面加载...")
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            logger.debug("页面加载完成")
        except PlaywrightTimeoutError:
            logger.log_warning("页面加载超时，但继续执行")
        except Exception as e:
            logger.log_warning(f"页面加载过程中出现异常: {str(e)}")
    
    @staticmethod
    def wait_for_network_idle(page: Page, timeout: Optional[int] = None):
        """
        等待网络空闲
        
        Args:
            page: Playwright页面对象
            timeout: 超时时间（秒）
        """
        timeout_ms = (timeout or config.get('wait.page_load', 5)) * 1000
        
        try:
            logger.debug("等待网络空闲...")
            page.wait_for_load_state("networkidle", timeout=timeout_ms)
            logger.debug("网络空闲")
        except PlaywrightTimeoutError:
            logger.log_warning("等待网络空闲超时")
        except Exception as e:
            logger.log_warning(f"等待网络空闲时出现异常: {str(e)}")
    
    @staticmethod
    def smart_wait_for_login(page: Page, username: str, password: str):
        """
        智能等待登录完成
        
        Args:
            page: Playwright页面对象
            username: 用户名
            password: 密码
        """
        logger.debug("开始智能等待登录...")
        
        # 等待登录表单出现
        try:
            WaitStrategies.wait_for_element_with_strategies(
                page, 
                'input[placeholder*="example.com"]',
                timeout=10
            )
            logger.log_success("登录表单已出现")
        except FISElementNotFoundException:
            logger.log_warning("未找到登录表单，可能已经登录或页面结构已改变")
        
        # 等待登录完成 - 检查URL变化或页面内容变化
        login_wait_time = config.get('wait.login_wait', 3)
        
        for i in range(login_wait_time * 2):  # 每0.5秒检查一次
            try:
                # 检查是否还在登录页面
                current_url = page.url
                if 'login' not in current_url.lower():
                    logger.log_success("登录成功，页面已跳转")
                    return
                
                # 检查是否有错误信息
                error_elements = page.query_selector_all('.error, .alert-danger, .login-error')
                if error_elements:
                    error_text = ' '.join([elem.inner_text() for elem in error_elements if elem.inner_text()])
                    logger.log_error(f"登录失败: {error_text}")
                    return
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.debug(f"检查登录状态时出现异常: {str(e)}")
                time.sleep(0.5)
        
        logger.log_warning("登录等待超时，继续执行")
    
    @staticmethod
    def wait_for_cookies_to_load(context, min_cookies: int = 1, timeout: int = 10):
        """
        等待cookies加载
        
        Args:
            context: Playwright上下文对象
            min_cookies: 最少cookies数量
            timeout: 超时时间（秒）
        """
        logger.debug(f"等待至少 {min_cookies} 个cookies加载...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            cookies = context.cookies()
            if len(cookies) >= min_cookies:
                logger.log_success(f"成功获取 {len(cookies)} 个cookies")
                return cookies
            
            time.sleep(0.5)
        
        logger.log_warning(f"等待cookies超时，当前只有 {len(context.cookies())} 个cookies")
        return context.cookies()
