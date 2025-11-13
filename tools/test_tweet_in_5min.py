"""
测试脚本：5分钟后自动发推
用于测试定时任务功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone as pytz_timezone
from utils.config_loader import config_loader
from utils.logger import logger


def send_test_tweet():
    """发送测试推文"""
    try:
        logger.info("开始发送测试推文...")
        
        # 延迟导入 Twitter 客户端
        from twitter.api_client import twitter_client
        
        # 固定的测试内容
        tweet_content = "Hello from Twitter Bot! 👋 This is a test tweet sent automatically. #TestTweet #Automation"
        
        logger.info(f"推文内容: {tweet_content}")
        
        # 发送推文
        result = twitter_client.post_tweet(tweet_content)
        
        if result and result.get('success'):
            logger.info(f"✓ 测试推文发送成功!")
            logger.info(f"  推文 ID: {result.get('id')}")
            logger.info(f"  推文 URL: {result.get('url')}")
            print(f"\n✓ 测试推文发送成功!")
            print(f"  推文 URL: {result.get('url')}")
        else:
            logger.error("✗ 测试推文发送失败")
            print("\n✗ 测试推文发送失败，请查看日志")
            
    except Exception as e:
        logger.error(f"发送测试推文时发生错误: {e}")
        print(f"\n✗ 发送失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Twitter Bot - 5分钟后发推测试")
    print("=" * 60)
    
    # 获取配置的时区
    scheduler_config = config_loader.get_scheduler_config()
    timezone_str = scheduler_config.get('timezone', 'America/New_York')
    tz = pytz_timezone(timezone_str)
    
    # 计算5分钟后的时间
    now = datetime.now(tz)
    run_time = now + timedelta(minutes=5)
    
    print(f"\n当前时间 ({timezone_str}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"计划执行时间: {run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"距离现在: 5 分钟")
    print(f"\n推文内容: Hello from Twitter Bot! 👋 This is a test tweet sent automatically. #TestTweet #Automation")
    
    print("\n" + "-" * 60)
    print("调度器已启动，等待执行...")
    print("按 Ctrl+C 可以取消")
    print("-" * 60)
    
    # 创建调度器
    scheduler = BlockingScheduler(timezone=tz)
    
    # 添加任务：5分钟后执行
    scheduler.add_job(
        send_test_tweet,
        'date',  # 一次性任务
        run_date=run_time,
        id='test_tweet_5min',
        name='5分钟后发推测试'
    )
    
    logger.info(f"测试任务已设置: {run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    try:
        # 启动调度器（阻塞模式）
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n\n任务已取消")
        logger.info("测试任务被用户取消")
        scheduler.shutdown()


if __name__ == "__main__":
    main()

