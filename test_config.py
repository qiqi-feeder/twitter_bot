#!/usr/bin/env python3
"""
配置测试脚本
用于验证系统配置是否正确
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.config_loader import config_loader
from utils.logger import logger
from utils.proxy import proxy_manager
from auth.token_manager import token_manager
from llm.llm_client import llm_client
from twitter.api_client import twitter_client


def test_config_loading():
    """测试配置文件加载"""
    print("🔧 测试配置文件加载...")
    
    try:
        config = config_loader.get_config()
        print("✅ 配置文件加载成功")
        
        # 检查各个配置部分
        sections = ['twitter', 'openai', 'proxy', 'scheduler', 'flask', 'logging']
        for section in sections:
            if section in config:
                print(f"  ✅ {section} 配置存在")
            else:
                print(f"  ❌ {section} 配置缺失")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False


def test_proxy():
    """测试代理配置"""
    print("\n🌐 测试代理配置...")
    
    try:
        if proxy_manager.is_proxy_enabled():
            print("  📡 代理已启用")
            if proxy_manager.test_proxy():
                print("  ✅ 代理连接测试成功")
                return True
            else:
                print("  ❌ 代理连接测试失败")
                return False
        else:
            print("  ℹ️  代理未启用")
            return True
            
    except Exception as e:
        print(f"  ❌ 代理测试失败: {e}")
        return False


def test_twitter_credentials():
    """测试 Twitter 凭据"""
    print("\n🐦 测试 Twitter 凭据...")
    
    try:
        if token_manager.validate_credentials():
            print("  ✅ Twitter 凭据验证通过")
            
            # 测试连接
            if twitter_client.test_connection():
                print("  ✅ Twitter API 连接测试成功")
                
                # 获取用户信息
                user_info = twitter_client.get_user_info()
                if user_info:
                    print(f"  👤 用户信息: @{user_info.get('username')} ({user_info.get('name')})")
                    print(f"  📊 粉丝数: {user_info.get('followers_count', 0)}")
                
                return True
            else:
                print("  ❌ Twitter API 连接测试失败")
                return False
        else:
            print("  ❌ Twitter 凭据验证失败")
            return False
            
    except Exception as e:
        print(f"  ❌ Twitter 测试失败: {e}")
        return False


def test_openai():
    """测试 OpenAI API"""
    print("\n🤖 测试 OpenAI API...")
    
    try:
        if llm_client.validate_api_key():
            print("  ✅ OpenAI API Key 验证通过")
            
            # 测试生成推文
            print("  🔄 测试推文生成...")
            tweet = llm_client.generate_tweet("生成一条简短的测试推文")
            
            if tweet:
                print(f"  ✅ 推文生成成功")
                print(f"  📝 生成内容: {tweet[:50]}{'...' if len(tweet) > 50 else ''}")
                print(f"  📏 内容长度: {len(tweet)} 字符")
                return True
            else:
                print("  ❌ 推文生成失败")
                return False
        else:
            print("  ❌ OpenAI API Key 验证失败")
            return False
            
    except Exception as e:
        print(f"  ❌ OpenAI 测试失败: {e}")
        return False


def test_logging():
    """测试日志系统"""
    print("\n📝 测试日志系统...")
    
    try:
        logger.info("这是一条测试日志信息")
        logger.warning("这是一条测试警告信息")
        print("  ✅ 日志系统工作正常")
        return True
        
    except Exception as e:
        print(f"  ❌ 日志系统测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🧪 Twitter 自动发推系统配置测试")
    print("=" * 60)
    
    tests = [
        ("配置文件加载", test_config_loading),
        ("代理配置", test_proxy),
        ("Twitter 凭据", test_twitter_credentials),
        ("OpenAI API", test_openai),
        ("日志系统", test_logging)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 测试结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统配置正确，可以正常运行。")
        return True
    else:
        print("⚠️  部分测试失败，请检查配置后重试。")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生未知错误: {e}")
        sys.exit(1)
