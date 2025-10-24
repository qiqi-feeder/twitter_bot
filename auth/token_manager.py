"""
Twitter Token 管理模块
负责管理和刷新 Twitter API 访问令牌
"""

import time
from typing import Dict, Optional
from utils.config_loader import config_loader
from utils.logger import logger


class TokenManager:
    """Twitter Token 管理器类"""
    
    def __init__(self):
        """初始化 Token 管理器"""
        self.twitter_config = config_loader.get_twitter_config()
        self._access_token = None
        self._access_token_secret = None
        self._token_expires_at = None
        self._load_tokens()
    
    def _load_tokens(self):
        """从配置文件加载令牌"""
        self._access_token = self.twitter_config.get('access_token')
        self._access_token_secret = self.twitter_config.get('access_token_secret')
        
        if not self._access_token or not self._access_token_secret:
            logger.warning("Twitter 访问令牌未配置")
        else:
            logger.info("Twitter 访问令牌已加载")
    
    def get_access_token(self) -> Optional[str]:
        """
        获取访问令牌
        
        Returns:
            访问令牌字符串
        """
        if self._is_token_expired():
            logger.info("访问令牌已过期，尝试刷新")
            self._refresh_token()
        
        return self._access_token
    
    def get_access_token_secret(self) -> Optional[str]:
        """
        获取访问令牌密钥
        
        Returns:
            访问令牌密钥字符串
        """
        return self._access_token_secret
    
    def get_consumer_credentials(self) -> Dict[str, str]:
        """
        获取消费者凭据
        
        Returns:
            包含 consumer_key 和 consumer_secret 的字典
        """
        return {
            'consumer_key': self.twitter_config.get('consumer_key', ''),
            'consumer_secret': self.twitter_config.get('consumer_secret', '')
        }
    
    def get_bearer_token(self) -> Optional[str]:
        """
        获取 Bearer Token
        
        Returns:
            Bearer Token 字符串
        """
        return self.twitter_config.get('bearer_token')
    
    def _is_token_expired(self) -> bool:
        """
        检查令牌是否过期
        
        Returns:
            令牌是否过期
        """
        if not self._token_expires_at:
            # 如果没有过期时间信息，假设令牌有效
            return False
        
        return time.time() >= self._token_expires_at
    
    def _refresh_token(self) -> bool:
        """
        刷新访问令牌
        
        注意：Twitter API v2 的访问令牌通常是长期有效的，
        这里主要是为了扩展性，实际实现可能需要根据具体需求调整
        
        Returns:
            刷新是否成功
        """
        try:
            # 对于 Twitter API v2，访问令牌通常是长期有效的
            # 这里可以实现令牌刷新逻辑，如果需要的话
            logger.info("Twitter API v2 访问令牌通常是长期有效的，无需刷新")
            return True
            
        except Exception as e:
            logger.error(f"刷新访问令牌失败: {e}")
            return False
    
    def validate_credentials(self) -> bool:
        """
        验证凭据是否完整
        
        Returns:
            凭据是否完整有效
        """
        required_fields = [
            'consumer_key',
            'consumer_secret',
            'access_token',
            'access_token_secret'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not self.twitter_config.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"缺少必要的 Twitter 凭据: {', '.join(missing_fields)}")
            return False
        
        logger.info("Twitter 凭据验证通过")
        return True
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        获取认证头部信息
        
        Returns:
            包含认证信息的头部字典
        """
        bearer_token = self.get_bearer_token()
        if bearer_token:
            return {
                'Authorization': f'Bearer {bearer_token}',
                'Content-Type': 'application/json'
            }
        else:
            logger.warning("Bearer Token 未配置")
            return {}


# 全局 Token 管理器实例
token_manager = TokenManager()
