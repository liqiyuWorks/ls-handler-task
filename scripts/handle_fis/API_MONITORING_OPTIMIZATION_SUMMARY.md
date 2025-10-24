# FIS API 监听优化总结

## 基于curl请求的优化

基于你提供的curl请求信息，我们对FIS Live网站的authorization提取功能进行了针对性优化：

```bash
curl 'https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods' \
  -H 'Accept: */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Connection: keep-alive' \
  -H 'Origin: https://www.fis-live.com' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: cross-site' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' \
  -H 'authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6IkVEejFQRlh5VnRGOUdkOWtaR04zSyJ9.eyJodHRwczovL2Zpcy1saXZlL2VtYWlsIjoidGVycnlAYXF1YWJyaWRnZS5haSIsImh0dHBzOi8vZmlzLWxpdmUvYWNjZXNzTGV2ZWwiOjEwLCJodHRwczovL2Zpcy1saXZlL2FjY2VwdFRlcm1zIjp0cnVlLCJpc3MiOiJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJhdXRoMHw2ODA5ZTViZDliY2JkOTI0ZTMwZTEwMzkiLCJhdWQiOlsiaHR0cHM6Ly9maXNwcm9kMmJhY2tlbmQiLCJodHRwczovL2Zpcy1saXZlLmV1LmF1dGgwLmNvbS91c2VyaW5mbyJdLCJpYXQiOjE3NjEyMDgxMzgsImV4cCI6MTc2MTI5NDUzOCwic2NvcGUiOiJvcGVuaWQgcHJvZmlsZSBlbWFpbCIsImF6cCI6InJ1MlluQTN4N0dwVThja29iZ1dSWWxlZHJoNm1YTEVDIn0.lTr6pVjJkkHg7JViLFIm_JVRmN70EbH8pVeRK2sexQCjC8b8oWxugqMZY1YwyJpImsKfZ8z2gMAeqWFR2pB4WNlFh-1FnDg57at1S6F5jNVsHe98pUYCGKsdgJdpN2Sf-6kD2doAueR7c9EQilGdUlke05SLlxyfULRE3m0lP-97zrnepGmfQvNSdf5NTQDRp0e9R883QMN4t0AJE25jXQEfo6FeHKA_Aj2vQ5pvaFOYhm8oVZHd0ESH66MlILAhuUW6Jnn6of20GZ6K8xi7nh_iwPeiuWI7cjI-R_sW8cHNoXMVuuB0CHWfHUWuwy3PWGQ_0BTL-Cca3QAZ4gHI_w' \
  -H 'content-type: application/json' \
  -H 'sec-ch-ua: "Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"'
```

## 关键优化内容

### 1. API端点监控

我们添加了对特定FIS API端点的监控：

- `livepricing-prod2.azurewebsites.net` - 主要的API端点
- `fis-live.com` - 主网站域名
- `fisprod2backend` - 后端服务

### 2. 网络请求监听优化

#### 增强的请求监听器
```python
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
```

### 3. 主动API请求触发

#### 直接API调用
```python
def _trigger_api_requests(self, page, context) -> Dict:
    """主动触发API请求来获取token"""
    
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
```

### 4. 页面操作触发

#### 智能元素点击
```python
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
```

## 提取方法优先级

现在我们有7种提取方法，按优先级排序：

1. **localStorage提取** - 从localStorage获取Auth0 token
2. **sessionStorage提取** - 从sessionStorage获取token
3. **页面内容搜索** - 从HTML内容中搜索Bearer token
4. **网络请求监听** - 监听API请求中的authorization header
5. **JavaScript变量提取** - 从页面JavaScript变量中获取token
6. **深度搜索** - 综合搜索所有可能的存储位置
7. **主动API触发** - 主动触发API请求来获取token

## 关键特性

### 1. 智能API识别
- 自动识别FIS相关的API请求
- 专门监听包含authorization header的请求
- 记录详细的请求信息用于调试

### 2. 主动触发机制
- 直接调用FIS API端点
- 模拟真实的浏览器请求
- 触发页面操作来生成API请求

### 3. 完整的请求头模拟
- 使用与curl请求相同的请求头
- 包含正确的Origin、User-Agent等头信息
- 支持CORS和跨域请求

### 4. 详细的日志记录
- 记录所有捕获到的API请求
- 显示请求URL、方法和状态
- 提供完整的调试信息

## 使用方法

### 基本使用
```python
from get_fis_cookie import FISLoginManager
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    login_manager = FISLoginManager()
    auth_info = login_manager.run(playwright)
    
    if auth_info:
        print("成功获取到authorization信息:")
        for key, value in auth_info.items():
            print(f"{key}: {value}")
```

### 测试脚本
我们提供了专门的测试脚本：
- `test_api_monitoring.py` - 测试API请求监听功能
- `test_authorization_extraction.py` - 完整的authorization提取测试

## 预期效果

基于你提供的curl请求信息，这个优化版本应该能够：

1. **捕获API请求** - 监听登录后页面发送的API请求
2. **提取Bearer Token** - 从请求头中提取authorization信息
3. **主动触发请求** - 主动调用API来获取token
4. **智能识别** - 自动识别FIS相关的API端点

## 下一步建议

1. **实际测试** - 在真实的FIS网站上测试这些功能
2. **调试优化** - 根据实际运行结果调整监听策略
3. **扩展支持** - 添加对其他API端点的支持
4. **性能优化** - 优化请求监听和处理的性能

## 总结

我们已经基于你提供的curl请求信息，实现了全面的API监听和authorization提取优化。这个版本专门针对FIS Live网站的API调用模式进行了优化，应该能够成功捕获到类似你提供的Bearer token格式的authorization信息。
