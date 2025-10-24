"""
日志管理模块
提供统一的日志记录功能
"""

import logging
import os
from typing import Optional
from utils.config_loader import config_loader


class Logger:
    """日志管理器类"""
    
    def __init__(self, name: str = "twitter_bot"):
        """
        初始化日志管理器
        
        Args:
            name: 日志记录器名称
        """
        self.name = name
        self.logger = None
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 获取日志配置
        log_config = config_loader.get_logging_config()
        
        # 创建日志记录器
        self.logger = logging.getLogger(self.name)
        
        # 设置日志级别
        level = log_config.get('level', 'INFO')
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # 避免重复添加处理器
        if self.logger.handlers:
            return
        
        # 日志格式
        formatter = logging.Formatter(
            log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # 文件处理器
        file_path = log_config.get('file_path', 'logs/twitter_bot.log')
        if file_path:
            # 确保日志目录存在
            log_dir = os.path.dirname(file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # 控制台处理器
        if log_config.get('console_output', True):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试信息"""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录一般信息"""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告信息"""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录错误信息"""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录严重错误信息"""
        self.logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(message, *args, **kwargs)


# 全局日志记录器实例
logger = Logger()
