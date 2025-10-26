from playwright.sync_api import Playwright, sync_playwright, expect
import time
import json
from typing import Dict, List, Optional

# 导入自定义模块
from config import config
from logger import logger
from exceptions import FISLoginException, FISNetworkException, FISElementNotFoundException
from retry import retry_on_network_failure, retry_on_element_not_found
from wait_strategies import WaitStrategies


class FISLoginManager:
    """FIS Live 登录管理器"""
    
    def __init__(self):
        """初始化登录管理器"""
        self.config = config
        self.logger = logger
        self.config.create_directories()
    
    @retry_on_network_failure(max_attempts=3, delay=5.0)
    def _navigate_to_login_page(self, page) -> None:
        """导航到登录页面"""
        login_url = self.config.get('website.login_url')
        self.logger.log_step("访问FIS Live网站", f"URL: {login_url}")
        
        try:
            page.goto(login_url)
            WaitStrategies.wait_for_page_load(page)
            self.logger.log_success("成功访问FIS Live网站")
        except Exception as e:
            raise FISNetworkException(f"访问网站失败: {str(e)}")
    
    @retry_on_element_not_found(max_attempts=3, delay=2.0)
    def _accept_cookie_policy(self, page) -> None:
        """接受cookie政策"""
        self.logger.log_step("接受cookie政策")
        
        try:
            # 尝试多种方式找到cookie政策按钮
            cookie_selectors = [
                'input[type="checkbox"][id*="cookie"]',
                'input[type="checkbox"][id*="accept"]',
                'button[id*="cookie"]',
                'button[id*="accept"]'
            ]
            
            for selector in cookie_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element:
                        element.click()
                        self.logger.log_success("成功接受cookie政策")
                        return
                except:
                    continue
            
            # 尝试通过标签文本查找
            try:
                page.get_by_label("By clicking 'accept', you agree on storing cookies on your device to enable basic functionality and enhance your experience.").check(timeout=3000)
                self.logger.log_success("成功接受cookie政策")
            except:
                self.logger.log_warning("未找到cookie政策按钮，可能已经接受或不存在")
                
        except Exception as e:
            self.logger.log_warning(f"接受cookie政策失败: {str(e)}")
    
    @retry_on_element_not_found(max_attempts=3, delay=2.0)
    def _click_login_button(self, page) -> None:
        """点击登录按钮"""
        self.logger.log_step("点击登录按钮")
        
        try:
            # 尝试多种方式找到登录按钮
            login_selectors = [
                'button:has-text("Log in")',
                'button:has-text("Sign up")',
                'button:has-text("Login")',
                'a:has-text("Log in")',
                'a:has-text("Sign up")'
            ]
            
            for selector in login_selectors:
                try:
                    element = page.wait_for_selector(selector, timeout=3000)
                    if element:
                        element.click()
                        self.logger.log_success("成功点击登录按钮")
                        return
                except:
                    continue
            
            # 尝试通过角色查找
            page.get_by_role("button", name="Log in / Sign up").click()
            self.logger.log_success("成功点击登录按钮")
            
        except Exception as e:
            raise FISElementNotFoundException(f"找不到登录按钮: {str(e)}")
    
    @retry_on_element_not_found(max_attempts=3, delay=2.0)
    def _fill_login_form(self, page) -> None:
        """填写登录表单"""
        username = self.config.get('credentials.username')
        password = self.config.get('credentials.password')
        
        self.logger.log_step("填写登录表单", f"用户名: {username}")
        
        try:
            # 等待登录表单出现
            WaitStrategies.wait_for_element_with_strategies(
                page, 
                'input[placeholder*="example.com"]',
                timeout=10
            )
            
            # 填写用户名
            username_input = page.get_by_placeholder("yours@example.com")
            username_input.click()
            username_input.fill(username)
            
            # 填写密码
            password_input = page.get_by_placeholder("your password")
            password_input.click()
            password_input.fill(password)
            
            self.logger.log_success("成功填写登录表单")
            
        except Exception as e:
            raise FISElementNotFoundException(f"填写登录表单失败: {str(e)}")
    
    @retry_on_element_not_found(max_attempts=3, delay=2.0)
    def _submit_login_form(self, page) -> None:
        """提交登录表单"""
        self.logger.log_step("提交登录表单")
        
        try:
            page.get_by_role("button", name="Log In").click()
            self.logger.log_success("成功提交登录表单")
        except Exception as e:
            raise FISElementNotFoundException(f"提交登录表单失败: {str(e)}")
    
    def _wait_for_login_completion(self, page) -> None:
        """等待登录完成"""
        self.logger.log_step("等待登录完成")
        
        try:
            WaitStrategies.smart_wait_for_login(
                page,
                self.config.get('credentials.username'),
                self.config.get('credentials.password')
            )
            self.logger.log_success("登录完成")
        except Exception as e:
            self.logger.log_warning(f"等待登录完成时出现异常: {str(e)}")
    
    def _is_page_fully_loaded(self, page) -> bool:
        """检查页面是否完全加载"""
        try:
            # 检查页面状态
            ready_state = page.evaluate("document.readyState")
            if ready_state != "complete":
                self.logger.debug(f"页面状态: {ready_state}")
                return False
            
            # 检查是否有正在进行的网络请求
            active_requests = page.evaluate("""
                () => {
                    if (window.performance && window.performance.getEntriesByType) {
                        const requests = window.performance.getEntriesByType('resource');
                        const now = Date.now();
                        // 检查是否有最近5秒内的请求
                        return requests.some(req => (now - req.startTime) < 5000);
                    }
                    return false;
                }
            """)
            
            if active_requests:
                self.logger.debug("检测到活跃的网络请求")
                return False
            
            # 检查是否有错误元素
            error_elements = page.query_selector_all('.error, .alert-danger, [class*="error"]')
            if error_elements:
                self.logger.debug(f"检测到 {len(error_elements)} 个错误元素")
                return False
            
            # 检查关键元素是否存在
            key_elements = page.query_selector_all('body, main, [role="main"]')
            if not key_elements:
                self.logger.debug("未找到关键页面元素")
                return False
            
            self.logger.debug("页面完全加载检查通过")
            return True
            
        except Exception as e:
            self.logger.debug(f"页面加载检查失败: {str(e)}")
            return False
    
    def _get_and_save_authorization(self, page, context) -> Dict:
        """获取并保存authorization信息"""
        self.logger.log_step("获取authorization信息")
        
        try:
            # 等待页面完全加载，使用更长的超时时间
            self.logger.log_step("等待页面完全加载...")
            
            # 简化页面加载逻辑，直接进入授权获取流程
            try:
                self.logger.log_step("等待页面基本加载...")
                # 等待DOM加载完成即可，不等待网络完全空闲
                page.wait_for_load_state("domcontentloaded", timeout=5000)
                
                # 额外等待，确保JavaScript执行
                page.wait_for_timeout(5000)
                self.logger.log_success("页面基本加载完成")
                
            except Exception as e:
                self.logger.log_warning(f"页面加载超时，继续执行: {str(e)}")
                # 即使超时也继续执行
                pass
            
            # 优先从特定API请求中获取authorization
            self.logger.log_step("从特定API请求中获取authorization...")
            auth_headers = self._extract_auth_from_specific_api(page, context)
            
            # 如果成功获取到，直接返回
            if auth_headers:
                self.logger.log_success("成功从API请求中获取到authorization")
                # 直接使用获取到的authorization，不进行严格验证
                self._print_authorization_details(auth_headers)
                self._save_authorization_to_file(auth_headers)
                return auth_headers
            
            # 如果未能获取到authorization，返回空字典
            self.logger.log_error("未能从API请求中获取到authorization")
            return {}
                
        except Exception as e:
            self.logger.log_error(f"获取authorization信息失败: {str(e)}")
            # 记录更详细的错误信息
            import traceback
            self.logger.debug(f"详细错误信息: {traceback.format_exc()}")
            return {}
    
    def _extract_auth_from_specific_api(self, page, context) -> Dict:
        """监听特定的API请求并提取authorization参数"""
        try:
            self.logger.log_step("监听特定API请求以获取authorization...")
            
            # 目标API URL
            target_api_url = "https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods"
            
            # 存储捕获到的authorization
            captured_auth = None
            
            def handle_request(request):
                """处理请求事件"""
                nonlocal captured_auth
                
                url = request.url
                headers = request.headers
                
                # 检查是否是目标API
                if target_api_url in url:
                    self.logger.log_success(f"捕获到目标API请求: {url}")
                    
                    # 检查是否有authorization header
                    if 'authorization' in headers:
                        auth_header = headers['authorization']
                        if auth_header.startswith('Bearer '):
                            captured_auth = auth_header
                            self.logger.log_success(f"成功从API请求中获取到authorization: {auth_header[:50]}...")
                            # 打印完整的authorization
                            self.logger.info(f"完整的authorization值: {auth_header}")
                    
                    # 也打印所有的请求头以便调试
                    self.logger.debug(f"请求方法: {request.method}")
                    self.logger.debug(f"请求URL: {url}")
                    self.logger.debug(f"所有请求头: {json.dumps(headers, indent=2)}")
            
            def handle_response(response):
                """处理响应事件"""
                url = response.url
                
                # 检查是否是目标API
                if target_api_url in url:
                    self.logger.log_success(f"捕获到目标API响应: {url}")
                    self.logger.debug(f"响应状态: {response.status}")
            
            # 设置事件监听器
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # 等待页面自动触发API请求
            self.logger.log_step("等待页面触发API请求...")
            page.wait_for_timeout(10000)  # 等待10秒
            
            # 返回结果
            if captured_auth:
                self.logger.log_success("成功从特定API请求中捕获到authorization")
                return {'authorization': captured_auth}
            else:
                self.logger.log_warning("未能从特定API请求中捕获到authorization")
                return {}
                
        except Exception as e:
            self.logger.log_error(f"监听特定API请求失败: {str(e)}")
            return {}
    
    def _validate_authorization_tokens(self, auth_headers: Dict) -> Dict:
        """验证authorization token的有效性"""
        try:
            validated_headers = {}
            
            for key, value in auth_headers.items():
                # 简单验证：只要包含Bearer开头就接受
                if isinstance(value, str) and value.startswith('Bearer '):
                    # 基本验证：检查token长度
                    token = value[7:]  # 移除 "Bearer " 前缀
                    if len(token) > 50:  # JWT token通常很长
                        validated_headers[key] = value
                        self.logger.log_success(f"Token验证通过: {key}")
                    else:
                        self.logger.log_warning(f"Token太短: {key}")
                else:
                    self.logger.log_warning(f"无效的authorization格式: {key}")
            
            return validated_headers
            
        except Exception as e:
            self.logger.log_error(f"验证authorization token失败: {str(e)}")
            return {}
    
    def _extract_session_storage_token(self, page) -> Dict:
        """从sessionStorage中提取token"""
        try:
            # 获取sessionStorage中的所有项目
            storage_items = page.evaluate("""
                () => {
                    const items = {};
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        const value = sessionStorage.getItem(key);
                        items[key] = value;
                    }
                    return items;
                }
            """)
            
            # 查找包含token的键
            for key, value in storage_items.items():
                if any(keyword in key.lower() for keyword in ['token', 'auth', 'bearer', 'access']):
                    try:
                        # 尝试解析JSON
                        data = json.loads(value)
                        if isinstance(data, dict):
                            for sub_key, sub_value in data.items():
                                if 'token' in sub_key.lower() and sub_value:
                                    token = sub_value
                                    if token.startswith('eyJ'):  # JWT token通常以eyJ开头
                                        self.logger.log_success(f"从sessionStorage提取到token: {token[:50]}...")
                                        return {'authorization': f'Bearer {token}'}
                    except:
                        # 如果不是JSON，检查是否直接是token
                        if value and value.startswith('eyJ'):
                            self.logger.log_success(f"从sessionStorage提取到token: {value[:50]}...")
                            return {'authorization': f'Bearer {value}'}
            
            self.logger.log_warning("sessionStorage中未找到token")
            return {}
            
        except Exception as e:
            self.logger.log_error(f"提取sessionStorage token失败: {str(e)}")
            return {}
    
    def _extract_bearer_token_from_content(self, page) -> Dict:
        """从页面内容中搜索Bearer token"""
        try:
            # 获取页面HTML内容
            content = page.content()
            self.logger.debug(f"页面内容长度: {len(content)} 字符")
            
            # 使用正则表达式搜索Bearer token
            import re
            
            # 搜索Bearer token模式
            bearer_patterns = [
                r'Bearer\s+([A-Za-z0-9_-]+\.){2}[A-Za-z0-9_-]+',  # 标准Bearer格式
                r'"authorization":\s*"Bearer\s+([A-Za-z0-9_-]+\.){2}[A-Za-z0-9_-]+"',  # JSON中的authorization
                r"'authorization':\s*'Bearer\s+([A-Za-z0-9_-]+\.){2}[A-Za-z0-9_-]+'",  # 单引号格式
                r'access_token["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]+\.){2}[A-Za-z0-9_-]+',  # access_token字段
                r'token["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]+\.){2}[A-Za-z0-9_-]+',  # token字段
                r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',  # 直接匹配JWT格式
            ]
            
            for i, pattern in enumerate(bearer_patterns):
                matches = re.findall(pattern, content, re.IGNORECASE)
                self.logger.debug(f"模式 {i+1} 匹配到 {len(matches)} 个结果")
                
                if matches:
                    # 取第一个匹配的token
                    token = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    if token and len(token) > 50:  # JWT token通常很长
                        self.logger.log_success(f"从页面内容提取到Bearer token: {token[:50]}...")
                        return {'authorization': f'Bearer {token}'}
            
            # 尝试搜索页面中的JavaScript代码
            try:
                js_content = page.evaluate("""
                    () => {
                        const scripts = document.querySelectorAll('script');
                        let jsContent = '';
                        scripts.forEach(script => {
                            if (script.textContent) {
                                jsContent += script.textContent + '\\n';
                            }
                        });
                        return jsContent;
                    }
                """)
                
                self.logger.debug(f"JavaScript内容长度: {len(js_content)} 字符")
                
                # 在JavaScript内容中搜索token
                for pattern in bearer_patterns:
                    matches = re.findall(pattern, js_content, re.IGNORECASE)
                    if matches:
                        token = matches[0] if isinstance(matches[0], str) else matches[0][0]
                        if token and len(token) > 50:
                            self.logger.log_success(f"从JavaScript内容提取到Bearer token: {token[:50]}...")
                            return {'authorization': f'Bearer {token}'}
                            
            except Exception as e:
                self.logger.debug(f"搜索JavaScript内容失败: {e}")
            
            self.logger.log_warning("页面内容中未找到Bearer token")
            return {}
            
        except Exception as e:
            self.logger.log_error(f"从页面内容提取Bearer token失败: {str(e)}")
            return {}
    
    def _extract_auth_from_network_requests(self, page, context) -> Dict:
        """从网络请求中捕获authorization header"""
        try:
            # 监听网络请求
            requests_with_auth = []
            
            def handle_request(request):
                headers = request.headers
                url = request.url
                
                # 检查是否是FIS相关的API请求
                if any(domain in url for domain in ['livepricing-prod2.azurewebsites.net', 'fis-live.com', 'fisprod2backend']):
                    self.logger.debug(f"捕获到FIS API请求: {url}")
                    
                    if 'authorization' in headers:
                        auth_header = headers['authorization']
                        if auth_header.startswith('Bearer '):
                            requests_with_auth.append(auth_header)
                            self.logger.log_success(f"捕获到API请求中的authorization: {auth_header[:50]}...")
                            self.logger.debug(f"请求URL: {url}")
                            self.logger.debug(f"请求方法: {request.method}")
                
                # 也检查所有请求的authorization header
                elif 'authorization' in headers:
                    auth_header = headers['authorization']
                    if auth_header.startswith('Bearer '):
                        requests_with_auth.append(auth_header)
                        self.logger.log_success(f"捕获到网络请求中的authorization: {auth_header[:50]}...")
            
            def handle_response(response):
                # 检查响应头
                headers = response.headers
                url = response.url
                
                if 'authorization' in headers:
                    auth_header = headers['authorization']
                    if auth_header.startswith('Bearer '):
                        requests_with_auth.append(auth_header)
                        self.logger.log_success(f"捕获到响应中的authorization: {auth_header[:50]}...")
                
                # 检查响应内容中是否包含token
                try:
                    if response.status == 200:
                        content_type = headers.get('content-type', '')
                        if 'application/json' in content_type:
                            response_text = response.text()
                            if response_text and 'token' in response_text.lower():
                                import re
                                token_pattern = r'["\']?token["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]+\.){2}[A-Za-z0-9_-]+'
                                matches = re.findall(token_pattern, response_text, re.IGNORECASE)
                                if matches:
                                    token = matches[0] if isinstance(matches[0], str) else matches[0][0]
                                    if token and len(token) > 50:
                                        requests_with_auth.append(f'Bearer {token}')
                                        self.logger.log_success(f"从响应内容提取到token: {token[:50]}...")
                except:
                    pass
            
            # 设置请求和响应监听
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            # 等待页面完全加载并触发API请求
            self.logger.log_step("等待页面加载并监听API请求...")
            
            # 等待更长时间让API请求发生
            page.wait_for_timeout(10000)
            
            # 尝试触发一些可能触发API请求的操作
            try:
                # 检查页面是否有可以点击的元素来触发API请求
                clickable_elements = page.query_selector_all('button, a, [onclick], [role="button"]')
                if clickable_elements:
                    # 尝试点击第一个可点击元素
                    try:
                        clickable_elements[0].click()
                        self.logger.debug("点击了页面元素以触发API请求")
                        page.wait_for_timeout(3000)
                    except:
                        pass
            except:
                pass
            
            # 再次等待让请求完成
            page.wait_for_timeout(5000)
            
            if requests_with_auth:
                # 返回最后一个authorization header
                self.logger.log_success(f"成功捕获到 {len(requests_with_auth)} 个authorization请求")
                return {'authorization': requests_with_auth[-1]}
            else:
                self.logger.log_warning("未在网络请求中找到authorization header")
                return {}
                
        except Exception as e:
            self.logger.log_error(f"从网络请求提取authorization失败: {str(e)}")
            return {}
    
    def _extract_token_from_js_variables(self, page) -> Dict:
        """从页面JavaScript变量中获取token"""
        try:
            # 尝试从常见的JavaScript变量中获取token
            js_variables = [
                'window.token',
                'window.access_token',
                'window.authToken',
                'window.authorization',
                'window.userToken',
                'window.auth.access_token',
                'window.user.token',
                'window.config.token',
                'localStorage.getItem("token")',
                'localStorage.getItem("access_token")',
                'localStorage.getItem("auth_token")',
                'sessionStorage.getItem("token")',
                'sessionStorage.getItem("access_token")',
            ]
            
            for var_name in js_variables:
                try:
                    value = page.evaluate(f"() => {{ try {{ return {var_name}; }} catch(e) {{ return null; }} }}")
                    if value and isinstance(value, str) and value.startswith('eyJ') and len(value) > 50:
                        self.logger.log_success(f"从JavaScript变量 {var_name} 提取到token: {value[:50]}...")
                        return {'authorization': f'Bearer {value}'}
                except:
                    continue
            
            # 尝试从全局对象中搜索token
            try:
                global_vars = page.evaluate("""
                    () => {
                        const tokens = [];
                        for (let prop in window) {
                            try {
                                const value = window[prop];
                                if (typeof value === 'string' && value.startsWith('eyJ') && value.length > 50) {
                                    tokens.push(value);
                                }
                            } catch(e) {}
                        }
                        return tokens;
                    }
                """)
                
                if global_vars and len(global_vars) > 0:
                    token = global_vars[0]
                    self.logger.log_success(f"从全局变量提取到token: {token[:50]}...")
                    return {'authorization': f'Bearer {token}'}
                    
            except Exception as e:
                self.logger.debug(f"搜索全局变量失败: {e}")
            
            self.logger.log_warning("JavaScript变量中未找到token")
            return {}
            
        except Exception as e:
            self.logger.log_error(f"从JavaScript变量提取token失败: {str(e)}")
            return {}
    
    def _deep_search_all_storages(self, page) -> Dict:
        """深度搜索所有可能的存储位置"""
        try:
            self.logger.log_step("开始深度搜索所有存储位置...")
            
            # 搜索所有可能的存储位置
            all_data = page.evaluate("""
                () => {
                    const results = {
                        localStorage: {},
                        sessionStorage: {},
                        cookies: document.cookie,
                        window_vars: {},
                        global_vars: {},
                        script_tags: []
                    };
                    
                    // 获取localStorage
                    for (let i = 0; i < localStorage.length; i++) {
                        const key = localStorage.key(i);
                        const value = localStorage.getItem(key);
                        results.localStorage[key] = value;
                    }
                    
                    // 获取sessionStorage
                    for (let i = 0; i < sessionStorage.length; i++) {
                        const key = sessionStorage.key(i);
                        const value = sessionStorage.getItem(key);
                        results.sessionStorage[key] = value;
                    }
                    
                    // 获取window对象中的变量
                    for (let prop in window) {
                        try {
                            const value = window[prop];
                            if (typeof value === 'string' && value.length > 10) {
                                results.window_vars[prop] = value;
                            }
                        } catch(e) {}
                    }
                    
                    // 获取所有script标签的内容
                    const scripts = document.querySelectorAll('script');
                    scripts.forEach((script, index) => {
                        if (script.textContent && script.textContent.length > 100) {
                            results.script_tags.push({
                                index: index,
                                content: script.textContent.substring(0, 1000) // 限制长度
                            });
                        }
                    });
                    
                    return results;
                }
            """)
            
            self.logger.debug(f"深度搜索完成，找到 {len(all_data)} 个数据源")
            
            # 搜索localStorage中的token
            for key, value in all_data.get('localStorage', {}).items():
                if self._is_potential_token(value):
                    self.logger.log_success(f"从localStorage深度搜索找到token: {key}")
                    return {'authorization': f'Bearer {value}'}
            
            # 搜索sessionStorage中的token
            for key, value in all_data.get('sessionStorage', {}).items():
                if self._is_potential_token(value):
                    self.logger.log_success(f"从sessionStorage深度搜索找到token: {key}")
                    return {'authorization': f'Bearer {value}'}
            
            # 搜索window变量中的token
            for key, value in all_data.get('window_vars', {}).items():
                if self._is_potential_token(value):
                    self.logger.log_success(f"从window变量深度搜索找到token: {key}")
                    return {'authorization': f'Bearer {value}'}
            
            # 搜索script标签中的token
            for script in all_data.get('script_tags', []):
                if self._search_token_in_text(script['content']):
                    token = self._extract_token_from_text(script['content'])
                    if token:
                        self.logger.log_success(f"从script标签深度搜索找到token")
                        return {'authorization': f'Bearer {token}'}
            
            self.logger.log_warning("深度搜索未找到token")
            return {}
            
        except Exception as e:
            self.logger.log_error(f"深度搜索失败: {str(e)}")
            return {}
    
    def _is_potential_token(self, value: str) -> bool:
        """检查字符串是否可能是token"""
        if not value or not isinstance(value, str):
            return False
        
        # 检查是否是JWT token格式
        if value.startswith('eyJ') and len(value) > 50 and '.' in value:
            parts = value.split('.')
            if len(parts) == 3:
                return True
        
        # 检查是否包含token关键词
        if any(keyword in value.lower() for keyword in ['token', 'bearer', 'auth']) and len(value) > 50:
            return True
        
        return False
    
    def _search_token_in_text(self, text: str) -> bool:
        """在文本中搜索token"""
        if not text:
            return False
        
        import re
        # 搜索JWT token模式
        pattern = r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
        return bool(re.search(pattern, text))
    
    def _extract_token_from_text(self, text: str) -> str:
        """从文本中提取token"""
        if not text:
            return None
        
        import re
        # 提取JWT token
        pattern = r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]
        
        return None
    
    def _trigger_api_requests(self, page, context) -> Dict:
        """主动触发API请求来获取token"""
        try:
            self.logger.log_step("开始主动触发API请求...")
            
            # 监听网络请求
            requests_with_auth = []
            
            def handle_request(request):
                headers = request.headers
                url = request.url
                
                # 检查是否是FIS相关的API请求
                if any(domain in url for domain in ['livepricing-prod2.azurewebsites.net', 'fis-live.com', 'fisprod2backend']):
                    self.logger.debug(f"捕获到FIS API请求: {url}")
                    
                    if 'authorization' in headers:
                        auth_header = headers['authorization']
                        if auth_header.startswith('Bearer '):
                            requests_with_auth.append(auth_header)
                            self.logger.log_success(f"捕获到API请求中的authorization: {auth_header[:50]}...")
                            self.logger.debug(f"请求URL: {url}")
                            self.logger.debug(f"请求方法: {request.method}")
            
            # 设置请求监听
            page.on('request', handle_request)
            
            # 尝试直接调用FIS API来触发authorization请求
            try:
                # 模拟发送API请求
                api_url = "https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods"
                
                # 使用page.evaluate来发送请求
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
                            return { status: response.status, success: true };
                        } catch (error) {
                            return { error: error.message, success: false };
                        }
                    }
                """)
                
                self.logger.debug(f"API请求结果: {result}")
                
            except Exception as e:
                self.logger.debug(f"直接API请求失败: {e}")
            
            # 等待请求完成
            page.wait_for_timeout(5000)
            
            # 尝试触发页面上的各种操作
            try:
                # 查找并点击可能触发API请求的元素
                elements_to_try = [
                    'button',
                    'a[href*="api"]',
                    '[onclick*="api"]',
                    '[data-action*="api"]',
                    '.btn',
                    '.button',
                    '[role="button"]'
                ]
                
                for selector in elements_to_try:
                    try:
                        elements = page.query_selector_all(selector)
                        if elements:
                            # 尝试点击第一个元素
                            elements[0].click()
                            self.logger.debug(f"点击了元素: {selector}")
                            page.wait_for_timeout(2000)
                            break
                    except:
                        continue
                        
            except Exception as e:
                self.logger.debug(f"触发页面操作失败: {e}")
            
            # 再次等待
            page.wait_for_timeout(3000)
            
            if requests_with_auth:
                self.logger.log_success(f"主动触发API请求成功，捕获到 {len(requests_with_auth)} 个authorization请求")
                return {'authorization': requests_with_auth[-1]}
            else:
                self.logger.log_warning("主动触发API请求未捕获到authorization header")
                return {}
                
        except Exception as e:
            self.logger.log_error(f"主动触发API请求失败: {str(e)}")
            return {}
    
    def _validate_authorization_tokens(self, auth_headers: Dict) -> Dict:
        """验证authorization token的有效性"""
        try:
            validated_headers = {}
            
            for key, value in auth_headers.items():
                if isinstance(value, str) and value.startswith('Bearer '):
                    token = value[7:]  # 移除 "Bearer " 前缀
                    
                    # 基本验证：检查token格式
                    if self._is_valid_jwt_token(token):
                        validated_headers[key] = value
                        self.logger.log_success(f"Token验证通过: {key}")
                    else:
                        self.logger.log_warning(f"Token验证失败: {key}")
                else:
                    self.logger.log_warning(f"无效的authorization格式: {key}")
            
            return validated_headers
            
        except Exception as e:
            self.logger.log_error(f"验证authorization token失败: {str(e)}")
            return {}
    
    def _is_valid_jwt_token(self, token: str) -> bool:
        """验证JWT token的基本格式"""
        try:
            if not token or len(token) < 50:
                self.logger.debug(f"Token太短: {len(token) if token else 0}")
                return False
            
            # JWT token通常由三部分组成，用点分隔
            parts = token.split('.')
            if len(parts) != 3:
                self.logger.debug(f"Token部分数量不正确: {len(parts)}")
                return False
            
            # 检查每个部分是否都是base64编码的
            import base64
            for i, part in enumerate(parts):
                try:
                    # 添加必要的填充
                    missing_padding = len(part) % 4
                    if missing_padding:
                        part += '=' * (4 - missing_padding)
                    base64.b64decode(part)
                except Exception as e:
                    self.logger.debug(f"Token第{i+1}部分base64解码失败: {e}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.debug(f"JWT token验证异常: {e}")
            return False
    
    
    def _print_authorization_details(self, auth_info: Dict) -> None:
        """打印authorization详细信息"""
        self.logger.info(f"\n成功获取到 {len(auth_info)} 个authorization信息:")
        self.logger.info("=" * 50)
        
        for i, (key, value) in enumerate(auth_info.items(), 1):
            self.logger.info(f"Authorization {i}:")
            self.logger.info(f"  键名: {key}")
            self.logger.info(f"  值: {value}")
            self.logger.info(f"  类型: {type(value).__name__}")
            self.logger.info(f"  长度: {len(str(value))}")
            self.logger.info("-" * 30)
    
    def _print_cookies_details(self, cookies: List[Dict]) -> None:
        """打印cookies详细信息"""
        self.logger.info(f"\n成功获取到 {len(cookies)} 个cookies:")
        self.logger.info("=" * 50)
        
        for i, cookie in enumerate(cookies, 1):
            self.logger.info(f"Cookie {i}:")
            self.logger.info(f"  名称: {cookie['name']}")
            self.logger.info(f"  值: {cookie['value']}")
            self.logger.info(f"  域名: {cookie['domain']}")
            self.logger.info(f"  路径: {cookie['path']}")
            self.logger.info(f"  过期时间: {cookie.get('expires', '会话cookie')}")
            self.logger.info(f"  安全: {cookie.get('secure', False)}")
            self.logger.info(f"  HttpOnly: {cookie.get('httpOnly', False)}")
            self.logger.info("-" * 30)
    
    def _save_authorization_to_file(self, auth_info: Dict) -> None:
        """保存authorization信息到文件"""
        auth_file = self.config.get('paths.cookies_file').parent / 'fis_authorization.json'
        
        try:
            with open(auth_file, 'w', encoding='utf-8') as f:
                json.dump(auth_info, f, indent=2, ensure_ascii=False)
            self.logger.log_success(f"Authorization信息已保存到文件: {auth_file}")
        except Exception as e:
            self.logger.log_error(f"保存authorization信息到文件失败: {str(e)}")
    
    def _save_cookies_to_file(self, cookies: List[Dict]) -> None:
        """保存cookies到文件"""
        cookies_file = self.config.get('paths.cookies_file')
        
        try:
            with open(cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            self.logger.log_success(f"Cookies已保存到文件: {cookies_file}")
        except Exception as e:
            self.logger.log_error(f"保存cookies到文件失败: {str(e)}")
    
    def _print_auth_cookies(self, cookies: List[Dict]) -> None:
        """打印认证相关的cookies"""
        auth_keywords = ['session', 'auth', 'token', 'login', 'user']
        auth_cookies = [
            cookie for cookie in cookies 
            if any(keyword in cookie['name'].lower() for keyword in auth_keywords)
        ]
        
        if auth_cookies:
            self.logger.info(f"\n找到认证相关的cookies ({len(auth_cookies)}个):")
            for cookie in auth_cookies:
                self.logger.info(f"  {cookie['name']}: {cookie['value']}")
    
    def run(self, playwright: Playwright) -> List[Dict]:
        """执行完整的登录流程"""
        browser = None
        context = None
        page = None
        
        try:
            # 启动浏览器
            browser_config = self.config.get('browser', {})
            browser = playwright.chromium.launch(
                headless=browser_config.get('headless', False)
            )
            
            context = browser.new_context(
                user_agent=browser_config.get('user_agent')
            )
            page = context.new_page()
            
            # 执行登录流程
            self._navigate_to_login_page(page)
            self._accept_cookie_policy(page)
            self._click_login_button(page)
            self._fill_login_form(page)
            self._submit_login_form(page)
            self._wait_for_login_completion(page)
            
            # 获取authorization信息
            auth_info = self._get_and_save_authorization(page, context)
            
            return auth_info
            
        except Exception as e:
            self.logger.log_error(f"登录过程中出现错误: {str(e)}")
            return []
        finally:
            # 清理资源
            try:
                if page:
                    page.close()
            except Exception as e:
                self.logger.debug(f"关闭页面失败: {e}")
            
            try:
                if context:
                    context.close()
            except Exception as e:
                self.logger.debug(f"关闭上下文失败: {e}")
            
            try:
                if browser:
                    browser.close()
            except Exception as e:
                self.logger.debug(f"关闭浏览器失败: {e}")
            
            self.logger.info("浏览器已关闭")


def run(playwright: Playwright) -> Dict:
    """兼容性函数，保持向后兼容"""
    login_manager = FISLoginManager()
    return login_manager.run(playwright)


if __name__ == "__main__":
    with sync_playwright() as playwright:
        auth_info = run(playwright)
        logger.info(f"\n登录完成，共获取到 {len(auth_info)} 个authorization信息")