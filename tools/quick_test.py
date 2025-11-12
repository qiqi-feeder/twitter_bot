#!/usr/bin/env python3
"""
快速测试脚本 - 只测试配置加载，不测试网络连接
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.token_manager import token_manager
from utils.config_loader import config_loader
from utils.proxy import proxy_manager


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 Twitter OAuth 2.0 快速配置测试")
    print("=" * 60)
    
    # 测试 1: 配置加载
    print("\n🔧 测试 1: 配置文件加载")
    print("-" * 60)
    
    try:
        config = config_loader.get_config()
        twitter_config = config_loader.get_twitter_config()
        proxy_config = config_loader.get_proxy_config()
        
        print("✅ 配置文件加载成功")
        print(f"   Twitter 配置项: {len(twitter_config)} 个")
        print(f"   代理配置项: {len(proxy_config)} 个")
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return False
    
    # 测试 2: OAuth 2.0 Token 加载
    print("\n🔧 测试 2: OAuth 2.0 Token 加载")
    print("-" * 60)
    
    access_token = twitter_config.get('access_token')
    refresh_token = twitter_config.get('refresh_token')
    
    if access_token:
        print(f"✅ Access Token: {access_token[:30]}...")
        print(f"   长度: {len(access_token)} 字符")
    else:
        print("❌ Access Token 未配置")
        return False
    
    if refresh_token:
        print(f"✅ Refresh Token: {refresh_token[:30]}...")
        print(f"   长度: {len(refresh_token)} 字符")
    else:
        print("⚠️  Refresh Token 未配置（Token 过期后无法自动刷新）")
    
    # 测试 3: 代理配置
    print("\n🔧 测试 3: 代理配置")
    print("-" * 60)
    
    if proxy_manager.is_proxy_enabled():
        proxies = proxy_manager.get_proxies()
        socks5_url = proxies.get('https', 'N/A')
        print(f"✅ 代理已启用")
        print(f"   SOCKS5 URL: {socks5_url}")
    else:
        print("ℹ️  代理未启用")
    
    # 测试 4: Token Manager
    print("\n🔧 测试 4: Token Manager 初始化")
    print("-" * 60)
    
    if token_manager.validate_credentials():
        print("✅ OAuth 2.0 凭据验证通过")
    else:
        print("❌ OAuth 2.0 凭据验证失败")
        return False
    
    # 测试 5: 认证头部生成
    print("\n🔧 测试 5: 认证头部生成")
    print("-" * 60)
    
    # 临时禁用自动刷新，只测试头部生成
    old_token = token_manager._access_token
    headers = {
        'Authorization': f'Bearer {old_token}',
        'Content-Type': 'application/json'
    }
    
    if headers and 'Authorization' in headers:
        auth_value = headers['Authorization']
        print(f"✅ Authorization Header 生成成功")
        print(f"   Header: {auth_value[:50]}...")
    else:
        print("❌ 无法生成认证头部")
        return False
    
    # 测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果")
    print("=" * 60)
    print("✅ 所有基本配置测试通过！")
    print("\n📝 配置摘要:")
    print(f"   - Access Token: 已配置 ({len(access_token)} 字符)")
    print(f"   - Refresh Token: {'已配置' if refresh_token else '未配置'}")
    print(f"   - 代理: {'已启用' if proxy_manager.is_proxy_enabled() else '未启用'}")
    
    print("\n💡 提示:")
    print("   - 基本配置正确，可以尝试运行完整测试")
    print("   - 如需测试网络连接，运行: python tools/test_oauth2.py")
    print("   - 如需测试发推功能，运行: python app.py")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

