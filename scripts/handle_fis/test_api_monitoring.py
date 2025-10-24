#!/usr/bin/env python3
"""
测试API请求监听功能
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


def test_api_monitoring():
    """测试API请求监听功能"""
    logger.info("开始测试API请求监听功能")
    
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
            
            logger.info("=" * 60)
            logger.info("开始测试API请求监听")
            logger.info("=" * 60)
            
            # 测试网络请求监听
            result = login_manager._extract_auth_from_network_requests(page, context)
            logger.info(f"网络请求监听结果: {result}")
            
            # 测试主动触发API请求
            result2 = login_manager._trigger_api_requests(page, context)
            logger.info(f"主动触发API请求结果: {result2}")
            
            # 清理资源
            page.close()
            context.close()
            browser.close()
            
            logger.log_success("API请求监听测试完成")
            return True
            
    except Exception as e:
        logger.log_error(f"API请求监听测试失败: {str(e)}")
        return False


def test_direct_api_call():
    """测试直接API调用"""
    logger.info("开始测试直接API调用")
    
    try:
        with sync_playwright() as playwright:
            login_manager = FISLoginManager()
            
            # 启动浏览器
            browser_config = login_manager.config.get('browser', {})
            browser = playwright.chromium.launch(headless=False)
            
            context = browser.new_context(
                user_agent=browser_config.get('user_agent')
            )
            page = context.new_page()
            
            # 直接访问FIS网站
            page.goto("https://www.fis-live.com/markets/dry-ffa")
            page.wait_for_load_state("networkidle")
            
            # 尝试直接调用API
            try:
                result = page.evaluate("""
                    async () => {
                        try {
                            const response = await fetch('https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods', {
                                method: 'GET',
                                headers: {
                                    'Accept': '*/*',
                                    'Accept-Language': 'zh-CN,zh;q=0.9',
                                    'Connection': 'keep-alive',
                                    'Origin': 'https://www.fis-live.com',
                                    'Sec-Fetch-Dest': 'empty',
                                    'Sec-Fetch-Mode': 'cors',
                                    'Sec-Fetch-Site': 'cross-site',
                                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                                    'content-type': 'application/json',
                                    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                                    'sec-ch-ua-mobile': '?0',
                                    'sec-ch-ua-platform': '"macOS"'
                                }
                            });
                            
                            const data = await response.text();
                            return { 
                                status: response.status, 
                                statusText: response.statusText,
                                headers: Object.fromEntries(response.headers.entries()),
                                data: data.substring(0, 500)  // 限制长度
                            };
                        } catch (error) {
                            return { error: error.message };
                        }
                    }
                """)
                
                logger.info(f"直接API调用结果: {result}")
                
            except Exception as e:
                logger.error(f"直接API调用失败: {e}")
            
            # 清理资源
            page.close()
            context.close()
            browser.close()
            
            logger.log_success("直接API调用测试完成")
            return True
            
    except Exception as e:
        logger.log_error(f"直接API调用测试失败: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始API请求监听测试")
    logger.info("=" * 60)
    
    # 测试API请求监听
    success1 = test_api_monitoring()
    
    logger.info("\n" + "=" * 60)
    
    # 测试直接API调用
    success2 = test_direct_api_call()
    
    logger.info("\n" + "=" * 60)
    logger.info("测试总结:")
    logger.info(f"API请求监听测试: {'成功' if success1 else '失败'}")
    logger.info(f"直接API调用测试: {'成功' if success2 else '失败'}")
    logger.info("=" * 60)
