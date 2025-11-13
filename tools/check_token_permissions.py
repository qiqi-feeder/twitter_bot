"""
检查 Twitter OAuth 2.0 Token 的权限
诊断工具：显示当前 token 的详细信息和权限范围
"""

import sys
import os
import base64
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.config_loader import config_loader
from utils.proxy import proxy_manager
from utils.logger import logger
import requests


def decode_jwt_payload(token):
    """
    解码 JWT token 的 payload 部分（不验证签名）
    
    Args:
        token: JWT token 字符串
        
    Returns:
        解码后的 payload 字典
    """
    try:
        # JWT 格式: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        # 解码 payload（第二部分）
        payload = parts[1]
        
        # 添加必要的 padding
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        # Base64 解码
        decoded = base64.urlsafe_b64decode(payload)
        
        # JSON 解析
        return json.loads(decoded)
        
    except Exception as e:
        logger.error(f"解码 JWT token 失败: {e}")
        return None


def check_token_info():
    """检查 token 信息"""
    print("\n" + "=" * 60)
    print("  Twitter OAuth 2.0 Token 权限检查")
    print("=" * 60)
    
    # 获取配置
    twitter_config = config_loader.get_twitter_config()
    
    access_token = twitter_config.get('access_token', '').strip()
    refresh_token = twitter_config.get('refresh_token', '').strip()
    client_id = twitter_config.get('client_id', '').strip()
    
    if not access_token:
        print("\n❌ 未找到 access_token")
        print("请运行授权工具: python tools/oauth2_authorize_remote.py")
        return
    
    print(f"\n✅ Access Token: {access_token[:30]}...")
    print(f"✅ Refresh Token: {refresh_token[:30] if refresh_token else 'N/A'}...")
    print(f"✅ Client ID: {client_id[:30] if client_id else 'N/A'}...")
    
    # 解码 access_token
    print("\n" + "-" * 60)
    print("解码 Access Token:")
    print("-" * 60)
    
    payload = decode_jwt_payload(access_token)
    if payload:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        
        # 检查 scopes
        if 'scope' in payload:
            scopes = payload['scope']
            print(f"\n📋 Token Scopes: {scopes}")
            
            # 检查必要的权限
            required_scopes = ['tweet.read', 'tweet.write', 'users.read']
            missing_scopes = []
            
            for scope in required_scopes:
                if scope in scopes:
                    print(f"  ✅ {scope}")
                else:
                    print(f"  ❌ {scope} (缺失)")
                    missing_scopes.append(scope)
            
            if missing_scopes:
                print(f"\n⚠️  缺少必要的权限: {', '.join(missing_scopes)}")
                print("\n解决方法:")
                print("  1. 访问 Twitter Developer Portal")
                print("  2. 检查 App Settings > User authentication settings")
                print("  3. 确保 App permissions 设置为 'Read and Write'")
                print("  4. 重新运行授权: python tools/oauth2_authorize_remote.py")
            else:
                print("\n✅ 所有必要权限都已包含")
        else:
            print("\n⚠️  Token 中未找到 scope 信息")
    else:
        print("⚠️  无法解码 access_token（可能不是 JWT 格式）")
    
    # 尝试调用 Twitter API 获取用户信息
    print("\n" + "-" * 60)
    print("测试 API 调用:")
    print("-" * 60)
    
    try:
        # 获取代理配置
        proxies = None
        if proxy_manager.is_proxy_enabled():
            proxies = proxy_manager.get_proxies()
            print(f"使用代理: {proxies.get('https', 'N/A')}")
        
        # 调用 Twitter API v2 获取当前用户信息
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(
            'https://api.twitter.com/2/users/me',
            headers=headers,
            proxies=proxies,
            timeout=30
        )
        
        print(f"\nHTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ API 调用成功")
            print(f"用户信息: {json.dumps(user_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ API 调用失败")
            print(f"响应内容: {response.text}")
            
            if response.status_code == 403:
                print("\n⚠️  403 Forbidden - 权限不足")
                print("可能原因:")
                print("  1. App 权限设置为 'Read Only'")
                print("  2. Token 是用旧权限生成的")
                print("  3. OAuth 2.0 Scopes 不足")
            elif response.status_code == 401:
                print("\n⚠️  401 Unauthorized - 认证失败")
                print("可能原因:")
                print("  1. Token 已过期")
                print("  2. Token 无效")
                
    except Exception as e:
        print(f"\n❌ API 调用异常: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    try:
        check_token_info()
        
        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

