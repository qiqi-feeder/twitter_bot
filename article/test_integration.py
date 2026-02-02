#!/usr/bin/env python3
"""
Test script to verify the integrated official Gemini API image generation
"""
import sys
import os

# Add project root to path
sys.path.insert(0, '/var/www/myproject/twitter_bot-main')
sys.path.insert(0, '/var/www/myproject/twitter_bot-main/article')

from src.image_factory import image_factory

print("=" * 60)
print("Testing Integrated Image Factory")
print("=" * 60)

test_news = """
币圈深度日报 - 测试版

今日要闻：
1. BTC突破历史新高,市场情绪高涨
2. 多国监管政策趋严，合规成为焦点
3. DeFi锁仓量创新高
"""

print(f"\n测试内容: {test_news[:100]}...")
print(f"\n开始生成封面图...")

result = image_factory.generate_article_cover(test_news)

if result:
    print(f"\n✅ 测试成功！")
    print(f"封面图路径: {result}")
else:
    print(f"\n❌ 测试失败")

print("=" * 60)
