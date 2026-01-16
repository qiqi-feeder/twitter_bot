"""
Twitter API 客户端模块
负责与 Twitter API v2 交互，发送推文（支持 OAuth 2.0 自动刷新）
"""

import tweepy
import time
from typing import Optional, Dict, Any
from auth.token_manager import token_manager
from utils.proxy import proxy_manager
from utils.logger import logger

class TwitterAPIClient:
    """Twitter API 客户端类（支持 OAuth 2.0 自动续期）"""

    def __init__(self):
        """初始化 Twitter API 客户端"""
        self.client = None
        self.api_v1 = None
        self.use_oauth2 = False
        self._setup_client()

    def _setup_client(self):
        """设置 Twitter API 客户端（优先使用 OAuth 2.0）"""
        try:
            # 验证凭据
            if not token_manager.validate_credentials():
                logger.error("Twitter 凭据验证失败，无法初始化客户端")
                return

            # 获取 OAuth 2.0 访问令牌
            access_token = token_manager.get_access_token()

            # 设置代理（如果启用）
            if proxy_manager.is_proxy_enabled():
                proxy_manager.set_env_proxies()
                logger.debug("为 Twitter 客户端配置了代理")

            # 优先使用 OAuth 2.0
            if access_token and token_manager.get_refresh_token():
                logger.info("初始化 OAuth 2.0 客户端...")
                self.use_oauth2 = True

                from utils.config_loader import config_loader
                twitter_config = config_loader.get_twitter_config()
                
                # 创建 Tweepy 客户端 (OAuth 2.0 User Context)
                self.client = tweepy.Client(
                    bearer_token=access_token,
                    wait_on_rate_limit=True
                )

                # 初始化 OAuth 1.0a (仅用于图片上传，可选)
                self._setup_v1_client(twitter_config)
                
                logger.info("Twitter API 客户端初始化完成")
            else:
                logger.error("OAuth 2.0 凭据不完整（缺少 Token），请运行 tools/oauth2_authorize_remote.py")
                return

        except Exception as e:
            logger.error(f"初始化 Twitter API 客户端失败: {e}", exc_info=True)

    def _setup_v1_client(self, config):
        """辅助方法：初始化 v1.1 客户端用于传图"""
        consumer_key = config.get('consumer_key')
        consumer_secret = config.get('consumer_secret')
        access_token_1_0a = config.get('access_token_1_0a')
        access_token_secret = config.get('access_token_secret')
        
        if all([consumer_key, consumer_secret, access_token_1_0a, access_token_secret]):
            try:
                auth = tweepy.OAuth1UserHandler(
                    consumer_key, consumer_secret, access_token_1_0a, access_token_secret
                )
                self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
                logger.debug("OAuth 1.0a 媒体上传客户端已就绪")
            except Exception as e:
                logger.warning(f"OAuth 1.0a 初始化失败: {e}")
        else:
            self.api_v1 = None

    def _refresh_token_and_reload(self):
        """
        [关键逻辑] 刷新 Token 并重新加载客户端
        """
        logger.warning("正在尝试刷新 Access Token...")
        try:
            # 调用 token_manager 进行刷新
            new_token = token_manager.refresh_access_token()
            
            if new_token:
                logger.info("Token 刷新成功，正在重载客户端...")
                # 重新运行 setup，加载新的 Token
                self._setup_client()
                return True
            else:
                logger.error("Token 刷新返回失败")
                return False
        except Exception as e:
            logger.error(f"刷新 Token 过程中发生异常: {e}")
            return False

    def post_tweet(self, content: str, media_paths: list = None, retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        发送推文（包含 401 自动刷新重试机制）
        """
        if not self.client:
            logger.error("客户端未初始化")
            return None
            
        if retry_count > 1:
            logger.error("Token 刷新后依然失败，停止重试")
            return None

        try:
            logger.info(f"发送推文 (长度: {len(content)})")

            # 1. 上传媒体 (使用 v1 接口)
            media_ids = []
            if media_paths and self.api_v1:
                logger.info(f"正在上传 {len(media_paths)} 张图片...")
                for path in media_paths:
                    media = self.api_v1.media_upload(filename=path)
                    media_ids.append(media.media_id)

            # 2. 发送推文 (使用 v2 接口)
            if media_ids:
                response = self.client.create_tweet(text=content, media_ids=media_ids, user_auth=False)
            else:
                response = self.client.create_tweet(text=content, user_auth=False)
            
            if response.data:
                tid = response.data['id']
                url = f"https://twitter.com/user/status/{tid}"
                logger.info(f"✅ 发送成功! URL: {url}")
                return {'id': tid, 'url': url, 'content': content, 'success': True}
            
        except tweepy.Unauthorized as e:
            # === 捕获 401 错误 ===
            logger.warning(f"⚠️ 捕获到 401 Unauthorized (Token 可能过期): {e}")
            
            if retry_count == 0:
                logger.info("🚀 触发自动刷新机制...")
                if self._refresh_token_and_reload():
                    logger.info("🔄 Token 刷新完毕，正在重发推文...")
                    return self.post_tweet(content, media_paths, retry_count=1)
                else:
                    logger.error("❌ 自动刷新失败，无法重发")
            else:
                logger.error("❌ 重试次数已达上限")

        except Exception as e:
            logger.error(f"❌ 发推异常: {e}")
            import traceback
            logger.debug(traceback.format_exc())

        return None

    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        if not self.client: return None
        try:
            return self._safe_api_call(lambda: self.client.get_me(user_fields=['public_metrics'], user_auth=False))
        except: return None

    def _safe_api_call(self, func):
        """API 调用包装器（带自动刷新）"""
        try:
            res = func()
            if hasattr(res, 'data') and res.data:
                # 提取数据
                data = res.data
                public_metrics = getattr(data, 'public_metrics', {}) or {}
                return {
                    'username': data.username,
                    'name': data.name,
                    'id': data.id,
                    'followers_count': public_metrics.get('followers_count', 0),
                    'following_count': public_metrics.get('following_count', 0),
                    'tweet_count': public_metrics.get('tweet_count', 0)
                }
            return None
        except tweepy.Unauthorized:
            if self._refresh_token_and_reload():
                return self._safe_api_call(func)
            return None
        except Exception as e:
            logger.error(f"API 调用失败: {e}")
            return None

    # ==========================================
    # 👇 补回缺失的 test_connection 方法
    # ==========================================
    def test_connection(self) -> bool:
        """
        测试 Twitter API 连接
        """
        try:
            user_info = self.get_user_info()
            if user_info:
                logger.info(f"Twitter API 连接测试成功 (用户: @{user_info['username']})")
                return True
            else:
                logger.error("Twitter API 连接测试失败 (无法获取用户信息)")
                return False
        except Exception as e:
            logger.error(f"Twitter API 连接测试异常: {e}")
            return False

    # ==========================================
    # 👇 补回缺失的 get_recent_tweets 方法
    # ==========================================
    def get_recent_tweets(self, count: int = 5) -> list:
        """获取最近推文"""
        if not self.client: return []
        try:
            user_info = self.get_user_info()
            if not user_info: return []
            
            tweets = self.client.get_users_tweets(
                id=user_info['id'],
                max_results=min(count, 100),
                tweet_fields=['created_at', 'public_metrics'],
                user_auth=False
            )
            
            tweet_list = []
            if tweets.data:
                for t in tweets.data:
                    tweet_list.append({
                        'id': t.id,
                        'text': t.text,
                        'created_at': t.created_at,
                        'url': f"https://twitter.com/user/status/{t.id}"
                    })
            return tweet_list
        except Exception as e:
            logger.error(f"获取推文失败: {e}")
            return []

# 全局实例
twitter_client = TwitterAPIClient()
# """
# Twitter API 客户端模块
# 负责与 Twitter API v2 交互，发送推文（支持 OAuth 2.0）
# """

# import tweepy
# import requests
# from typing import Optional, Dict, Any
# from auth.token_manager import token_manager
# from utils.proxy import proxy_manager
# from utils.logger import logger


# class TwitterAPIClient:
#     """Twitter API 客户端类（支持 OAuth 2.0）"""

#     def __init__(self):
#         """初始化 Twitter API 客户端"""
#         self.client = None
#         self.api = None
#         self.use_oauth2 = False
#         self._setup_client()

#     def _setup_client(self):
#         """设置 Twitter API 客户端（优先使用 OAuth 2.0）"""
#         try:
#             # 验证凭据
#             if not token_manager.validate_credentials():
#                 logger.error("Twitter 凭据验证失败，无法初始化客户端")
#                 return

#             # 获取 OAuth 2.0 访问令牌
#             access_token = token_manager.get_access_token()

#             # 设置代理（如果启用）
#             proxy_url = None
#             if proxy_manager.is_proxy_enabled():
#                 proxies = proxy_manager.get_proxies()
#                 if proxies:
#                     proxy_url = proxies.get('https')
#                     logger.info("为 Twitter 客户端配置代理")
#                     # 设置环境变量，tweepy 会自动使用这些环境变量
#                     proxy_manager.set_env_proxies()

#             # 优先使用 OAuth 2.0
#             if access_token and token_manager.get_refresh_token():
#                 logger.info("使用 OAuth 2.0 认证方式")
#                 self.use_oauth2 = True

#                 # 获取配置
#                 from utils.config_loader import config_loader
#                 twitter_config = config_loader.get_twitter_config()
                
#                 # 创建 Tweepy 客户端 (OAuth 2.0 User Context)
#                 # 用于发送推文、读取数据等 v2 API
#                 self.client = tweepy.Client(
#                     bearer_token=access_token,
#                     wait_on_rate_limit=True
#                 )

#                 logger.info("Twitter API 客户端初始化成功（OAuth 2.0）")

#                 # 尝试初始化 OAuth 1.0a 客户端用于媒体上传
#                 # OAuth 1.0a 是可选的，仅用于 v1.1 API 的 media/upload 端点
#                 consumer_key = twitter_config.get('consumer_key')
#                 consumer_secret = twitter_config.get('consumer_secret')
#                 access_token_1_0a = twitter_config.get('access_token_1_0a')
#                 access_token_secret = twitter_config.get('access_token_secret')
                
#                 if all([consumer_key, consumer_secret, access_token_1_0a, access_token_secret]):
#                     try:
#                         # 创建 OAuth 1.0a 认证
#                         auth_1_0a = tweepy.OAuth1UserHandler(
#                             consumer_key=consumer_key,
#                             consumer_secret=consumer_secret,
#                             access_token=access_token_1_0a,
#                             access_token_secret=access_token_secret
#                         )
                        
#                         # 创建 v1.1 API 客户端（用于媒体上传）
#                         # 注意：tweepy.API 会自动使用环境变量中的代理配置
#                         self.api_v1 = tweepy.API(auth_1_0a, wait_on_rate_limit=True)
                        
#                         logger.info("OAuth 1.0a 客户端初始化成功（用于媒体上传）")
#                     except Exception as e:
#                         logger.warning(f"OAuth 1.0a 客户端初始化失败: {e}")
#                         logger.warning("媒体上传功能将不可用，但其他功能正常")
#                         self.api_v1 = None
#                 else:
#                     logger.info("未配置 OAuth 1.0a 凭据，媒体上传功能将不可用")
#                     logger.info("如需上传图片，请配置 consumer_key, consumer_secret, access_token_1_0a, access_token_secret")
#                     self.api_v1 = None


#             else:
#                 # OAuth 2.0 凭据不完整，无法初始化客户端
#                 logger.error("OAuth 2.0 凭据不完整（缺少 access_token 或 refresh_token）")
#                 logger.error("请运行授权工具获取 Token: python tools/oauth2_authorize_remote.py")
#                 return

#         except Exception as e:
#             logger.error(f"初始化 Twitter API 客户端失败: {e}", exc_info=True)
    
#     def post_tweet(self, content: str, media_paths: list = None) -> Optional[Dict[str, Any]]:
#         """
#         发送推文
        
#         Args:
#             content: 推文内容
#             media_paths: 图片文件路径列表 (可选)
            
#         Returns:
#             推文信息字典，失败时返回 None
#         """
#         if not self.client:
#             logger.error("Twitter API 客户端未初始化")
#             return None
        
#         if not content or not content.strip():
#             logger.error("推文内容为空")
#             return None
        
#         # 检查推文长度
#         if len(content) > 280:
#             logger.error(f"推文内容过长: {len(content)} 字符")
#             return None
        
#         try:
#             logger.info(f"开始发送推文，内容长度: {len(content)} 字符")
#             logger.debug(f"推文内容: {content}")

#             # 上传媒体文件 (如果有)
#             media_ids = []
#             if media_paths:
#                 logger.info(f"准备上传 {len(media_paths)} 个媒体文件")
#                 for path in media_paths:
#                     try:
#                         # 使用 v1.1 API 上传
#                         # 注意：这里假设 self.api_v1 已经正确初始化
#                         # 如果是 OAuth 2.0 Bearer Token，media_upload 可能受限
#                         media = self.api_v1.media_upload(filename=path)
#                         media_ids.append(media.media_id)
#                         logger.info(f"媒体文件上传成功: {path} (ID: {media.media_id})")
#                     except Exception as e:
#                         logger.error(f"媒体文件上传失败 {path}: {e}")
            
#             # 使用 Twitter API v2 发送推文
#             # 注意：使用 OAuth 2.0 时必须设置 user_auth=False
#             # 默认 user_auth=True 会尝试使用 OAuth 1.0a 认证
#             if media_ids:
#                 response = self.client.create_tweet(text=content, media_ids=media_ids, user_auth=False)
#             else:
#                 response = self.client.create_tweet(text=content, user_auth=False)
            
#             if response.data:
#                 tweet_id = response.data['id']
#                 tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                
#                 result = {
#                     'id': tweet_id,
#                     'url': tweet_url,
#                     'content': content,
#                     'success': True
#                 }
                
#                 logger.info(f"推文发送成功! ID: {tweet_id}")
#                 logger.info(f"推文链接: {tweet_url}")
                
#                 return result
#             else:
#                 logger.error("推文发送失败，API 返回空数据")
#                 return None
                
#         except tweepy.TooManyRequests as e:
#             logger.error(f"Twitter API 速率限制，请稍后重试: {e}")
#             return None
#         except tweepy.Unauthorized as e:
#             logger.error(f"Twitter API 认证失败: {e}")
#             logger.error("可能原因: access_token 已过期或无效")
#             logger.error("解决方法: 运行 python tools/oauth2_authorize_remote.py 重新授权")
#             return None
#         except tweepy.Forbidden as e:
#             logger.error(f"Twitter API 权限不足: {e}")
#             logger.error("详细错误信息:")
#             if hasattr(e, 'response') and e.response:
#                 logger.error(f"  HTTP 状态码: {e.response.status_code}")
#                 logger.error(f"  响应内容: {e.response.text}")
#             logger.error("可能原因:")
#             logger.error("  1. App 权限设置不正确（需要 Read and Write 权限）")
#             logger.error("  2. OAuth 2.0 Scopes 不足（需要 tweet.read 和 tweet.write）")
#             logger.error("  3. access_token 权限不足")
#             logger.error("解决方法:")
#             logger.error("  1. 检查 Twitter Developer Portal 中的 App Permissions")
#             logger.error("  2. 确保授权时包含了 tweet.write scope")
#             logger.error("  3. 重新运行授权: python tools/oauth2_authorize_remote.py")
#             return None
#         except Exception as e:
#             logger.error(f"发送推文时发生错误: {e}")
#             logger.error(f"错误类型: {type(e).__name__}")
#             import traceback
#             logger.error(f"错误堆栈: {traceback.format_exc()}")
#             return None
    
#     def get_user_info(self) -> Optional[Dict[str, Any]]:
#         """
#         获取当前用户信息
        
#         Returns:
#             用户信息字典，失败时返回 None
#         """
#         if not self.client:
#             logger.error("Twitter API 客户端未初始化")
#             return None
        
#         try:
#             # 获取当前认证用户信息
#             # user_auth=False 表示使用 bearer token 认证，而不是 OAuth 1.0a
#             # user_fields 指定返回 public_metrics 数据
#             user = self.client.get_me(
#                 user_fields=['public_metrics'],
#                 user_auth=False
#             )
            
#             if user.data:
#                 # 安全获取 public_metrics
#                 public_metrics = getattr(user.data, 'public_metrics', None)
#                 if public_metrics is None:
#                     public_metrics = {}
                
#                 user_info = {
#                     'id': user.data.id,
#                     'username': user.data.username,
#                     'name': user.data.name,
#                     'followers_count': public_metrics.get('followers_count', 0),
#                     'following_count': public_metrics.get('following_count', 0),
#                     'tweet_count': public_metrics.get('tweet_count', 0)
#                 }
                
#                 logger.info(f"获取用户信息成功: @{user_info['username']}")
#                 return user_info
#             else:
#                 logger.error("获取用户信息失败，API 返回空数据")
#                 return None
                
#         except Exception as e:
#             logger.error(f"获取用户信息时发生错误: {e}")
#             return None
    
#     def test_connection(self) -> bool:
#         """
#         测试 Twitter API 连接
        
#         Returns:
#             连接是否成功
#         """
#         try:
#             user_info = self.get_user_info()
#             if user_info:
#                 logger.info("Twitter API 连接测试成功")
#                 return True
#             else:
#                 logger.error("Twitter API 连接测试失败")
#                 return False
                
#         except Exception as e:
#             logger.error(f"Twitter API 连接测试失败: {e}")
#             return False
    
#     def get_recent_tweets(self, count: int = 5) -> list:
#         """
#         获取最近的推文
        
#         Args:
#             count: 获取推文数量
            
#         Returns:
#             推文列表
#         """
#         if not self.client:
#             logger.error("Twitter API 客户端未初始化")
#             return []
        
#         try:
#             # 获取当前用户信息
#             user = self.client.get_me(user_auth=False)
#             if not user.data:
#                 logger.error("无法获取用户信息")
#                 return []
            
#             # 获取用户最近的推文
#             tweets = self.client.get_users_tweets(
#                 id=user.data.id,
#                 max_results=min(count, 100),  # API 限制
#                 tweet_fields=['created_at', 'public_metrics'],
#                 user_auth=False
#             )
            
#             if tweets.data:
#                 tweet_list = []
#                 for tweet in tweets.data:
#                     tweet_info = {
#                         'id': tweet.id,
#                         'text': tweet.text,
#                         'created_at': tweet.created_at,
#                         'url': f"https://twitter.com/user/status/{tweet.id}"
#                     }
#                     tweet_list.append(tweet_info)
                
#                 logger.info(f"获取到 {len(tweet_list)} 条最近推文")
#                 return tweet_list
#             else:
#                 logger.info("没有找到最近的推文")
#                 return []
                
#         except Exception as e:
#             logger.error(f"获取最近推文时发生错误: {e}")
#             return []


# # 全局 Twitter API 客户端实例
# twitter_client = TwitterAPIClient()
