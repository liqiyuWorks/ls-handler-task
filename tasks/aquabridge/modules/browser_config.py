"""
浏览器配置模块
管理不同环境的浏览器配置
"""
import os
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict


class BrowserType(Enum):
    """浏览器类型枚举"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class Environment(Enum):
    """环境类型枚举"""
    PRODUCTION = "production"
    TESTING = "testing"
    DEVELOPMENT = "development"


@dataclass
class BrowserConfig:
    """浏览器配置"""
    browser_type: BrowserType
    headless: bool
    args: List[str]
    viewport: Dict[str, int]
    ignore_https_errors: bool
    slow_mo: int = 0  # 慢动作模式，用于调试（毫秒）
    
    def __repr__(self):
        return f"BrowserConfig(type={self.browser_type.value}, headless={self.headless})"


# Chromium 浏览器配置（生产环境推荐）
CHROMIUM_CONFIG = BrowserConfig(
    browser_type=BrowserType.CHROMIUM,
    headless=True,
    args=[
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor,TranslateUI',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-extensions',
        '--disable-sync',
        '--disable-translate',
        '--memory-pressure-off'
    ],
    viewport={'width': 1280, 'height': 800},
    ignore_https_errors=True
)

# Firefox 浏览器配置（测试环境推荐）
FIREFOX_CONFIG = BrowserConfig(
    browser_type=BrowserType.FIREFOX,
    headless=True,
    args=[
        '-safe-mode'  # Firefox 安全模式，禁用扩展
    ],
    viewport={'width': 1280, 'height': 800},
    ignore_https_errors=True
)

# WebKit 浏览器配置（Safari 内核，可选）
WEBKIT_CONFIG = BrowserConfig(
    browser_type=BrowserType.WEBKIT,
    headless=True,
    args=[],
    viewport={'width': 1280, 'height': 800},
    ignore_https_errors=True
)

# 环境到浏览器配置的映射
ENVIRONMENT_BROWSER_MAP = {
    Environment.PRODUCTION: CHROMIUM_CONFIG,
    Environment.TESTING: FIREFOX_CONFIG,
    Environment.DEVELOPMENT: CHROMIUM_CONFIG  # 开发环境也使用 Chromium
}


def get_browser_config(
    environment: str = None,
    browser_type: str = None,
    headless: bool = None
) -> BrowserConfig:
    """获取浏览器配置
    
    优先级：
    1. 直接指定 browser_type 参数
    2. 环境变量 BROWSER_TYPE
    3. 根据 environment 参数选择
    4. 环境变量 ENVIRONMENT
    5. 默认使用生产环境配置（Chromium）
    
    Args:
        environment: 环境名称 ("production", "testing", "development")
        browser_type: 浏览器类型 ("chromium", "firefox", "webkit")
        headless: 是否无头模式，None 表示使用配置默认值
    
    Returns:
        BrowserConfig 对象
    """
    # 1. 直接指定 browser_type
    if browser_type:
        browser_type = browser_type.lower()
        if browser_type == "chromium":
            config = CHROMIUM_CONFIG
        elif browser_type == "firefox":
            config = FIREFOX_CONFIG
        elif browser_type == "webkit":
            config = WEBKIT_CONFIG
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
    
    # 2. 检查环境变量 BROWSER_TYPE
    elif os.getenv("BROWSER_TYPE"):
        browser_type = os.getenv("BROWSER_TYPE").lower()
        if browser_type == "chromium":
            config = CHROMIUM_CONFIG
        elif browser_type == "firefox":
            config = FIREFOX_CONFIG
        elif browser_type == "webkit":
            config = WEBKIT_CONFIG
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
    
    # 3. 根据 environment 参数选择
    elif environment:
        env_key = Environment[environment.upper()]
        config = ENVIRONMENT_BROWSER_MAP[env_key]
    
    # 4. 检查环境变量 ENVIRONMENT
    elif os.getenv("ENVIRONMENT"):
        env_name = os.getenv("ENVIRONMENT").upper()
        env_key = Environment[env_name]
        config = ENVIRONMENT_BROWSER_MAP[env_key]
    
    # 5. 默认使用生产环境配置
    else:
        config = CHROMIUM_CONFIG
    
    # 复制配置以避免修改原始配置
    import copy
    config = copy.deepcopy(config)
    
    # 如果指定了 headless 参数，覆盖配置
    if headless is not None:
        config.headless = headless
    
    return config


def list_available_browsers() -> List[str]:
    """列出所有可用的浏览器类型"""
    return [browser.value for browser in BrowserType]


def get_environment_info() -> Dict[str, str]:
    """获取当前环境信息"""
    return {
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
        "BROWSER_TYPE": os.getenv("BROWSER_TYPE", "chromium"),
        "HEADLESS": os.getenv("HEADLESS", "true")
    }


def set_environment(environment: str):
    """设置环境变量（仅在当前进程中有效）"""
    os.environ["ENVIRONMENT"] = environment.lower()


def set_browser_type(browser_type: str):
    """设置浏览器类型环境变量（仅在当前进程中有效）"""
    os.environ["BROWSER_TYPE"] = browser_type.lower()


# 使用示例
if __name__ == "__main__":
    print("=== 浏览器配置示例 ===\n")
    
    # 示例 1: 获取生产环境配置
    print("1. 生产环境配置 (Chromium):")
    config = get_browser_config(environment="production")
    print(f"   {config}")
    print(f"   浏览器: {config.browser_type.value}")
    print(f"   无头模式: {config.headless}\n")
    
    # 示例 2: 获取测试环境配置
    print("2. 测试环境配置 (Firefox):")
    config = get_browser_config(environment="testing")
    print(f"   {config}")
    print(f"   浏览器: {config.browser_type.value}")
    print(f"   无头模式: {config.headless}\n")
    
    # 示例 3: 直接指定浏览器类型
    print("3. 直接指定 Firefox:")
    config = get_browser_config(browser_type="firefox", headless=False)
    print(f"   {config}")
    print(f"   浏览器: {config.browser_type.value}")
    print(f"   无头模式: {config.headless}\n")
    
    # 示例 4: 列出所有可用浏览器
    print("4. 可用浏览器:")
    for browser in list_available_browsers():
        print(f"   - {browser}")
    
    # 示例 5: 环境信息
    print("\n5. 当前环境信息:")
    env_info = get_environment_info()
    for key, value in env_info.items():
        print(f"   {key}: {value}")

