"""
Twitter OAuth 2.0 客户端模块
提供完整的 OAuth 2.0 认证流程支持
"""

import base64
import hashlib
import secrets
import requests
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, parse_qs, urlparse
from utils.logger import logger


class OAuth2Client:
    """Twitter OAuth 2.0 客户端"""
    
    # Twitter OAuth 2.0 端点
    AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    REVOKE_URL = "https://api.twitter.com/2/oauth2/revoke"
    
    def __init__(self, client_id: str, client_secret: Optional[str] = None, 
                 redirect_uri: str = "http://localhost:8080/callback",
                 proxies: Optional[Dict[str, str]] = None):
        """
        初始化 OAuth 2.0 客户端
        
        Args:
            client_id: Twitter 应用的 Client ID
            client_secret: Twitter 应用的 Client Secret（可选，用于机密客户端）
            redirect_uri: 回调 URI
            proxies: 代理配置
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.proxies = proxies
        
        # OAuth 2.0 PKCE 参数
        self.code_verifier = None
        self.code_challenge = None
        self.state = None
    
    def _generate_pkce_params(self) -> Tuple[str, str]:
        """
        生成 PKCE (Proof Key for Code Exchange) 参数
        
        Returns:
            (code_verifier, code_challenge) 元组
        """
        # 生成 code_verifier (43-128 个字符)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        code_verifier = code_verifier.rstrip('=')
        
        # 生成 code_challenge (SHA256 哈希)
        code_challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(code_challenge_bytes).decode('utf-8')
        code_challenge = code_challenge.rstrip('=')
        
        return code_verifier, code_challenge
    
    def get_authorization_url(self, scopes: list = None) -> str:
        """
        获取授权 URL
        
        Args:
            scopes: 请求的权限范围列表，默认为 ['tweet.read', 'tweet.write', 'users.read']
            
        Returns:
            授权 URL
        """
        if scopes is None:
            scopes = ['tweet.read', 'tweet.write', 'users.read', 'offline.access']
        
        # 生成 PKCE 参数
        self.code_verifier, self.code_challenge = self._generate_pkce_params()
        
        # 生成 state 参数（防止 CSRF 攻击）
        self.state = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        
        # 构建授权 URL 参数
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(scopes),
            'state': self.state,
            'code_challenge': self.code_challenge,
            'code_challenge_method': 'S256'
        }
        
        authorization_url = f"{self.AUTHORIZE_URL}?{urlencode(params)}"
        
        logger.info("授权 URL 已生成")
        logger.debug(f"State: {self.state}")
        logger.debug(f"Code Challenge: {self.code_challenge}")
        
        return authorization_url
    
    def exchange_code_for_token(self, authorization_code: str) -> Optional[Dict]:
        """
        使用授权码交换访问令牌
        
        Args:
            authorization_code: 从回调 URL 中获取的授权码
            
        Returns:
            包含 access_token, refresh_token 等信息的字典
        """
        if not self.code_verifier:
            logger.error("code_verifier 未设置，请先调用 get_authorization_url()")
            return None
        
        try:
            # 准备请求数据
            data = {
                'grant_type': 'authorization_code',
                'code': authorization_code,
                'redirect_uri': self.redirect_uri,
                'code_verifier': self.code_verifier,
            }
            
            # 准备请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # 如果有 client_secret，使用 Basic Auth
            if self.client_secret:
                auth_string = f"{self.client_id}:{self.client_secret}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                headers['Authorization'] = f'Basic {auth_b64}'
            else:
                # 公共客户端，将 client_id 放在请求体中
                data['client_id'] = self.client_id
            
            logger.info("正在交换授权码获取访问令牌...")
            
            # 发送请求
            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers=headers,
                proxies=self.proxies,
                timeout=30
            )
            
            if response.status_code == 200:
                token_data = response.json()
                logger.info("成功获取访问令牌")
                logger.debug(f"Token 类型: {token_data.get('token_type')}")
                logger.debug(f"过期时间: {token_data.get('expires_in')} 秒")
                return token_data
            else:
                logger.error(f"交换授权码失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"交换授权码时发生错误: {e}", exc_info=True)
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """
        使用 refresh_token 刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新的 access_token 和 refresh_token 的字典
        """
        try:
            # 准备请求数据
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            }

            # 准备请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # 如果有 client_secret，使用 Basic Auth
            if self.client_secret:
                auth_string = f"{self.client_id}:{self.client_secret}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                headers['Authorization'] = f'Basic {auth_b64}'
            else:
                # 公共客户端，将 client_id 放在请求体中
                data['client_id'] = self.client_id

            logger.info("正在刷新访问令牌...")

            # 发送请求
            response = requests.post(
                self.TOKEN_URL,
                data=data,
                headers=headers,
                proxies=self.proxies,
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                logger.info("访问令牌刷新成功")
                logger.debug(f"新 Token 过期时间: {token_data.get('expires_in')} 秒")
                return token_data
            else:
                logger.error(f"刷新访问令牌失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return None

        except Exception as e:
            logger.error(f"刷新访问令牌时发生错误: {e}", exc_info=True)
            return None

    def revoke_token(self, token: str, token_type_hint: str = 'access_token') -> bool:
        """
        撤销访问令牌或刷新令牌

        Args:
            token: 要撤销的令牌
            token_type_hint: 令牌类型提示 ('access_token' 或 'refresh_token')

        Returns:
            撤销是否成功
        """
        try:
            # 准备请求数据
            data = {
                'token': token,
                'token_type_hint': token_type_hint
            }

            # 准备请求头
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            # 如果有 client_secret，使用 Basic Auth
            if self.client_secret:
                auth_string = f"{self.client_id}:{self.client_secret}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                headers['Authorization'] = f'Basic {auth_b64}'
            else:
                # 公共客户端，将 client_id 放在请求体中
                data['client_id'] = self.client_id

            logger.info(f"正在撤销 {token_type_hint}...")

            # 发送请求
            response = requests.post(
                self.REVOKE_URL,
                data=data,
                headers=headers,
                proxies=self.proxies,
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"{token_type_hint} 撤销成功")
                return True
            else:
                logger.error(f"撤销令牌失败，状态码: {response.status_code}")
                logger.error(f"响应内容: {response.text}")
                return False

        except Exception as e:
            logger.error(f"撤销令牌时发生错误: {e}", exc_info=True)
            return False

    @staticmethod
    def parse_callback_url(callback_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        解析回调 URL，提取授权码和 state

        Args:
            callback_url: 完整的回调 URL

        Returns:
            (authorization_code, state, error) 元组
        """
        try:
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)

            code = params.get('code', [None])[0]
            state = params.get('state', [None])[0]
            error = params.get('error', [None])[0]

            if error:
                logger.error(f"授权回调包含错误: {error}")
                error_description = params.get('error_description', [''])[0]
                if error_description:
                    logger.error(f"错误描述: {error_description}")

            return code, state, error

        except Exception as e:
            logger.error(f"解析回调 URL 时发生错误: {e}")
            return None, None, str(e)

    def verify_state(self, received_state: str) -> bool:
        """
        验证 state 参数（防止 CSRF 攻击）

        Args:
            received_state: 从回调 URL 中接收到的 state

        Returns:
            state 是否匹配
        """
        if not self.state:
            logger.warning("本地 state 未设置，无法验证")
            return False

        if received_state == self.state:
            logger.info("State 验证通过")
            return True
        else:
            logger.error("State 验证失败，可能存在 CSRF 攻击")
            return False

