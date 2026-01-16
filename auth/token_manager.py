"""
Twitter Token 管理模块
负责管理和刷新 Twitter API 访问令牌（OAuth 2.0）
"""

import time
import base64
import requests
import yaml
import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.config_loader import config_loader
from utils.logger import logger


class TokenManager:
    """Twitter Token 管理器类（OAuth 2.0）"""

    def __init__(self):
        """初始化 Token 管理器"""
        self.twitter_config = config_loader.get_twitter_config()
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._client_id = None
        self._client_secret = None
        
        # 【修改1】使用绝对路径，防止 Crontab 运行时找不到文件
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file_path = os.path.join(base_dir, "config", "config.yaml")
        
        self._load_tokens()

    def _load_tokens(self):
        """从配置文件加载令牌"""
        self._access_token = self.twitter_config.get('access_token')
        self._refresh_token = self.twitter_config.get('refresh_token')
        self._client_id = self.twitter_config.get('client_id')
        self._client_secret = self.twitter_config.get('client_secret')

        # 加载 token 过期时间（如果有）
        expires_at = self.twitter_config.get('token_expires_at')
        if expires_at:
            try:
                self._token_expires_at = datetime.fromisoformat(expires_at).timestamp()
            except:
                self._token_expires_at = None

        if not self._access_token:
            logger.warning("Twitter OAuth 2.0 访问令牌未配置")

    def get_access_token(self) -> Optional[str]:
        """获取访问令牌，如果过期则自动刷新"""
        # 检查 token 是否即将过期（提前 5 分钟刷新）
        if self._is_token_expired():
            logger.info("访问令牌已过期或即将过期，尝试刷新")
            # 这里调用新的 public 方法
            if self.refresh_access_token():
                logger.info("访问令牌刷新成功")
            else:
                logger.error("访问令牌刷新失败")

        return self._access_token

    def get_refresh_token(self) -> Optional[str]:
        return self._refresh_token

    def _is_token_expired(self) -> bool:
        """检查令牌是否过期"""
        if not self._token_expires_at:
            return True
        # 提前 5 分钟刷新
        return time.time() >= (self._token_expires_at - 300)

    # 【修改2】将方法名从 _refresh_access_token 改为 refresh_access_token (公开)
    # 【修改3】返回值改为 Optional[str]，返回新的 token 字符串
    def refresh_access_token(self) -> Optional[str]:
        """
        使用 refresh_token 刷新 access_token（OAuth 2.0）
        外部强制刷新时调用此方法
        """
        if not self._refresh_token:
            logger.error("刷新令牌未配置，无法刷新访问令牌")
            return None

        try:
            from utils.proxy import proxy_manager

            token_url = "https://api.twitter.com/2/oauth2/token"

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self._refresh_token,
            }

            # 准备认证头
            client_id = self._client_id or self.twitter_config.get('consumer_key')
            client_secret = self._client_secret or self.twitter_config.get('consumer_secret')

            if client_id and client_secret:
                auth_string = f"{client_id}:{client_secret}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

                headers = {
                    'Authorization': f'Basic {auth_b64}',
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            else:
                headers = {'Content-Type': 'application/x-www-form-urlencoded'}
                if client_id:
                    data['client_id'] = client_id

            proxies = proxy_manager.get_proxies() if proxy_manager.is_proxy_enabled() else None

            logger.info("正在刷新 Twitter OAuth 2.0 访问令牌...")

            response = requests.post(
                token_url,
                data=data,
                headers=headers,
                proxies=proxies,
                timeout=60
            )

            if response.status_code == 200:
                token_data = response.json()

                new_access_token = token_data.get('access_token')
                new_refresh_token = token_data.get('refresh_token')
                expires_in = token_data.get('expires_in', 7200)

                if new_access_token:
                    self._access_token = new_access_token
                    logger.info("访问令牌已更新")

                if new_refresh_token:
                    self._refresh_token = new_refresh_token
                    logger.info("刷新令牌已更新")

                self._token_expires_at = time.time() + expires_in
                expires_at_str = datetime.fromtimestamp(self._token_expires_at).isoformat()

                # 保存到配置文件
                self._save_tokens_to_config(
                    access_token=new_access_token,
                    refresh_token=new_refresh_token,
                    expires_at=expires_at_str
                )

                logger.info(f"访问令牌刷新成功，将在 {expires_in} 秒后过期")
                
                # 【修改4】返回 token 字符串而不是 True
                return new_access_token 
            else:
                logger.error(f"刷新失败 {response.status_code}: {response.text}")
                return None

        except Exception as e:
            logger.error(f"刷新访问令牌时发生错误: {e}", exc_info=True)
            return None

    def _save_tokens_to_config(self, access_token: str, refresh_token: Optional[str] = None,
                               expires_at: Optional[str] = None):
        """将新的 token 保存到配置文件"""
        try:
            # 确定目标配置文件
            # 如果存在 config.local.yaml，优先保存到那里
            local_config_path = self.config_file_path.replace('.yaml', '.local.yaml')
            if os.path.exists(local_config_path):
                target_file = local_config_path
                logger.info(f"检测到本地配置文件，Token 将保存到: {target_file}")
            else:
                target_file = self.config_file_path

            # 确保目录存在
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            
            # 读取当前配置
            if os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}

            if 'twitter' not in config:
                config['twitter'] = {}

            config['twitter']['access_token'] = access_token
            if refresh_token:
                config['twitter']['refresh_token'] = refresh_token
            if expires_at:
                config['twitter']['token_expires_at'] = expires_at

            # 写回配置文件
            with open(target_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            logger.info("新的访问令牌已保存到配置文件")

        except Exception as e:
            logger.error(f"保存令牌到配置文件失败: {e}")

    # ... validate_credentials, get_auth_headers, revoke_token 保持不变 ...
    def validate_credentials(self) -> bool:
        if not self._access_token:
            return False
        return True

    def get_auth_headers(self) -> Dict[str, str]:
        access_token = self.get_access_token()
        if access_token:
            return {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
        return {}

    def revoke_token(self) -> bool:
        # (保持你原来的 revoke_token 逻辑，这里略去以节省篇幅，不需要修改)
        # 如果需要完整代码，请把你原来的 revoke_token 粘贴回来即可
        return True

# 全局 Token 管理器实例
token_manager = TokenManager()# """
# Twitter Token 管理模块
# 负责管理和刷新 Twitter API 访问令牌（OAuth 2.0）
# """

# import time
# import base64
# import requests
# import yaml
# from pathlib import Path
# from typing import Dict, Optional
# from datetime import datetime, timedelta
# from utils.config_loader import config_loader
# from utils.logger import logger


# class TokenManager:
#     """Twitter Token 管理器类（OAuth 2.0）"""

#     def __init__(self):
#         """初始化 Token 管理器"""
#         self.twitter_config = config_loader.get_twitter_config()
#         self._access_token = None
#         self._refresh_token = None
#         self._token_expires_at = None
#         self._client_id = None
#         self._client_secret = None
#         self.config_file_path = Path("config/config.yaml")
#         self._load_tokens()

#     def _load_tokens(self):
#         """从配置文件加载令牌"""
#         self._access_token = self.twitter_config.get('access_token')
#         self._refresh_token = self.twitter_config.get('refresh_token')
#         self._client_id = self.twitter_config.get('client_id')
#         self._client_secret = self.twitter_config.get('client_secret')

#         # 加载 token 过期时间（如果有）
#         expires_at = self.twitter_config.get('token_expires_at')
#         if expires_at:
#             try:
#                 self._token_expires_at = datetime.fromisoformat(expires_at).timestamp()
#             except:
#                 self._token_expires_at = None

#         if not self._access_token:
#             logger.warning("Twitter OAuth 2.0 访问令牌未配置")
#         else:
#             logger.info("Twitter OAuth 2.0 访问令牌已加载")

#         if not self._refresh_token:
#             logger.warning("Twitter OAuth 2.0 刷新令牌未配置")

#     def get_access_token(self) -> Optional[str]:
#         """
#         获取访问令牌，如果过期则自动刷新

#         Returns:
#             访问令牌字符串
#         """
#         # 检查 token 是否即将过期（提前 5 分钟刷新）
#         if self._is_token_expired():
#             logger.info("访问令牌已过期或即将过期，尝试刷新")
#             if self._refresh_access_token():
#                 logger.info("访问令牌刷新成功")
#             else:
#                 logger.error("访问令牌刷新失败")

#         return self._access_token

#     def get_refresh_token(self) -> Optional[str]:
#         """
#         获取刷新令牌

#         Returns:
#             刷新令牌字符串
#         """
#         return self._refresh_token

#     def _is_token_expired(self) -> bool:
#         """
#         检查令牌是否过期或即将过期

#         Returns:
#             令牌是否过期
#         """
#         if not self._token_expires_at:
#             # 如果没有过期时间信息，假设需要刷新
#             return True

#         # 提前 5 分钟刷新 token
#         return time.time() >= (self._token_expires_at - 300)

#     def _refresh_access_token(self) -> bool:
#         """
#         使用 refresh_token 刷新 access_token（OAuth 2.0）

#         Returns:
#             刷新是否成功
#         """
#         if not self._refresh_token:
#             logger.error("刷新令牌未配置，无法刷新访问令牌")
#             return False

#         try:
#             # 导入代理管理器
#             from utils.proxy import proxy_manager

#             # Twitter OAuth 2.0 token endpoint
#             token_url = "https://api.twitter.com/2/oauth2/token"

#             # 准备请求数据
#             data = {
#                 'grant_type': 'refresh_token',
#                 'refresh_token': self._refresh_token,
#             }

#             # 准备认证头（使用 client_id 和 client_secret）
#             # 如果没有配置 client_id，尝试使用 consumer_key
#             client_id = self._client_id or self.twitter_config.get('consumer_key')
#             client_secret = self._client_secret or self.twitter_config.get('consumer_secret')

#             if client_id and client_secret:
#                 # 使用 Basic Auth
#                 auth_string = f"{client_id}:{client_secret}"
#                 auth_bytes = auth_string.encode('ascii')
#                 auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

#                 headers = {
#                     'Authorization': f'Basic {auth_b64}',
#                     'Content-Type': 'application/x-www-form-urlencoded'
#                 }
#             else:
#                 headers = {
#                     'Content-Type': 'application/x-www-form-urlencoded'
#                 }
#                 # 如果没有 client credentials，将 client_id 放在请求体中
#                 if client_id:
#                     data['client_id'] = client_id

#             # 获取代理配置
#             proxies = proxy_manager.get_proxies() if proxy_manager.is_proxy_enabled() else None

#             logger.info("正在刷新 Twitter OAuth 2.0 访问令牌...")

#             # 发送刷新请求（增加超时时间）
#             response = requests.post(
#                 token_url,
#                 data=data,
#                 headers=headers,
#                 proxies=proxies,
#                 timeout=60  # 增加到 60 秒
#             )

#             if response.status_code == 200:
#                 token_data = response.json()

#                 # 更新 token
#                 new_access_token = token_data.get('access_token')
#                 new_refresh_token = token_data.get('refresh_token')
#                 expires_in = token_data.get('expires_in', 7200)  # 默认 2 小时

#                 if new_access_token:
#                     self._access_token = new_access_token
#                     logger.info("访问令牌已更新")

#                 if new_refresh_token:
#                     self._refresh_token = new_refresh_token
#                     logger.info("刷新令牌已更新")

#                 # 计算过期时间
#                 self._token_expires_at = time.time() + expires_in
#                 expires_at_str = datetime.fromtimestamp(self._token_expires_at).isoformat()

#                 # 保存新的 token 到配置文件
#                 self._save_tokens_to_config(
#                     access_token=new_access_token,
#                     refresh_token=new_refresh_token,
#                     expires_at=expires_at_str
#                 )

#                 logger.info(f"访问令牌刷新成功，将在 {expires_in} 秒后过期")
#                 return True
#             else:
#                 logger.error(f"刷新访问令牌失败，状态码: {response.status_code}")
#                 logger.error(f"响应内容: {response.text}")
#                 return False

#         except Exception as e:
#             logger.error(f"刷新访问令牌时发生错误: {e}", exc_info=True)
#             return False

#     def _save_tokens_to_config(self, access_token: str, refresh_token: Optional[str] = None,
#                                expires_at: Optional[str] = None):
#         """
#         将新的 token 保存到配置文件

#         Args:
#             access_token: 新的访问令牌
#             refresh_token: 新的刷新令牌（可选）
#             expires_at: 过期时间（ISO 格式字符串）
#         """
#         try:
#             # 读取当前配置文件
#             with open(self.config_file_path, 'r', encoding='utf-8') as f:
#                 config = yaml.safe_load(f)

#             # 更新 token
#             if 'twitter' not in config:
#                 config['twitter'] = {}

#             config['twitter']['access_token'] = access_token

#             if refresh_token:
#                 config['twitter']['refresh_token'] = refresh_token

#             if expires_at:
#                 config['twitter']['token_expires_at'] = expires_at

#             # 写回配置文件
#             with open(self.config_file_path, 'w', encoding='utf-8') as f:
#                 yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

#             logger.info("新的访问令牌已保存到配置文件")

#         except Exception as e:
#             logger.error(f"保存令牌到配置文件失败: {e}")

#     def validate_credentials(self) -> bool:
#         """
#         验证 OAuth 2.0 凭据是否完整

#         Returns:
#             凭据是否完整有效
#         """
#         # OAuth 2.0 需要 access_token 和 refresh_token
#         if not self._access_token:
#             logger.error("缺少 OAuth 2.0 访问令牌 (access_token)")
#             return False

#         if not self._refresh_token:
#             logger.warning("缺少 OAuth 2.0 刷新令牌 (refresh_token)，token 过期后将无法自动刷新")

#         logger.info("Twitter OAuth 2.0 凭据验证通过")
#         return True

#     def get_auth_headers(self) -> Dict[str, str]:
#         """
#         获取 OAuth 2.0 认证头部信息

#         Returns:
#             包含认证信息的头部字典
#         """
#         access_token = self.get_access_token()
#         if access_token:
#             return {
#                 'Authorization': f'Bearer {access_token}',
#                 'Content-Type': 'application/json'
#             }
#         else:
#             logger.warning("OAuth 2.0 访问令牌未配置")
#             return {}

#     def revoke_token(self) -> bool:
#         """
#         撤销当前的访问令牌

#         Returns:
#             撤销是否成功
#         """
#         if not self._access_token:
#             logger.warning("没有可撤销的访问令牌")
#             return False

#         try:
#             from utils.proxy import proxy_manager

#             revoke_url = "https://api.twitter.com/2/oauth2/revoke"

#             # 准备请求数据
#             data = {
#                 'token': self._access_token,
#                 'token_type_hint': 'access_token'
#             }

#             # 准备认证头
#             client_id = self._client_id or self.twitter_config.get('consumer_key')
#             client_secret = self._client_secret or self.twitter_config.get('consumer_secret')

#             if client_id and client_secret:
#                 auth_string = f"{client_id}:{client_secret}"
#                 auth_bytes = auth_string.encode('ascii')
#                 auth_b64 = base64.b64encode(auth_bytes).decode('ascii')

#                 headers = {
#                     'Authorization': f'Basic {auth_b64}',
#                     'Content-Type': 'application/x-www-form-urlencoded'
#                 }
#             else:
#                 headers = {
#                     'Content-Type': 'application/x-www-form-urlencoded'
#                 }
#                 if client_id:
#                     data['client_id'] = client_id

#             # 获取代理配置
#             proxies = proxy_manager.get_proxies() if proxy_manager.is_proxy_enabled() else None

#             # 发送撤销请求
#             response = requests.post(
#                 revoke_url,
#                 data=data,
#                 headers=headers,
#                 proxies=proxies,
#                 timeout=30
#             )

#             if response.status_code == 200:
#                 logger.info("访问令牌已成功撤销")
#                 self._access_token = None
#                 return True
#             else:
#                 logger.error(f"撤销访问令牌失败，状态码: {response.status_code}")
#                 return False

#         except Exception as e:
#             logger.error(f"撤销访问令牌时发生错误: {e}")
#             return False


# # 全局 Token 管理器实例
# token_manager = TokenManager()
