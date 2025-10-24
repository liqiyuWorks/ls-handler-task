#!/usr/bin/env python3
"""
测试优化后的authorization提取功能
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


def test_authorization_extraction():
    """测试authorization提取功能"""
    logger.info("开始测试优化后的authorization提取功能")
    
    try:
        with sync_playwright() as playwright:
            login_manager = FISLoginManager()
            auth_info = login_manager.run(playwright)
            
            if auth_info:
                logger.log_success(f"测试成功！获取到 {len(auth_info)} 个authorization信息")
                
                # 打印详细信息
                for key, value in auth_info.items():
                    logger.info(f"{key}: {value[:100]}..." if len(value) > 100 else f"{key}: {value}")
                
                return True
            else:
                logger.log_error("测试失败：未获取到authorization信息")
                return False
                
    except Exception as e:
        logger.log_error(f"测试过程中出现错误: {str(e)}")
        return False


def test_individual_extraction_methods():
    """测试各个提取方法的单独功能"""
    logger.info("开始测试各个提取方法的单独功能")
    
    try:
        with sync_playwright() as playwright:
            login_manager = FISLoginManager()
            
            # 启动浏览器并登录
            browser_config = login_manager.config.get('browser', {})
            browser = playwright.chromium.launch(
                headless=browser_config.get('headless', False)
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
            
            # 测试各个提取方法
            logger.info("=" * 50)
            logger.info("测试各个提取方法")
            logger.info("=" * 50)
            
            # 方法1: localStorage
            logger.info("测试方法1: localStorage提取")
            result1 = login_manager._extract_auth0_access_token(page)
            logger.info(f"结果: {result1}")
            
            # 方法2: sessionStorage
            logger.info("测试方法2: sessionStorage提取")
            result2 = login_manager._extract_session_storage_token(page)
            logger.info(f"结果: {result2}")
            
            # 方法3: 页面内容
            logger.info("测试方法3: 页面内容提取")
            result3 = login_manager._extract_bearer_token_from_content(page)
            logger.info(f"结果: {result3}")
            
            # 方法4: 网络请求
            logger.info("测试方法4: 网络请求提取")
            result4 = login_manager._extract_auth_from_network_requests(page, context)
            logger.info(f"结果: {result4}")
            
            # 方法5: JavaScript变量
            logger.info("测试方法5: JavaScript变量提取")
            result5 = login_manager._extract_token_from_js_variables(page)
            logger.info(f"结果: {result5}")
            
            # 清理资源
            page.close()
            context.close()
            browser.close()
            
            logger.log_success("各个提取方法测试完成")
            return True
            
    except Exception as e:
        logger.log_error(f"测试各个提取方法时出现错误: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始测试优化后的FIS authorization提取功能")
    logger.info("=" * 60)
    
    # 测试完整的authorization提取流程
    success1 = test_authorization_extraction()
    
    logger.info("\n" + "=" * 60)
    
    # 测试各个提取方法的单独功能
    success2 = test_individual_extraction_methods()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试总结:")
    logger.info(f"完整流程测试: {'成功' if success1 else '失败'}")
    logger.info(f"单独方法测试: {'成功' if success2 else '失败'}")
    logger.info("=" * 60)
