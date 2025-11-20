"""
Twitter Thread 发布模块
自动拆分和发布 Twitter Thread
"""

import json
import time
from typing import List, Dict, Optional
from utils.logger import logger


class ThreadPoster:
    """Thread 发布器"""
    
    def __init__(self):
        pass
    
    def post_thread(self, tweets: List[str], delay: int = 2) -> Dict:
        """
        发布 Twitter Thread
        
        Args:
            tweets: 推文列表
            delay: 每条推文之间的延迟（秒）
            
        Returns:
            发布结果字典
        """
        if not tweets:
            logger.error("推文列表为空，无法发布 Thread")
            return {
                'success': False,
                'error': '推文列表为空'
            }
        
        try:
            # 延迟导入 Twitter 客户端
            from twitter.api_client import twitter_client
            
            logger.info(f"开始发布 Thread，共 {len(tweets)} 条推文")
            
            posted_tweets = []
            previous_tweet_id = None
            
            for i, tweet_content in enumerate(tweets, 1):
                logger.info(f"发布第 {i}/{len(tweets)} 条推文...")
                
                # 如果是回复推文，需要设置 in_reply_to_tweet_id
                if previous_tweet_id:
                    result = self._post_reply(tweet_content, previous_tweet_id)
                else:
                    # 第一条推文
                    result = twitter_client.post_tweet(tweet_content)
                
                if result and result.get('success'):
                    tweet_id = result.get('id')
                    tweet_url = result.get('url')
                    
                    posted_tweets.append({
                        'index': i,
                        'id': tweet_id,
                        'url': tweet_url,
                        'content': tweet_content
                    })
                    
                    previous_tweet_id = tweet_id
                    logger.info(f"第 {i} 条推文发布成功: {tweet_url}")
                    
                    # 延迟，避免触发速率限制
                    if i < len(tweets):
                        time.sleep(delay)
                else:
                    logger.error(f"第 {i} 条推文发布失败")
                    return {
                        'success': False,
                        'error': f'第 {i} 条推文发布失败',
                        'posted_tweets': posted_tweets
                    }
            
            logger.info(f"Thread 发布成功！共 {len(posted_tweets)} 条推文")
            
            return {
                'success': True,
                'thread_url': posted_tweets[0]['url'] if posted_tweets else None,
                'tweet_count': len(posted_tweets),
                'tweets': posted_tweets
            }
            
        except Exception as e:
            logger.error(f"发布 Thread 时发生错误: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _post_reply(self, content: str, reply_to_tweet_id: str) -> Optional[Dict]:
        """
        发布回复推文
        
        Args:
            content: 推文内容
            reply_to_tweet_id: 要回复的推文 ID
            
        Returns:
            发布结果
        """
        try:
            from twitter.api_client import twitter_client
            
            # 使用 tweepy 的 create_tweet 方法发布回复
            response = twitter_client.client.create_tweet(
                text=content,
                in_reply_to_tweet_id=reply_to_tweet_id,
                user_auth=False  # 使用 OAuth 2.0
            )
            
            if response.data:
                tweet_id = response.data['id']
                tweet_url = f"https://twitter.com/user/status/{tweet_id}"
                
                return {
                    'id': tweet_id,
                    'url': tweet_url,
                    'content': content,
                    'success': True
                }
            else:
                logger.error("回复推文发送失败，API 返回空数据")
                return None
                
        except Exception as e:
            logger.error(f"发布回复推文失败: {e}")
            return None


def post_daily_recap_thread(tweets: List[str]) -> Dict:
    """
    发布每日复盘 Thread
    
    Args:
        tweets: 推文列表
        
    Returns:
        发布结果字典
    """
    poster = ThreadPoster()
    return poster.post_thread(tweets, delay=2)


if __name__ == '__main__':
    # 测试发布
    test_tweets = [
        "📊 Test Thread 1/3\n\nThis is a test thread.",
        "📊 Test Thread 2/3\n\nSecond tweet in the thread.",
        "📊 Test Thread 3/3\n\nFinal tweet in the thread."
    ]
    
    result = post_daily_recap_thread(test_tweets)
    print(json.dumps(result, indent=2, ensure_ascii=False))

