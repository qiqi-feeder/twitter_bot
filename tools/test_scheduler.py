"""
测试定时任务调度器
验证时区设置和任务调度功能
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pytz import timezone as pytz_timezone
from utils.config_loader import config_loader
from utils.logger import logger


def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def test_timezone_info():
    """测试时区信息"""
    print_separator("时区信息测试")

    # 获取配置的时区
    scheduler_config = config_loader.get_scheduler_config()
    timezone_str = scheduler_config.get('timezone', 'America/New_York')

    print(f"配置的时区: {timezone_str}")
    print()

    # 显示各时区当前时间
    timezones = {
        'America/New_York': '美国东部时间',
        'America/Los_Angeles': '美国太平洋时间',
        'America/Chicago': '美国中部时间',
        'Asia/Shanghai': '中国时间',
        'UTC': '协调世界时'
    }

    print("当前各时区时间:")
    for tz_name, tz_desc in timezones.items():
        tz = pytz_timezone(tz_name)
        current_time = datetime.now(tz)
        print(f"  {tz_desc:20s} ({tz_name:25s}): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def test_scheduler_config():
    """测试调度器配置"""
    print_separator("调度器配置")

    scheduler_config = config_loader.get_scheduler_config()

    print(f"时区设置: {scheduler_config.get('timezone', 'America/New_York')}")
    print(f"每日发推次数: {scheduler_config.get('tweets_per_day', 1)}")
    print(f"发推时间点: {scheduler_config.get('tweet_times', ['08:00'])}")

    fixed_content = scheduler_config.get('fixed_content')
    if fixed_content:
        print(f"固定内容: {fixed_content}")
    else:
        print("固定内容: 未设置（将使用 LLM 生成）")


def test_time_calculation():
    """测试时间计算"""
    print_separator("时间计算测试")

    scheduler_config = config_loader.get_scheduler_config()
    timezone_str = scheduler_config.get('timezone', 'America/New_York')
    tweet_times = scheduler_config.get('tweet_times', ['08:00'])

    tz = pytz_timezone(timezone_str)
    now = datetime.now(tz)

    print(f"当前时间 ({timezone_str}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    print("计划的发推时间:")

    for tweet_time in tweet_times:
        hour, minute = map(int, tweet_time.split(':'))
        print(f"  - 每天 {tweet_time} ({timezone_str})")

        # 计算下次执行时间
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= now:
            # 如果今天的时间已过，计算明天的时间
            next_run = next_run + timedelta(days=1)

        print(f"    下次执行: {next_run.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        # 计算时间差
        time_diff = next_run - now
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        print(f"    距离现在: {hours} 小时 {minutes} 分钟")


def test_scheduler_import():
    """测试调度器导入"""
    print_separator("调度器导入测试")

    try:
        from scheduler.job_scheduler import JobScheduler
        print("✓ JobScheduler 类导入成功")

        # 创建调度器实例（不启动）
        scheduler = JobScheduler()
        print("✓ JobScheduler 实例创建成功")
        print(f"  时区: {scheduler.timezone}")
        print(f"  运行状态: {'运行中' if scheduler.is_running else '未启动'}")

        # 获取任务列表
        jobs = scheduler.scheduler.get_jobs()
        print(f"  已配置任务数: {len(jobs)}")

        for job in jobs:
            print(f"    - {job.name} (ID: {job.id})")
            print(f"      触发器: {job.trigger}")

        return True

    except Exception as e:
        print(f"✗ 调度器导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Twitter Bot 定时任务调度器测试")
    print("=" * 60)

    try:
        # 测试时区信息
        test_timezone_info()

        # 测试调度器配置
        test_scheduler_config()

        # 测试时间计算
        test_time_calculation()

        # 测试调度器导入
        success = test_scheduler_import()

        print_separator("测试完成")
        if success:
            print("✓ 所有测试通过")
            print()
            print("下一步:")
            print("  1. 确保已配置 Twitter OAuth 2.0 凭据")
            print("  2. 运行授权工具获取 Token: python tools/oauth2_authorize_remote.py")
            print("  3. 启动应用: python app.py")
        else:
            print("✗ 部分测试失败，请检查错误信息")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
