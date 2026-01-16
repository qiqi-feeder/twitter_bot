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
from apscheduler.triggers.date import DateTrigger
from pytz import timezone as pytz_timezone
import uuid
from utils.config_loader import config_loader
from utils.logger import logger
import pytz


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

    def setup_crypto_hot_job(self):
        """
        中国时区：每天 00:00 / 08:00 / 16:00
        """
        from get_data.main import run_once

        tz = pytz.timezone("Asia/Shanghai")

        trigger = CronTrigger(
            hour="0,8,16",
            minute=0,
            timezone=tz
        )

        self.scheduler.add_job(
            func=run_once,
            trigger=trigger,
            id="crypto_hot_auto_tweet",
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )

        logger.info("已注册【中国时区】8 小时热点自动推文任务")
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
                # 延迟导入 LLM 客户端
                from llm.llm_client import llm_client
                # 生成推文内容
                tweet_content = llm_client.generate_tweet()
                if not tweet_content:
                    logger.error("生成推文内容失败，跳过本次发推")
                    return
                logger.info("使用 LLM 生成的推文内容")

            # 延迟导入 Twitter 客户端
            from twitter.api_client import twitter_client
            # 发送推文
            result = twitter_client.post_tweet(tweet_content)
            if result and result.get('success'):
                logger.info(f"自动发推成功: {result.get('url')}")
            else:
                logger.error("自动发推失败")

        except Exception as e:
            logger.error(f"执行自动发推任务时发生错误: {e}")

    def _daily_recap_job(self):
        """
        每日大盘复盘任务
        1. 获取市场数据
        2. 生成复盘 Thread
        3. 发布 Thread
        """
        try:
            current_time = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
            logger.info(f"开始执行每日大盘复盘任务 (当前时间: {current_time})")

            # 1. 获取市场数据
            logger.info("步骤 1/3: 获取市场数据...")
            from data_sources.fetch_real_data import fetch_all_market_data
            market_data = fetch_all_market_data(save_to_file=True)

            if not market_data:
                logger.error("获取市场数据失败，跳过本次复盘")
                return

            logger.info("市场数据获取成功")

            # 2. 生成复盘 Thread
            logger.info("步骤 2/3: 生成复盘 Thread...")
            from recap.generate_summary import generate_daily_recap
            thread = generate_daily_recap()

            if not thread:
                logger.error("生成复盘 Thread 失败，跳过本次发布")
                return

            logger.info(f"复盘 Thread 生成成功，共 {len(thread)} 条推文")

            # 3. 发布 Thread
            logger.info("步骤 3/3: 发布 Thread...")
            from recap.post_thread import post_daily_recap_thread
            result = post_daily_recap_thread(thread)

            if result and result.get('success'):
                logger.info(f"每日大盘复盘发布成功！Thread URL: {result.get('thread_url')}")
            else:
                logger.error(f"每日大盘复盘发布失败: {result.get('error')}")

        except Exception as e:
            logger.error(f"执行每日大盘复盘任务时发生错误: {e}")

    def setup_daily_recap_job(self, recap_time: str = "20:00"):
        """
        设置每日大盘复盘任务

        Args:
            recap_time: 复盘时间 (HH:MM 格式)，默认 20:00
        """
        try:
            hour, minute = map(int, recap_time.split(':'))

            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                timezone=self.timezone
            )

            self.scheduler.add_job(
                func=self._daily_recap_job,
                trigger=trigger,
                id='daily_recap',
                name=f'每天 {recap_time} 大盘复盘',
                replace_existing=True
            )

            logger.info(f"已设置每日大盘复盘任务: 每天 {recap_time} ({self.timezone})")

        except Exception as e:
            logger.error(f"设置每日大盘复盘任务失败: {e}")

    def manual_daily_recap(self) -> dict:
        """
        手动触发每日大盘复盘

        Returns:
            执行结果字典
        """
        try:
            logger.info("手动触发每日大盘复盘...")

            # 1. 获取市场数据
            from data_sources.fetch_real_data import fetch_all_market_data
            market_data = fetch_all_market_data(save_to_file=True)

            if not market_data:
                return {
                    'success': False,
                    'error': '获取市场数据失败'
                }

            # 2. 生成复盘 Thread
            from recap.generate_summary import generate_daily_recap
            thread = generate_daily_recap()

            if not thread:
                return {
                    'success': False,
                    'error': '生成复盘 Thread 失败'
                }

            # 3. 发布 Thread
            from recap.post_thread import post_daily_recap_thread
            result = post_daily_recap_thread(thread)

            if result and result.get('success'):
                logger.info(f"手动大盘复盘发布成功: {result.get('thread_url')}")
                return {
                    'success': True,
                    'thread_url': result.get('thread_url'),
                    'tweet_count': result.get('tweet_count'),
                    'tweets': result.get('tweets')
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', '发布失败')
                }

        except Exception as e:
            logger.error(f"手动大盘复盘失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

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
    
    def manual_tweet(self, custom_content: str = None, media_files: list = None, job_id: str = None) -> dict:
        """
        手动触发发推
        
        Args:
            custom_content: 自定义推文内容，如果不提供则自动生成
            media_files: 媒体文件路径列表 (可选)
            job_id: 关联的任务 ID (用于更新历史记录)
            
        Returns:
            发推结果字典
        """
        # 延迟导入以避免循环依赖
        from history.history_manager import history_manager
        
        try:
            logger.info(f"开始手动发推 (Job ID: {job_id})")

            # 获取推文内容
            if custom_content:
                tweet_content = custom_content
                logger.info("使用自定义推文内容")
            else:
                # 延迟导入 LLM 客户端
                from llm.llm_client import llm_client
                tweet_content = llm_client.generate_tweet()
                if not tweet_content:
                    if job_id:
                        history_manager.update_status(job_id, 'failed', error='生成推文内容失败')
                    return {
                        'success': False,
                        'error': '生成推文内容失败'
                    }
                logger.info("使用自动生成的推文内容")

            # 延迟导入 Twitter 客户端
            from twitter.api_client import twitter_client
            # 发送推文
            result = twitter_client.post_tweet(tweet_content, media_paths=media_files)

            if result and result.get('success'):
                logger.info(f"手动发推成功: {result.get('url')}")
                if job_id:
                    history_manager.update_status(
                        job_id, 
                        'sent', 
                        tweet_id=result.get('id'), 
                        tweet_url=result.get('url')
                    )
                return {
                    'success': True,
                    'tweet_id': result.get('id'),
                    'tweet_url': result.get('url'),
                    'content': tweet_content
                }
            else:
                error_msg = '发送推文失败'
                logger.error(error_msg)
                if job_id:
                    history_manager.update_status(job_id, 'failed', error=error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"手动发推时发生错误: {e}")
            if job_id:
                history_manager.update_status(job_id, 'failed', error=str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    def schedule_one_off_tweet(self, content: str, scheduled_time: str, media_files: list = None, timezone_str: str = 'America/New_York') -> dict:
        """
        安排一次性发推任务
        
        Args:
            content: 推文内容
            scheduled_time: 计划发送时间 (ISO 格式字符串, e.g., '2023-01-01T12:00')
            media_files: 媒体文件路径列表 (可选)
            timezone_str: 时区字符串
            
        Returns:
            结果字典
        """
        # 延迟导入以避免循环依赖
        from history.history_manager import history_manager
        
        try:
            # 解析时间
            tz = pytz_timezone(timezone_str)
            # 前端传来的 datetime-local 格式通常是 'YYYY-MM-DDTHH:MM'
            run_date = datetime.fromisoformat(scheduled_time)
            
            # 如果时间没有时区信息，假定为指定时区
            if run_date.tzinfo is None:
                run_date = tz.localize(run_date)
            
            # 生成唯一 Job ID
            job_id = f"one_off_{uuid.uuid4().hex}"
            
            # 添加任务
            self.scheduler.add_job(
                func=self.manual_tweet,
                trigger=DateTrigger(run_date=run_date, timezone=tz),
                args=[content, media_files, job_id],  # 传递 job_id
                id=job_id,
                name=f'定时发推: {content[:20]}...'
            )
            
            # 记录到历史
            history_manager.add_record(
                job_id=job_id,
                content=content,
                scheduled_time=run_date.isoformat(),
                status='pending',
                media_files=media_files
            )
            
            logger.info(f"已安排定时发推任务: {run_date} (ID: {job_id})")
            
            return {
                'success': True,
                'message': f'推文已安排在 {run_date.strftime("%Y-%m-%d %H:%M:%S %Z")} 发送',
                'job_id': job_id,
                'scheduled_time': run_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"安排定时发推任务失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_job(self, job_id: str) -> dict:
        """
        取消任务
        
        Args:
            job_id: 任务 ID
            
        Returns:
            结果字典
        """
        from history.history_manager import history_manager
        
        try:
            # 检查任务是否存在于调度器中
            job = self.scheduler.get_job(job_id)
            if job:
                self.scheduler.remove_job(job_id)
                logger.info(f"已取消调度器任务: {job_id}")
            else:
                logger.warning(f"调度器中未找到任务: {job_id} (可能已执行或不存在)")
            
            # 更新历史记录状态
            history_manager.update_status(job_id, 'cancelled')
            
            return {
                'success': True,
                'message': '任务已取消'
            }
            
        except Exception as e:
            logger.error(f"取消任务失败: {e}")
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
