"""
定时任务调度模块
负责管理自动发推的定时任务
"""

import schedule
import time
import threading
from datetime import datetime
from typing import List, Callable
from utils.config_loader import config_loader
from utils.logger import logger
from llm.llm_client import llm_client
from twitter.api_client import twitter_client


class JobScheduler:
    """定时任务调度器类"""
    
    def __init__(self):
        """初始化调度器"""
        self.scheduler_config = config_loader.get_scheduler_config()
        self.is_running = False
        self.scheduler_thread = None
        self._setup_jobs()
    
    def _setup_jobs(self):
        """设置定时任务"""
        tweet_times = self.scheduler_config.get('tweet_times', ['09:00', '18:00'])
        
        # 清除现有任务
        schedule.clear()
        
        # 为每个时间点设置任务
        for tweet_time in tweet_times:
            try:
                schedule.every().day.at(tweet_time).do(self._auto_tweet_job)
                logger.info(f"已设置定时发推任务: 每天 {tweet_time}")
            except Exception as e:
                logger.error(f"设置定时任务失败 ({tweet_time}): {e}")
        
        logger.info(f"共设置了 {len(tweet_times)} 个定时发推任务")
    
    def _auto_tweet_job(self):
        """自动发推任务"""
        try:
            logger.info("开始执行自动发推任务")
            
            # 生成推文内容
            tweet_content = llm_client.generate_tweet()
            if not tweet_content:
                logger.error("生成推文内容失败，跳过本次发推")
                return
            
            # 发送推文
            result = twitter_client.post_tweet(tweet_content)
            if result and result.get('success'):
                logger.info(f"自动发推成功: {result.get('url')}")
            else:
                logger.error("自动发推失败")
                
        except Exception as e:
            logger.error(f"执行自动发推任务时发生错误: {e}")
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行中")
            return
        
        self.is_running = True
        
        # 在单独的线程中运行调度器
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("定时任务调度器已启动")
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            logger.warning("调度器未在运行")
            return
        
        self.is_running = False
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        
        logger.info("定时任务调度器已停止")
    
    def _run_scheduler(self):
        """运行调度器主循环"""
        logger.info("调度器主循环开始运行")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"调度器运行时发生错误: {e}")
                time.sleep(60)
        
        logger.info("调度器主循环已退出")
    
    def get_next_run_time(self) -> str:
        """
        获取下次运行时间
        
        Returns:
            下次运行时间字符串
        """
        try:
            jobs = schedule.get_jobs()
            if not jobs:
                return "无定时任务"
            
            next_run = min(job.next_run for job in jobs)
            return next_run.strftime("%Y-%m-%d %H:%M:%S")
            
        except Exception as e:
            logger.error(f"获取下次运行时间失败: {e}")
            return "未知"
    
    def get_job_status(self) -> dict:
        """
        获取任务状态信息
        
        Returns:
            任务状态字典
        """
        jobs = schedule.get_jobs()
        
        status = {
            'is_running': self.is_running,
            'job_count': len(jobs),
            'next_run_time': self.get_next_run_time(),
            'tweet_times': self.scheduler_config.get('tweet_times', []),
            'tweets_per_day': self.scheduler_config.get('tweets_per_day', 0)
        }
        
        return status
    
    def manual_tweet(self, custom_content: str = None) -> dict:
        """
        手动触发发推
        
        Args:
            custom_content: 自定义推文内容，如果不提供则自动生成
            
        Returns:
            发推结果字典
        """
        try:
            logger.info("开始手动发推")
            
            # 获取推文内容
            if custom_content:
                tweet_content = custom_content
                logger.info("使用自定义推文内容")
            else:
                tweet_content = llm_client.generate_tweet()
                if not tweet_content:
                    return {
                        'success': False,
                        'error': '生成推文内容失败'
                    }
                logger.info("使用自动生成的推文内容")
            
            # 发送推文
            result = twitter_client.post_tweet(tweet_content)
            
            if result and result.get('success'):
                logger.info(f"手动发推成功: {result.get('url')}")
                return {
                    'success': True,
                    'tweet_id': result.get('id'),
                    'tweet_url': result.get('url'),
                    'content': tweet_content
                }
            else:
                logger.error("手动发推失败")
                return {
                    'success': False,
                    'error': '发送推文失败'
                }
                
        except Exception as e:
            logger.error(f"手动发推时发生错误: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_schedule(self, tweet_times: List[str]):
        """
        更新定时任务时间
        
        Args:
            tweet_times: 新的发推时间列表
        """
        try:
            # 更新配置
            self.scheduler_config['tweet_times'] = tweet_times
            
            # 重新设置任务
            self._setup_jobs()
            
            logger.info(f"定时任务时间已更新: {tweet_times}")
            
        except Exception as e:
            logger.error(f"更新定时任务失败: {e}")


# 全局调度器实例
job_scheduler = JobScheduler()
