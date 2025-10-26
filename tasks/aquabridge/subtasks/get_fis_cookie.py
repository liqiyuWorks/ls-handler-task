#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
from playwright.sync_api import sync_playwright
import json
import logging
from pathlib import Path
import time

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from pkg.public.models import BaseModel


class GetFisCookie(BaseModel):
    """获取FIS网站的token"""
    
    def __init__(self):
        config = {
            "cache_rds": True,
        }
        # 初始化BaseModel（不需要数据库配置）
        super(GetFisCookie, self).__init__(config=config)
        
        # 初始化日志 - 只记录关键错误
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
    
    def _navigate_to_login_page(self, page):
        """导航到登录页面"""
        login_url = 'https://www.fis-live.com/markets/dry-ffa'
        print("📌 正在访问FIS Live网站...")
        try:
            page.goto(login_url)
            page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            print(f"❌ 访问网站失败: {str(e)}")
            raise
    
    def _accept_cookie_policy(self, page):
        """接受cookie政策"""
        try:
            # 等待并尝试接受cookie
            time.sleep(2)
            
            # 尝试多种方式找到cookie政策相关元素
            cookie_selectors = [
                'input[type="checkbox"]',
                'button:has-text("Accept")',
                'button:has-text("accept")',
            ]
            
            for selector in cookie_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element:
                        element.click()
                        return
                except:
                    continue
        except Exception as e:
            pass
    
    def _click_login_button(self, page):
        """点击登录按钮"""
        print("📌 正在登录...")
        try:
            # 先等待页面完全加载
            page.wait_for_load_state("networkidle", timeout=10000)
            time.sleep(2)
            
            # 尝试多种方式找到登录按钮
            login_selectors = [
                'button:has-text("Log in")',
                'button:has-text("Login")',
                'a:has-text("Log in")',
            ]
            
            for selector in login_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=3000, state="visible")
                    if element:
                        element.click(timeout=5000)
                        time.sleep(2)
                        return
                except:
                    continue
            
            # 尝试通过角色查找，但先等待按钮变为可点击状态
            try:
                login_btn = page.get_by_role("button", name="Log in / Sign up")
                page.wait_for_timeout(3000)
                login_btn.click(timeout=5000)
                time.sleep(2)
            except Exception as e:
                pass
            
            # 如果上面都失败，尝试强制点击
            try:
                login_btn = page.get_by_role("button", name="Log in / Sign up")
                if login_btn.is_visible():
                    page.evaluate("""
                        () => {
                            const btn = document.querySelector('button:has-text("Log in / Sign up")');
                            if (btn) btn.click();
                        }
                    """)
                    time.sleep(2)
            except Exception as e:
                raise
                
        except Exception as e:
            print(f"❌ 登录失败: {str(e)}")
            raise
    
    def _fill_login_form(self, page):
        """填写登录表单"""
        username = 'terry@aquabridge.ai'
        password = 'Abs,88000'
        
        try:
            # 等待登录表单出现
            page.wait_for_selector('input[placeholder*="example.com"]', timeout=10000)
            time.sleep(1)
            
            # 填写用户名
            username_input = page.get_by_placeholder("yours@example.com")
            username_input.click()
            username_input.fill(username)
            
            # 填写密码
            password_input = page.get_by_placeholder("your password")
            password_input.click()
            password_input.fill(password)
            
        except Exception as e:
            print(f"❌ 填写表单失败: {str(e)}")
            raise
    
    def _submit_login_form(self, page):
        """提交登录表单"""
        try:
            page.get_by_role("button", name="Log In").click()
        except Exception as e:
            print(f"❌ 提交表单失败: {str(e)}")
            raise
    
    def _wait_for_login_completion(self, page):
        """等待登录完成"""
        try:
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)
        except Exception as e:
            pass
    
    def _get_authorization(self, page):
        """获取authorization token"""
        print("📌 正在获取token...")
        
        try:
            # 监听特定的API请求
            target_api_url = "https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods"
            captured_auth = None
            
            def handle_request(request):
                nonlocal captured_auth
                url = request.url
                headers = request.headers
                
                if target_api_url in url and 'authorization' in headers:
                    auth_header = headers['authorization']
                    if auth_header.startswith('Bearer '):
                        captured_auth = auth_header
            
            page.on('request', handle_request)
            page.wait_for_timeout(10000)
            
            if captured_auth:
                token = captured_auth.replace('Bearer ', '')
                return token
            else:
                return None
                
        except Exception as e:
            print(f"❌ 获取token失败: {str(e)}")
            return None
    
    def get_token(self):
        """获取FIS token的核心方法"""
        with sync_playwright() as playwright:
            browser = None
            context = None
            page = None
            
            try:
                # 启动浏览器
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                # 执行完整的登录流程
                self._navigate_to_login_page(page)
                self._accept_cookie_policy(page)
                self._click_login_button(page)
                self._fill_login_form(page)
                self._submit_login_form(page)
                self._wait_for_login_completion(page)
                
                # 获取authorization token
                token = self._get_authorization(page)
                return token
                
            except Exception as e:
                self.logger.error(f"获取token失败: {str(e)}")
                return None
            finally:
                # 清理资源
                try:
                    if page:
                        page.close()
                except:
                    pass
                
                try:
                    if context:
                        context.close()
                except:
                    pass
                
                try:
                    if browser:
                        browser.close()
                except:
                    pass
    
    def run(self):
        """运行任务，获取FIS token"""
        token = self.get_token()
        
        if token:
            print("✅ Token获取成功")
            
            # 保存token到cache_rds
            try:
                authorization = f"Bearer {token}"
                self.cache_rds.set("fis-live", authorization)
                self.logger.info(f"Token已保存到Redis缓存: {authorization}")
            except Exception as e:
                print(f"❌ 保存token失败: {str(e)}")
            
            # 输出完整token
            return token
        else:
            print("❌ 未能获取到token")
            return None
