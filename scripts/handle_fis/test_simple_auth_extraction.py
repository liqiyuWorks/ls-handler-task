#!/usr/bin/env python3
"""
简单的authorization提取测试脚本
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from playwright.sync_api import sync_playwright
from get_fis_cookie import FISLoginManager
from logger import logger


def test_simple_auth_extraction():
    """简单的authorization提取测试"""
    logger.info("开始简单的authorization提取测试")
    
    try:
        with sync_playwright() as playwright:
            login_manager = FISLoginManager()
            
            # 启动浏览器并登录
            browser_config = login_manager.config.get('browser', {})
            browser = playwright.chromium.launch(
                headless=False  # 设置为非无头模式以便观察
            )
            
            context = browser.new_context(
                user_agent=browser_config.get('user_agent')
            )
            page = context.new_page()
            
            # 执行登录流程
            login_manager._navigate_to_login_page(page)
            login_manager._accept_cookie_policy(page)
            login_manager._click_login_button(page)
            login_manager._fill_login_form(page)
            login_manager._submit_login_form(page)
            login_manager._wait_for_login_completion(page)
            
            # 等待页面完全加载
            page.wait_for_load_state("networkidle", timeout=30000)
            page.wait_for_timeout(5000)
            
            # 获取当前页面URL
            current_url = page.url
            logger.info(f"当前页面URL: {current_url}")
            
            # 获取页面标题
            page_title = page.title()
            logger.info(f"页面标题: {page_title}")
            
            # 检查页面是否包含特定的元素或文本
            try:
                # 查找可能包含用户信息的元素
                user_elements = page.query_selector_all('[class*="user"], [class*="profile"], [class*="account"]')
                logger.info(f"找到 {len(user_elements)} 个用户相关元素")
                
                for i, element in enumerate(user_elements[:5]):  # 只检查前5个
                    try:
                        text = element.inner_text()
                        if text and len(text.strip()) > 0:
                            logger.info(f"用户元素 {i+1}: {text.strip()[:100]}")
                    except:
                        pass
                        
            except Exception as e:
                logger.debug(f"查找用户元素失败: {e}")
            
            # 测试深度搜索功能
            logger.info("=" * 50)
            logger.info("开始深度搜索测试")
            logger.info("=" * 50)
            
            result = login_manager._deep_search_all_storages(page)
            logger.info(f"深度搜索结果: {result}")
            
            # 清理资源
            page.close()
            context.close()
            browser.close()
            
            logger.log_success("简单authorization提取测试完成")
            return True
            
    except Exception as e:
        logger.log_error(f"简单authorization提取测试失败: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始简单authorization提取测试")
    logger.info("=" * 60)
    
    success = test_simple_auth_extraction()
    
    logger.info("\n" + "=" * 60)
    logger.info(f"测试结果: {'成功' if success else '失败'}")
    logger.info("=" * 60)
