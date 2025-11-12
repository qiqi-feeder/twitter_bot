"""
定时任务调度模块
负责管理自动发推的定时任务
支持时区设置，可按照指定时区（如美国时间）执行任务
"""

import time
import threading
from datetime import datetime
from typing import List, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone as pytz_timezone
from utils.config_loader import config_loader
from utils.logger import logger
from llm.llm_client import llm_client
from twitter.api_client import twitter_client


class JobScheduler:
    """定时任务调度器类 - 支持时区设置"""

    def __init__(self):
        """初始化调度器"""
        self.scheduler_config = config_loader.get_scheduler_config()
        self.is_running = False

        # 获取时区设置
        timezone_str = self.scheduler_config.get('timezone', 'America/New_York')
        self.timezone = pytz_timezone(timezone_str)

        # 创建 APScheduler 调度器
        self.scheduler = BackgroundScheduler(timezone=self.timezone)

        # 设置定时任务
        self._setup_jobs()

        logger.info(f"调度器初始化完成，时区: {timezone_str}")

    def _setup_jobs(self):
        """设置定时任务"""
        tweet_times = self.scheduler_config.get('tweet_times', ['08:00'])
        fixed_content = self.scheduler_config.get('fixed_content', None)

        # 清除现有任务
        self.scheduler.remove_all_jobs()

        # 为每个时间点设置任务
        for tweet_time in tweet_times:
            try:
                # 解析时间 (HH:MM)
                hour, minute = map(int, tweet_time.split(':'))

                # 创建 cron 触发器
                trigger = CronTrigger(
                    hour=hour,
                    minute=minute,
                    timezone=self.timezone
                )

                # 添加任务
                self.scheduler.add_job(
                    func=self._auto_tweet_job,
                    trigger=trigger,
                    args=[fixed_content],
                    id=f'tweet_{tweet_time}',
                    name=f'每天 {tweet_time} 发推',
                    replace_existing=True
                )

                logger.info(f"已设置定时发推任务: 每天 {tweet_time} ({self.timezone})")
            except Exception as e:
                logger.error(f"设置定时任务失败 ({tweet_time}): {e}")

        logger.info(f"共设置了 {len(tweet_times)} 个定时发推任务")
    
    def _auto_tweet_job(self, fixed_content=None):
        """
        自动发推任务

        Args:
            fixed_content: 固定内容，如果提供则使用固定内容，否则使用 LLM 生成
        """
        try:
            current_time = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
            logger.info(f"开始执行自动发推任务 (当前时间: {current_time})")

            # 获取推文内容
            if fixed_content:
                tweet_content = fixed_content
                logger.info("使用固定推文内容")
            else:
                # 生成推文内容
                tweet_content = llm_client.generate_tweet()
                if not tweet_content:
                    logger.error("生成推文内容失败，跳过本次发推")
                    return
                logger.info("使用 LLM 生成的推文内容")

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

        try:
            self.scheduler.start()
            self.is_running = True
            logger.info("定时任务调度器已启动")

            # 显示下次运行时间
            next_run = self.get_next_run_time()
            logger.info(f"下次发推时间: {next_run}")

        except Exception as e:
            logger.error(f"启动调度器失败: {e}")

    def stop(self):
        """停止调度器"""
        if not self.is_running:
            logger.warning("调度器未在运行")
            return

        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("定时任务调度器已停止")

        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    def get_next_run_time(self) -> str:
        """
        获取下次运行时间

        Returns:
            下次运行时间字符串
        """
        try:
            jobs = self.scheduler.get_jobs()
            if not jobs:
                return "无定时任务"

            # 获取所有任务的下次运行时间
            next_runs = [job.next_run_time for job in jobs if job.next_run_time]
            if not next_runs:
                return "无定时任务"

            next_run = min(next_runs)
            return next_run.strftime("%Y-%m-%d %H:%M:%S %Z")

        except Exception as e:
            logger.error(f"获取下次运行时间失败: {e}")
            return "未知"

    def get_job_status(self) -> dict:
        """
        获取任务状态信息

        Returns:
            任务状态字典
        """
        jobs = self.scheduler.get_jobs()

        # 获取当前时区时间
        current_time = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

        status = {
            'is_running': self.is_running,
            'job_count': len(jobs),
            'next_run_time': self.get_next_run_time(),
            'current_time': current_time,
            'timezone': str(self.timezone),
            'tweet_times': self.scheduler_config.get('tweet_times', []),
            'tweets_per_day': self.scheduler_config.get('tweets_per_day', 0),
            'fixed_content': self.scheduler_config.get('fixed_content', None)
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
    
    def update_schedule(self, tweet_times: List[str] = None, fixed_content: str = None, timezone_str: str = None):
        """
        更新定时任务配置

        Args:
            tweet_times: 新的发推时间列表
            fixed_content: 固定推文内容
            timezone_str: 时区字符串（如 'America/New_York'）
        """
        try:
            # 更新配置
            if tweet_times is not None:
                self.scheduler_config['tweet_times'] = tweet_times

            if fixed_content is not None:
                self.scheduler_config['fixed_content'] = fixed_content

            if timezone_str is not None:
                self.scheduler_config['timezone'] = timezone_str
                self.timezone = pytz_timezone(timezone_str)
                # 重新创建调度器以应用新时区
                if self.is_running:
                    self.scheduler.shutdown(wait=False)
                self.scheduler = BackgroundScheduler(timezone=self.timezone)

            # 重新设置任务
            self._setup_jobs()

            # 如果之前在运行，重新启动
            if self.is_running and timezone_str is not None:
                self.scheduler.start()

            logger.info(f"定时任务配置已更新")
            if tweet_times:
                logger.info(f"  发推时间: {tweet_times}")
            if fixed_content:
                logger.info(f"  固定内容: {fixed_content[:50]}...")
            if timezone_str:
                logger.info(f"  时区: {timezone_str}")

        except Exception as e:
            logger.error(f"更新定时任务失败: {e}")


# 全局调度器实例
job_scheduler = JobScheduler()
