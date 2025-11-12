"""
测试定时任务调度器
验证时区设置和任务调度功能
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.job_scheduler import job_scheduler
from pytz import timezone as pytz_timezone


def print_separator(title=""):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print('=' * 60)
    else:
        print('-' * 60)


def test_timezone_info():
    """测试时区信息"""
    print_separator("时区信息测试")
    
    # 获取配置的时区
    status = job_scheduler.get_job_status()
    tz_str = status.get('timezone', 'Unknown')
    
    print(f"配置的时区: {tz_str}")
    
    # 显示不同时区的当前时间
    timezones = {
        'America/New_York': '美国东部时间',
        'America/Los_Angeles': '美国太平洋时间',
        'America/Chicago': '美国中部时间',
        'Asia/Shanghai': '中国时间',
        'UTC': '协调世界时'
    }
    
    print("\n当前各时区时间:")
    for tz_name, tz_desc in timezones.items():
        tz = pytz_timezone(tz_name)
        current_time = datetime.now(tz)
        print(f"  {tz_desc:20s} ({tz_name:25s}): {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")


def test_scheduler_status():
    """测试调度器状态"""
    print_separator("调度器状态")
    
    status = job_scheduler.get_job_status()
    
    print(f"运行状态: {'运行中' if status['is_running'] else '已停止'}")
    print(f"任务数量: {status['job_count']}")
    print(f"当前时间: {status['current_time']}")
    print(f"时区设置: {status['timezone']}")
    print(f"下次运行: {status['next_run_time']}")
    print(f"\n发推时间点:")
    for time_point in status['tweet_times']:
        print(f"  - {time_point}")
    
    fixed_content = status.get('fixed_content')
    if fixed_content:
        print(f"\n固定内容: {fixed_content}")
    else:
        print("\n内容生成: 使用 LLM 自动生成")


def test_job_list():
    """测试任务列表"""
    print_separator("定时任务列表")
    
    jobs = job_scheduler.scheduler.get_jobs()
    
    if not jobs:
        print("❌ 没有定时任务")
        return
    
    print(f"共有 {len(jobs)} 个定时任务:\n")
    
    for i, job in enumerate(jobs, 1):
        print(f"任务 {i}:")
        print(f"  ID: {job.id}")
        print(f"  名称: {job.name}")
        print(f"  下次运行: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z') if job.next_run_time else '未知'}")
        print(f"  触发器: {job.trigger}")
        print()


def test_time_calculation():
    """测试时间计算"""
    print_separator("时间计算测试")
    
    # 获取配置的时区
    status = job_scheduler.get_job_status()
    tz = pytz_timezone(status['timezone'])
    
    # 当前时间
    now = datetime.now(tz)
    print(f"当前时间 ({status['timezone']}): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # 计算到下次发推的时间
    tweet_times = status['tweet_times']
    if tweet_times:
        print(f"\n今天的发推时间点:")
        for time_str in tweet_times:
            hour, minute = map(int, time_str.split(':'))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            if target_time < now:
                # 如果今天的时间已过，显示明天的时间
                from datetime import timedelta
                target_time = target_time + timedelta(days=1)
                status_text = "（明天）"
            else:
                status_text = "（今天）"
            
            time_diff = target_time - now
            hours = int(time_diff.total_seconds() // 3600)
            minutes = int((time_diff.total_seconds() % 3600) // 60)
            
            print(f"  {time_str} {status_text}: {target_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"    距离现在: {hours} 小时 {minutes} 分钟")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  Twitter Bot 定时任务调度器测试")
    print("=" * 60)
    
    try:
        # 测试时区信息
        test_timezone_info()
        
        # 测试调度器状态
        test_scheduler_status()
        
        # 测试任务列表
        test_job_list()
        
        # 测试时间计算
        test_time_calculation()
        
        print_separator()
        print("\n✅ 所有测试完成！")
        print("\n提示:")
        print("  - 如果调度器未运行，请启动应用: python app.py")
        print("  - 查看日志: tail -f logs/twitter_bot.log")
        print("  - 手动发推: curl -X POST http://localhost:5000/tweet/post")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

