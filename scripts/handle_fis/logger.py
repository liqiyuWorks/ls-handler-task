"""
日志记录系统
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from config import config


class FISLogger:
    """FIS Live 专用日志记录器"""
    
    def __init__(self, name: str = 'FIS_LOGIN'):
        """
        初始化日志记录器
        
        Args:
            name: 日志记录器名称
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.get('logging.level', 'INFO')))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """设置日志处理器"""
        formatter = logging.Formatter(
            config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件处理器
        log_file = config.get('logging.file')
        if log_file:
            # 确保日志目录存在
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)
    
    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """记录严重错误日志"""
        self.logger.critical(message)
    
    def log_step(self, step: str, details: Optional[str] = None):
        """记录步骤日志"""
        message = f"步骤: {step}"
        if details:
            message += f" - {details}"
        self.info(message)
    
    def log_success(self, message: str):
        """记录成功日志"""
        self.info(f"✅ 成功: {message}")
    
    def log_error(self, message: str, exception: Optional[Exception] = None):
        """记录错误日志"""
        error_msg = f"❌ 错误: {message}"
        if exception:
            error_msg += f" - {str(exception)}"
        self.error(error_msg)
    
    def log_warning(self, message: str):
        """记录警告日志"""
        self.warning(f"⚠️ 警告: {message}")


# 全局日志记录器实例
logger = FISLogger()
