"""
LLM 客户端模块
负责调用 OpenAI API 生成推文内容
"""

from openai import OpenAI
import httpx
from typing import Optional
from utils.config_loader import config_loader
from utils.proxy import proxy_manager
from utils.logger import logger


class LLMClient:
    """LLM 客户端类"""

    def __init__(self):
        """初始化 LLM 客户端"""
        self.openai_config = config_loader.get_openai_config()
        self.client = None
        self._setup_openai_client()

    def _setup_openai_client(self):
        """设置 OpenAI 客户端"""
        api_key = self.openai_config.get('api_key')
        if not api_key:
            logger.warning("OpenAI API Key 未配置，LLM 功能将不可用")
            return

        # 如果启用了代理，配置代理
        http_client = None
        if proxy_manager.is_proxy_enabled():
            proxies = proxy_manager.get_proxies()
            if proxies:
                # 为 OpenAI v1.x 配置代理
                # proxies 格式: {'http://': 'socks5://...', 'https://': 'socks5://...'}
                proxy_url = proxies.get('https://') or proxies.get('http://')
                if proxy_url:
                    # httpx.Client 使用 proxy 参数（单数），不是 proxies
                    http_client = httpx.Client(proxy=proxy_url)
                    logger.info(f"已为 OpenAI 客户端配置代理: {proxy_url}")

        # 创建 OpenAI 客户端（v1.x API）
        self.client = OpenAI(
            api_key=api_key,
            http_client=http_client
        )

        logger.info("OpenAI 客户端初始化完成")
    
    def generate_tweet(self, custom_prompt: Optional[str] = None) -> Optional[str]:
        """
        生成推文内容

        Args:
            custom_prompt: 自定义提示词，如果不提供则使用配置文件中的默认提示词

        Returns:
            生成的推文内容，失败时返回 None
        """
        # 检查客户端是否初始化
        if not self.client:
            logger.error("OpenAI 客户端未初始化，无法生成推文")
            return None

        try:
            # 获取提示词
            prompt = custom_prompt or self.openai_config.get('prompt_template', '')
            if not prompt:
                logger.error("未配置推文生成提示词")
                return None

            # 获取模型配置
            model = self.openai_config.get('model', 'gpt-3.5-turbo')

            logger.info(f"开始生成推文，使用模型: {model}")

            # 调用 OpenAI API (v1.x)
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,  # 限制生成长度
                temperature=0.8,  # 增加创造性
                top_p=1.0,
                frequency_penalty=0.5,  # 减少重复
                presence_penalty=0.5
            )

            # 提取生成的内容
            if response.choices and len(response.choices) > 0:
                tweet_content = response.choices[0].message.content.strip()

                # 验证推文长度（Twitter 限制 280 字符）
                if len(tweet_content) > 280:
                    logger.warning(f"生成的推文过长 ({len(tweet_content)} 字符)，尝试截断")
                    tweet_content = tweet_content[:277] + "..."

                logger.info(f"推文生成成功，长度: {len(tweet_content)} 字符")
                logger.debug(f"生成的推文内容: {tweet_content}")

                return tweet_content
            else:
                logger.error("OpenAI API 返回空响应")
                return None

        except Exception as e:
            # OpenAI v1.x 使用不同的异常类型
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                logger.error("OpenAI API 速率限制，请稍后重试")
            elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                logger.error("OpenAI API 认证失败，请检查 API Key")
            else:
                logger.error(f"生成推文时发生错误: {e}")
            return None
    
    def generate_multiple_tweets(self, count: int = 3) -> list:
        """
        生成多条推文供选择
        
        Args:
            count: 生成推文数量
            
        Returns:
            推文内容列表
        """
        tweets = []
        
        for i in range(count):
            logger.info(f"生成第 {i+1}/{count} 条推文")
            tweet = self.generate_tweet()
            if tweet:
                tweets.append(tweet)
            else:
                logger.warning(f"第 {i+1} 条推文生成失败")
        
        logger.info(f"成功生成 {len(tweets)}/{count} 条推文")
        return tweets
    
    def validate_api_key(self) -> bool:
        """
        验证 OpenAI API Key 是否有效

        Returns:
            API Key 是否有效
        """
        if not self.client:
            logger.error("OpenAI 客户端未初始化")
            return False

        try:
            # 发送一个简单的请求来验证 API Key
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )

            logger.info("OpenAI API Key 验证成功")
            return True

        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "api_key" in error_msg.lower():
                logger.error("OpenAI API Key 验证失败")
            else:
                logger.error(f"验证 OpenAI API Key 时发生错误: {e}")
            return False


# 全局 LLM 客户端实例
llm_client = LLMClient()
