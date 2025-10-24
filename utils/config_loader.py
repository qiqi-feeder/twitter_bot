"""
配置文件加载器
负责读取和解析 YAML 配置文件
"""

import yaml
import os
from typing import Dict, Any


class ConfigLoader:
    """配置文件加载器类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
            
        Raises:
            FileNotFoundError: 配置文件不存在
            yaml.YAMLError: YAML 格式错误
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
                return self._config
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"配置文件格式错误: {e}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取配置，如果未加载则先加载
        
        Returns:
            配置字典
        """
        if self._config is None:
            self.load_config()
        return self._config
    
    def get_twitter_config(self) -> Dict[str, str]:
        """获取 Twitter 配置"""
        config = self.get_config()
        return config.get('twitter', {})
    
    def get_openai_config(self) -> Dict[str, str]:
        """获取 OpenAI 配置"""
        config = self.get_config()
        return config.get('openai', {})
    
    def get_proxy_config(self) -> Dict[str, Any]:
        """获取代理配置"""
        config = self.get_config()
        return config.get('proxy', {})
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """获取调度器配置"""
        config = self.get_config()
        return config.get('scheduler', {})
    
    def get_flask_config(self) -> Dict[str, Any]:
        """获取 Flask 配置"""
        config = self.get_config()
        return config.get('flask', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        config = self.get_config()
        return config.get('logging', {})


# 全局配置加载器实例
config_loader = ConfigLoader()
