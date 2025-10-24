import json
import requests
from typing import Dict, List, Optional
from pathlib import Path
from config import config
from logger import logger


class FISAuthorizationManager:
    """FIS Live网站的Authorization管理工具"""
    
    def __init__(self, auth_file_path: str = None):
        """
        初始化Authorization管理器
        
        Args:
            auth_file_path: Authorization文件路径，默认为配置文件中指定的路径
        """
        self.auth_file_path = auth_file_path or config.get('paths.cookies_file').parent / 'fis_authorization.json'
        self.authorization = self.load_authorization()
    
    def load_authorization(self) -> Dict:
        """从文件加载authorization信息"""
        try:
            with open(self.auth_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Authorization文件不存在: {self.auth_file_path}")
            return {}
        except Exception as e:
            logger.error(f"加载Authorization文件时出错: {e}")
            return {}
    
    def save_authorization(self, auth_info: Dict) -> None:
        """保存authorization信息到文件"""
        try:
            with open(self.auth_file_path, 'w', encoding='utf-8') as f:
                json.dump(auth_info, f, indent=2, ensure_ascii=False)
            logger.log_success(f"Authorization信息已保存到: {self.auth_file_path}")
        except Exception as e:
            logger.log_error(f"保存Authorization文件时出错: {e}")
    
    def get_authorization_headers(self) -> Dict[str, str]:
        """获取authorization请求头格式，用于requests库"""
        headers = {}
        for key, value in self.authorization.items():
            if 'authorization' in key.lower() or 'bearer' in key.lower():
                headers[key] = value
            elif 'token' in key.lower() or 'auth' in key.lower():
                headers['Authorization'] = f"Bearer {value}"
        return headers
    
    def get_auth_tokens(self) -> Dict[str, str]:
        """获取认证相关的tokens"""
        auth_tokens = {}
        for key, value in self.authorization.items():
            if any(keyword in key.lower() for keyword in ['token', 'auth', 'session', 'jwt', 'bearer']):
                auth_tokens[key] = value
        return auth_tokens
    
    def get_authorization_by_key(self, key: str) -> Optional[str]:
        """根据键名获取特定的authorization值"""
        return self.authorization.get(key)
    
    def print_authorization_summary(self) -> None:
        """打印authorization摘要信息"""
        if not self.authorization:
            logger.warning("没有可用的authorization信息")
            return
        
        logger.info(f"总共 {len(self.authorization)} 个authorization信息:")
        logger.info("=" * 50)
        
        for i, (key, value) in enumerate(self.authorization.items(), 1):
            logger.info(f"{i}. {key}: {str(value)[:50]}...")
        
        # 显示认证相关的tokens
        auth_tokens = self.get_auth_tokens()
        if auth_tokens:
            logger.info(f"\n认证相关tokens ({len(auth_tokens)}个):")
            for key in auth_tokens:
                logger.info(f"  - {key}")
    
    def create_requests_session(self) -> requests.Session:
        """创建一个配置了authorization的requests会话"""
        session = requests.Session()
        
        # 设置authorization请求头
        auth_headers = self.get_authorization_headers()
        session.headers.update(auth_headers)
        
        # 设置通用请求头
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def test_login_status(self) -> bool:
        """测试登录状态"""
        if not self.authorization:
            logger.warning("没有可用的authorization信息")
            return False
        
        try:
            session = self.create_requests_session()
            response = session.get("https://www.fis-live.com/markets/dry-ffa", timeout=10)
            
            # 检查是否成功访问需要登录的页面
            if response.status_code == 200:
                # 简单的检查：如果页面包含登录按钮，说明未登录
                if 'Log in / Sign up' in response.text:
                    logger.warning("登录状态: 未登录")
                    return False
                else:
                    logger.log_success("登录状态: 已登录")
                    return True
            else:
                logger.log_error(f"访问失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            logger.log_error(f"测试登录状态时出错: {e}")
            return False


def main():
    """主函数，演示如何使用Authorization管理器"""
    auth_manager = FISAuthorizationManager()
    
    logger.info("=== FIS Live Authorization 管理器 ===")
    auth_manager.print_authorization_summary()
    
    logger.info("\n=== 测试登录状态 ===")
    auth_manager.test_login_status()


if __name__ == "__main__":
    main()
