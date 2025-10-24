"""
代理管理模块
提供 SOCKS5 代理配置和管理功能
"""

import requests
from typing import Dict, Optional
from utils.config_loader import config_loader
from utils.logger import logger


class ProxyManager:
    """代理管理器类"""
    
    def __init__(self):
        """初始化代理管理器"""
        self.proxy_config = config_loader.get_proxy_config()
        self.proxies = self._setup_proxies()
    
    def _setup_proxies(self) -> Optional[Dict[str, str]]:
        """
        设置代理配置
        
        Returns:
            代理配置字典，如果未启用代理则返回 None
        """
        if not self.proxy_config.get('enabled', False):
            logger.info("代理未启用")
            return None
        
        socks5_url = self.proxy_config.get('socks5_url')
        if not socks5_url:
            logger.warning("代理已启用但未配置 SOCKS5 URL")
            return None
        
        # 构建代理配置
        proxies = {
            'http': socks5_url,
            'https': socks5_url
        }
        
        logger.info(f"代理已配置: {socks5_url}")
        return proxies
    
    def get_proxies(self) -> Optional[Dict[str, str]]:
        """
        获取代理配置
        
        Returns:
            代理配置字典，如果未启用代理则返回 None
        """
        return self.proxies
    
    def test_proxy(self) -> bool:
        """
        测试代理连接
        
        Returns:
            代理是否可用
        """
        if not self.proxies:
            logger.info("未配置代理，跳过代理测试")
            return True
        
        try:
            # 使用代理访问一个测试 URL
            test_url = "https://httpbin.org/ip"
            response = requests.get(
                test_url,
                proxies=self.proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("代理连接测试成功")
                logger.debug(f"代理 IP 信息: {response.json()}")
                return True
            else:
                logger.error(f"代理连接测试失败，状态码: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"代理连接测试失败: {e}")
            return False
    
    def get_session(self) -> requests.Session:
        """
        获取配置了代理的 requests 会话
        
        Returns:
            配置了代理的 requests.Session 对象
        """
        session = requests.Session()
        
        if self.proxies:
            session.proxies.update(self.proxies)
            logger.debug("已为会话配置代理")
        
        return session
    
    def is_proxy_enabled(self) -> bool:
        """
        检查代理是否启用
        
        Returns:
            代理是否启用
        """
        return self.proxies is not None


# 全局代理管理器实例
proxy_manager = ProxyManager()
