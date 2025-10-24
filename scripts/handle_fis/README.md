# FIS Live Auth0 Token 提取工具

专门用于从FIS Live网站提取Auth0 SPA JS的access_token，用于API调用。

## 核心文件

- `get_fis_cookie.py` - 主登录脚本，提取Auth0 access_token
- `cookie_utils.py` - Authorization管理器
- `config.py` - 配置管理
- `logger.py` - 日志系统
- `exceptions.py` - 异常处理
- `retry.py` - 重试机制
- `wait_strategies.py` - 等待策略

## 主要功能

### 1. Auth0 Token提取
- 自动登录FIS Live网站
- 从localStorage中提取Auth0 SPA JS的access_token
- 格式化为Bearer token格式
- 保存到JSON文件

### 2. Authorization管理
- 加载和保存authorization信息
- 创建带authorization的requests会话
- 测试登录状态
- 获取认证tokens

## 使用方法

### 基本使用

```bash
# 运行登录脚本获取access_token
python3 get_fis_cookie.py
```

### 高级使用

```python
from get_fis_cookie import FISLoginManager
from cookie_utils import FISAuthorizationManager
from playwright.sync_api import sync_playwright

# 使用登录管理器
with sync_playwright() as playwright:
    login_manager = FISLoginManager()
    auth_info = login_manager.run(playwright)
    
    if 'authorization' in auth_info:
        print(f"Access Token: {auth_info['authorization']}")

# 使用Authorization管理器
auth_manager = FISAuthorizationManager()
session = auth_manager.create_requests_session()
response = session.get("https://livepricing-prod2.azurewebsites.net/api/v1/product/1/periods")
```

## 输出文件

- `fis_authorization.json` - 完整的authorization信息
- `logs/fis_login.log` - 登录日志

## 配置

通过环境变量配置：

```bash
export FIS_USERNAME="your_email@example.com"
export FIS_PASSWORD="your_password"
export FIS_HEADLESS="false"
```

## 依赖安装

```bash
pip install playwright requests
playwright install chromium
```

## 注意事项

1. 确保网络连接正常
2. 检查用户名密码是否正确
3. 登录后会自动提取Auth0 access_token
4. Token会保存到JSON文件中供后续使用
