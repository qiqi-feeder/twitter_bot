#!/usr/bin/env python3
"""
远程服务器 OAuth 2.0 授权工具
适用于通过 SSH 连接的远程服务器环境
"""

import sys
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from auth.oauth2_client import OAuth2Client
from utils.proxy import ProxyManager
from utils.config_loader import ConfigLoader


def load_config():
    """加载配置文件（支持 config.local.yaml 覆盖）"""
    # 切换到项目根目录，确保相对路径正确
    import os
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    config_path = project_root / "config" / "config.yaml"
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return None
    
    # 使用 ConfigLoader 以支持 config.local.yaml 覆盖
    try:
        config_loader = ConfigLoader(str(config_path))
        return config_loader.load_config()
    except Exception as e:
        print(f"❌ 加载配置文件失败: {e}")
        return None


def save_tokens(access_token, refresh_token, expires_in):
    """保存令牌到配置文件（保存到 config.local.yaml）"""
    # 保存到 config.local.yaml，而不是覆盖 config.yaml
    project_root = Path(__file__).parent.parent
    local_config_path = project_root / "config" / "config.local.yaml"
    
    # 读取现有的 local config（如果存在）
    if local_config_path.exists():
        with open(local_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    
    # 计算过期时间
    from datetime import datetime, timedelta
    expires_at = datetime.now() + timedelta(seconds=expires_in)
    
    # 确保 twitter 配置存在
    if 'twitter' not in config:
        config['twitter'] = {}
    
    # 更新配置
    config['twitter']['access_token'] = access_token
    config['twitter']['refresh_token'] = refresh_token
    config['twitter']['token_expires_at'] = expires_at.isoformat()
    
    # 保存配置
    with open(local_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ 令牌已保存到: {local_config_path}")
    print(f"   Access Token: {access_token[:30]}...")
    print(f"   Refresh Token: {refresh_token[:30]}...")
    print(f"   过期时间: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """主函数"""
    print("=" * 70)
    print("🔐 Twitter OAuth 2.0 授权工具 (远程服务器版)")
    print("=" * 70)
    print("\n本工具适用于通过 SSH 连接的远程服务器环境")
    print("您需要在本地浏览器中完成授权，然后手动复制授权码\n")
    
    # 加载配置
    print("📋 检查配置...")
    print("-" * 70)
    
    config = load_config()
    if not config:
        print("\n💡 提示: 请先配置 Client ID 和 Client Secret")
        print("   详细步骤请参考: docs/GET_STARTED.md")
        return
    
    twitter_config = config.get('twitter', {})
    
    # 获取 Client ID
    client_id = twitter_config.get('client_id', '').strip()
    if not client_id or client_id == 'your_client_id_here':
        print("❌ 未配置有效的 Client ID\n")
        print("📝 配置步骤:")
        print("   1. 访问 https://developer.twitter.com/en/portal/dashboard")
        print("   2. 创建或选择您的应用")
        print("   3. 在 'Keys and tokens' 或 'Settings' 中找到 OAuth 2.0 Client ID")
        print("   4. 编辑 config/config.yaml，将 Client ID 填入 twitter.client_id")
        print("\n详细指南: docs/GET_STARTED.md")
        return
    
    print(f"✅ Client ID: {client_id[:30]}...")
    
    # 获取 Client Secret（可选）
    client_secret = twitter_config.get('client_secret', '').strip()
    if not client_secret or client_secret == 'your_client_secret_here':
        print("⚠️  未配置 Client Secret（将使用公共客户端模式）")
        client_secret = None
    else:
        print(f"✅ Client Secret: {client_secret[:20]}...")
    
    # 回调 URI - 远程服务器使用特殊的回调 URI
    redirect_uri = "http://localhost:5050/callback"
    
    # 获取代理配置
    proxy_manager = ProxyManager()
    proxies = proxy_manager.get_proxies() if proxy_manager.is_proxy_enabled() else None
    
    # 创建 OAuth 2.0 客户端
    oauth_client = OAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        proxies=proxies
    )
    
    # 生成授权 URL
    print("\n📋 步骤 1: 获取授权 URL")
    print("-" * 70)
    
    scopes = ['tweet.read', 'tweet.write', 'users.read', 'offline.access']
    auth_url = oauth_client.get_authorization_url(scopes=scopes)
    
    print(f"\n请在您的本地浏览器中打开以下 URL 进行授权：\n")
    print(f"🔗 {auth_url}\n")
    print("=" * 70)
    print("\n📌 授权步骤:")
    print("   1. 复制上面的 URL")
    print("   2. 在您的本地电脑浏览器中打开")
    print("   3. 登录您的 Twitter 账号（如果未登录）")
    print("   4. 点击 'Authorize app' 授权应用")
    print("   5. 浏览器会跳转到 http://localhost:8080/callback?code=...")
    print("   6. 虽然页面无法加载，但 URL 中包含授权码")
    print("   7. 从 URL 中复制 'code=' 后面的内容（授权码）\n")
    
    print("示例:")
    print("   URL: http://localhost:8080/callback?code=ABC123XYZ&state=...")
    print("   授权码: ABC123XYZ")
    print("=" * 70)
    
    # 等待用户输入授权码
    print("\n📋 步骤 2: 输入授权码")
    print("-" * 70)
    
    authorization_code = input("\n请粘贴授权码 (code): ").strip()
    
    if not authorization_code:
        print("\n❌ 未输入授权码")
        return
    
    print(f"\n✅ 收到授权码: {authorization_code[:20]}...")
    
    # 交换访问令牌
    print("\n📋 步骤 3: 交换访问令牌")
    print("-" * 70)
    
    token_data = oauth_client.exchange_code_for_token(authorization_code)
    
    if not token_data:
        print("\n❌ 交换访问令牌失败")
        print("\n可能的原因:")
        print("   1. 授权码已过期（授权码只能使用一次，且有效期很短）")
        print("   2. 授权码复制不完整")
        print("   3. 网络连接问题")
        print("\n请重新运行此工具获取新的授权码")
        return
    
    # 提取令牌信息
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    expires_in = token_data.get('expires_in', 7200)
    token_type = token_data.get('token_type')
    scope = token_data.get('scope')
    
    print(f"\n✅ 成功获取访问令牌！")
    print(f"   Token 类型: {token_type}")
    print(f"   权限范围: {scope}")
    print(f"   有效期: {expires_in} 秒 ({expires_in // 3600} 小时)")
    
    # 保存令牌
    print("\n📋 步骤 4: 保存令牌到配置文件")
    print("-" * 70)
    
    save_tokens(access_token, refresh_token, expires_in)
    
    print("\n" + "=" * 70)
    print("🎉 OAuth 2.0 授权完成！")
    print("=" * 70)
    print("\n您现在可以使用 Twitter 自动发推系统了。")
    print("运行 'python app.py' 启动系统。\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 授权已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

