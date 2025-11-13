"""
Twitter API 客户端模块
负责与 Twitter API v2 交互，发送推文（支持 OAuth 2.0）
"""

import tweepy
import requests
from typing import Optional, Dict, Any
from auth.token_manager import token_manager
from utils.proxy import proxy_manager
from utils.logger import logger


class TwitterAPIClient:
    """Twitter API 客户端类（支持 OAuth 2.0）"""

    def __init__(self):
        """初始化 Twitter API 客户端"""
        self.client = None
        self.api = None
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
            proxy_url = None
            if proxy_manager.is_proxy_enabled():
                proxies = proxy_manager.get_proxies()
                if proxies:
                    proxy_url = proxies.get('https')
                    logger.info("为 Twitter 客户端配置代理")

            # 优先使用 OAuth 2.0
            if access_token and token_manager.get_refresh_token():
                logger.info("使用 OAuth 2.0 认证方式")
                self.use_oauth2 = True

                # 获取 client_id 和 client_secret（OAuth 2.0 需要）
                from utils.config_loader import config_loader
                twitter_config = config_loader.get_twitter_config()
                client_id = twitter_config.get('client_id')
                client_secret = twitter_config.get('client_secret')

                # 创建 Tweepy 客户端 (OAuth 2.0)
                # 注意：tweepy 的 Client 在使用 OAuth 2.0 User Context 时需要 consumer_key 和 consumer_secret
                # 这里我们使用 client_id 作为 consumer_key，client_secret 作为 consumer_secret
                self.client = tweepy.Client(
                    bearer_token=access_token,
                    consumer_key=client_id,
                    consumer_secret=client_secret,
                    wait_on_rate_limit=True
                )

                logger.info("Twitter API 客户端初始化成功（OAuth 2.0）")

            else:
                # OAuth 2.0 凭据不完整，无法初始化客户端
                logger.error("OAuth 2.0 凭据不完整（缺少 access_token 或 refresh_token）")
                logger.error("请运行授权工具获取 Token: python tools/oauth2_authorize_remote.py")
                return

        except Exception as e:
            logger.error(f"初始化 Twitter API 客户端失败: {e}", exc_info=True)
    
    def post_tweet(self, content: str) -> Optional[Dict[str, Any]]:
        """
        发送推文
        
        Args:
            content: 推文内容
            
        Returns:
            推文信息字典，失败时返回 None
        """
        if not self.client:
            logger.error("Twitter API 客户端未初始化")
            return None
        
        if not content or not content.strip():
            logger.error("推文内容为空")
            return None
        
        # 检查推文长度
        if len(content) > 280:
            logger.error(f"推文内容过长: {len(content)} 字符")
            return None
        
        try:
            logger.info(f"开始发送推文，内容长度: {len(content)} 字符")
            logger.debug(f"推文内容: {content}")
            
            # 使用 Twitter API v2 发送推文
            response = self.client.create_tweet(text=content)
            
            if response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                
                result = {
                    'id': tweet_id,
                    'url': tweet_url,
                    'content': content,
                    'success': True
                }
                
                logger.info(f"推文发送成功! ID: {tweet_id}")
                logger.info(f"推文链接: {tweet_url}")
                
                return result
            else:
                logger.error("推文发送失败，API 返回空数据")
                return None
                
        except tweepy.TooManyRequests as e:
            logger.error(f"Twitter API 速率限制，请稍后重试: {e}")
            return None
        except tweepy.Unauthorized as e:
            logger.error(f"Twitter API 认证失败: {e}")
            logger.error("可能原因: access_token 已过期或无效")
            logger.error("解决方法: 运行 python tools/oauth2_authorize_remote.py 重新授权")
            return None
        except tweepy.Forbidden as e:
            logger.error(f"Twitter API 权限不足: {e}")
            logger.error("详细错误信息:")
            if hasattr(e, 'response') and e.response:
                logger.error(f"  HTTP 状态码: {e.response.status_code}")
                logger.error(f"  响应内容: {e.response.text}")
            logger.error("可能原因:")
            logger.error("  1. App 权限设置不正确（需要 Read and Write 权限）")
            logger.error("  2. OAuth 2.0 Scopes 不足（需要 tweet.read 和 tweet.write）")
            logger.error("  3. access_token 权限不足")
            logger.error("解决方法:")
            logger.error("  1. 检查 Twitter Developer Portal 中的 App Permissions")
            logger.error("  2. 确保授权时包含了 tweet.write scope")
            logger.error("  3. 重新运行授权: python tools/oauth2_authorize_remote.py")
            return None
        except Exception as e:
            logger.error(f"发送推文时发生错误: {e}")
            logger.error(f"错误类型: {type(e).__name__}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return None
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        获取当前用户信息
        
        Returns:
            用户信息字典，失败时返回 None
        """
        if not self.client:
            logger.error("Twitter API 客户端未初始化")
            return None
        
        try:
            # 获取当前认证用户信息
            user = self.client.get_me()
            
            if user.data:
                user_info = {
                    'id': user.data.id,
                    'username': user.data.username,
                    'name': user.data.name,
                    'followers_count': getattr(user.data, 'public_metrics', {}).get('followers_count', 0),
                    'following_count': getattr(user.data, 'public_metrics', {}).get('following_count', 0),
                    'tweet_count': getattr(user.data, 'public_metrics', {}).get('tweet_count', 0)
                }
                
                logger.info(f"获取用户信息成功: @{user_info['username']}")
                return user_info
            else:
                logger.error("获取用户信息失败，API 返回空数据")
                return None
                
        except Exception as e:
            logger.error(f"获取用户信息时发生错误: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        测试 Twitter API 连接
        
        Returns:
            连接是否成功
        """
        try:
            user_info = self.get_user_info()
            if user_info:
                logger.info("Twitter API 连接测试成功")
                return True
            else:
                logger.error("Twitter API 连接测试失败")
                return False
                
        except Exception as e:
            logger.error(f"Twitter API 连接测试失败: {e}")
            return False
    
    def get_recent_tweets(self, count: int = 5) -> list:
        """
        获取最近的推文
        
        Args:
            count: 获取推文数量
            
        Returns:
            推文列表
        """
        if not self.client:
            logger.error("Twitter API 客户端未初始化")
            return []
        
        try:
            # 获取当前用户信息
            user = self.client.get_me()
            if not user.data:
                logger.error("无法获取用户信息")
                return []
            
            # 获取用户最近的推文
            tweets = self.client.get_users_tweets(
                id=user.data.id,
                max_results=min(count, 100),  # API 限制
                tweet_fields=['created_at', 'public_metrics']
            )
            
            if tweets.data:
                tweet_list = []
                for tweet in tweets.data:
                    tweet_info = {
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at,
                        'url': f"https://twitter.com/user/status/{tweet.id}"
                    }
                    tweet_list.append(tweet_info)
                
                logger.info(f"获取到 {len(tweet_list)} 条最近推文")
                return tweet_list
            else:
                logger.info("没有找到最近的推文")
                return []
                
        except Exception as e:
            logger.error(f"获取最近推文时发生错误: {e}")
            return []


# 全局 Twitter API 客户端实例
twitter_client = TwitterAPIClient()
