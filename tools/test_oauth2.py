#!/usr/bin/env python3
"""
测试 OAuth 2.0 认证和 Token 刷新
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.token_manager import token_manager
from utils.logger import logger
from utils.proxy import proxy_manager


def test_token_loading():
    """测试令牌加载"""
    print("\n🔧 测试 1: 令牌加载")
    print("-" * 60)
    
    access_token = token_manager._access_token
    refresh_token = token_manager._refresh_token
    
    if access_token:
        print(f"✅ Access Token: {access_token[:30]}...")
    else:
        print("❌ Access Token 未配置")
        return False
    
    if refresh_token:
        print(f"✅ Refresh Token: {refresh_token[:30]}...")
    else:
        print("⚠️  Refresh Token 未配置")
    
    return True


def test_token_validation():
    """测试令牌验证"""
    print("\n🔧 测试 2: 令牌验证")
    print("-" * 60)
    
    if token_manager.validate_credentials():
        print("✅ OAuth 2.0 凭据验证通过")
        return True
    else:
        print("❌ OAuth 2.0 凭据验证失败")
        return False


def test_auth_headers():
    """测试认证头部生成"""
    print("\n🔧 测试 3: 认证头部生成")
    print("-" * 60)
    
    headers = token_manager.get_auth_headers()
    
    if headers and 'Authorization' in headers:
        auth_value = headers['Authorization']
        print(f"✅ Authorization Header: {auth_value[:50]}...")
        return True
    else:
        print("❌ 无法生成认证头部")
        return False


def test_token_refresh():
    """测试令牌刷新"""
    print("\n🔧 测试 4: 令牌刷新")
    print("-" * 60)
    
    print("正在测试令牌刷新功能...")
    
    # 获取当前 token
    old_token = token_manager._access_token
    
    # 强制刷新
    if token_manager._refresh_access_token():
        new_token = token_manager._access_token
        
        if new_token and new_token != old_token:
            print(f"✅ 令牌刷新成功")
            print(f"   旧 Token: {old_token[:30]}...")
            print(f"   新 Token: {new_token[:30]}...")
            return True
        elif new_token == old_token:
            print("⚠️  令牌刷新成功，但 Token 未变化（可能是同一个 Token）")
            return True
        else:
            print("❌ 令牌刷新后为空")
            return False
    else:
        print("❌ 令牌刷新失败")
        return False


def test_proxy():
    """测试代理配置"""
    print("\n🔧 测试 5: 代理配置")
    print("-" * 60)
    
    if proxy_manager.is_proxy_enabled():
        proxies = proxy_manager.get_proxies()
        print(f"✅ 代理已启用")
        print(f"   代理地址: {proxies.get('https', 'N/A')}")
        
        # 测试代理连接
        if proxy_manager.test_proxy():
            print("✅ 代理连接测试成功")
            return True
        else:
            print("❌ 代理连接测试失败")
            return False
    else:
        print("ℹ️  代理未启用")
        return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 Twitter OAuth 2.0 认证测试")
    print("=" * 60)
    
    tests = [
        ("令牌加载", test_token_loading),
        ("令牌验证", test_token_validation),
        ("认证头部生成", test_auth_headers),
        ("代理配置", test_proxy),
        ("令牌刷新", test_token_refresh),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print("-" * 60)
    print(f"总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！OAuth 2.0 认证配置正确。")
        return True
    else:
        print(f"\n⚠️  {total - passed} 项测试失败，请检查配置。")
        return False


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

