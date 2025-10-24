"""
FIS Live 模拟登录配置文件
"""

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """配置管理类"""
    
    def __init__(self):
        """初始化配置"""
        self.base_dir = Path(__file__).parent
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        return {
            # 网站配置
            'website': {
                'base_url': 'https://www.fis-live.com',
                'login_url': 'https://www.fis-live.com/markets/dry-ffa',
                'login_endpoint': '/api/login',  # 如果需要的话
            },
            
            # 登录凭据 - 从环境变量读取，避免硬编码
            'credentials': {
                'username': os.getenv('FIS_USERNAME', 'terry@aquabridge.ai'),
                'password': os.getenv('FIS_PASSWORD', 'Abs,88000'),
            },
            
            # 浏览器配置
            'browser': {
                'headless': os.getenv('FIS_HEADLESS', 'False').lower() == 'true',
                'timeout': int(os.getenv('FIS_TIMEOUT', '30000')),  # 30秒
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
            
            # 文件路径配置
            'paths': {
                'cookies_file': self.base_dir / 'fis_cookies.json',
                'logs_dir': self.base_dir / 'logs',
                'screenshots_dir': self.base_dir / 'screenshots',
            },
            
            # 等待配置
            'wait': {
                'page_load': int(os.getenv('FIS_PAGE_LOAD_WAIT', '5')),  # 5秒
                'login_wait': int(os.getenv('FIS_LOGIN_WAIT', '3')),  # 3秒
                'element_timeout': int(os.getenv('FIS_ELEMENT_TIMEOUT', '10')),  # 10秒
            },
            
            # 重试配置
            'retry': {
                'max_attempts': int(os.getenv('FIS_MAX_RETRIES', '3')),
                'retry_delay': int(os.getenv('FIS_RETRY_DELAY', '5')),  # 5秒
            },
            
            # 日志配置
            'logging': {
                'level': os.getenv('FIS_LOG_LEVEL', 'INFO'),
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': self.base_dir / 'logs' / 'fis_login.log',
            },
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，如 'website.base_url'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def create_directories(self):
        """创建必要的目录"""
        dirs_to_create = [
            self.get('paths.logs_dir'),
            self.get('paths.screenshots_dir'),
        ]
        
        for directory in dirs_to_create:
            if directory and not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                print(f"创建目录: {directory}")


# 全局配置实例
config = Config()
