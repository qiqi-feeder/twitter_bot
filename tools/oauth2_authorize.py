#!/usr/bin/env python3
"""
Twitter OAuth 2.0 授权辅助工具
帮助用户完成 OAuth 2.0 授权流程，获取 access_token 和 refresh_token
"""

import sys
import os
import yaml
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.oauth2_client import OAuth2Client
from utils.proxy import proxy_manager
from utils.logger import logger


class CallbackHandler(BaseHTTPRequestHandler):
    """处理 OAuth 2.0 回调的 HTTP 服务器"""
    
    authorization_code = None
    state = None
    error = None
    
    def do_GET(self):
        """处理 GET 请求"""
        # 解析 URL
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        
        # 提取参数
        CallbackHandler.authorization_code = params.get('code', [None])[0]
        CallbackHandler.state = params.get('state', [None])[0]
        CallbackHandler.error = params.get('error', [None])[0]
        
        # 发送响应
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        if CallbackHandler.error:
            error_desc = params.get('error_description', [''])[0]
            html = f"""
            <html>
            <head><title>授权失败</title></head>
            <body>
                <h1>❌ 授权失败</h1>
                <p>错误: {CallbackHandler.error}</p>
                <p>描述: {error_desc}</p>
                <p>请关闭此窗口并重试。</p>
            </body>
            </html>
            """
        elif CallbackHandler.authorization_code:
            html = """
            <html>
            <head><title>授权成功</title></head>
            <body>
                <h1>✅ 授权成功！</h1>
                <p>已收到授权码，正在交换访问令牌...</p>
                <p>请返回终端查看结果。</p>
                <p>您可以关闭此窗口。</p>
            </body>
            </html>
            """
        else:
            html = """
            <html>
            <head><title>授权失败</title></head>
            <body>
                <h1>❌ 未收到授权码</h1>
                <p>请关闭此窗口并重试。</p>
            </body>
            </html>
            """
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """禁用默认的日志输出"""
        pass


def load_config():
    """加载配置文件"""
    config_path = Path("config/config.yaml")
    if not config_path.exists():
        print("❌ 配置文件不存在: config/config.yaml")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_tokens(access_token: str, refresh_token: str, expires_in: int):
    """保存令牌到配置文件"""
    config_path = Path("config/config.yaml")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    if 'twitter' not in config:
        config['twitter'] = {}
    
    config['twitter']['access_token'] = access_token
    config['twitter']['refresh_token'] = refresh_token
    
    # 计算过期时间
    from datetime import datetime, timedelta
    expires_at = datetime.now() + timedelta(seconds=expires_in)
    config['twitter']['token_expires_at'] = expires_at.isoformat()
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
    
    print(f"✅ 令牌已保存到配置文件")
    print(f"   Access Token: {access_token[:20]}...")
    print(f"   Refresh Token: {refresh_token[:20]}...")
    print(f"   过期时间: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """主函数"""
    print("🔐 Twitter OAuth 2.0 授权工具")
    print("=" * 60)
    
    # 加载配置
    config = load_config()
    if not config:
        return
    
    twitter_config = config.get('twitter', {})
    
    # 获取 Client ID
    client_id = twitter_config.get('client_id')
    if not client_id:
        print("❌ 配置文件中未找到 client_id")
        print("请在 config/config.yaml 中配置 twitter.client_id")
        return
    
    # 获取 Client Secret（可选）
    client_secret = twitter_config.get('client_secret')
    
    # 回调 URI
    redirect_uri = "http://localhost:8080/callback"
    
    # 获取代理配置
    proxies = proxy_manager.get_proxies() if proxy_manager.is_proxy_enabled() else None
    
    # 创建 OAuth 2.0 客户端
    oauth_client = OAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        proxies=proxies
    )
    
    # 生成授权 URL
    print("\n📋 步骤 1: 获取授权")
    print("-" * 60)
    
    scopes = ['tweet.read', 'tweet.write', 'users.read', 'offline.access']
    auth_url = oauth_client.get_authorization_url(scopes=scopes)
    
    print(f"\n请在浏览器中打开以下 URL 进行授权：\n")
    print(f"🔗 {auth_url}\n")
    print("授权后，浏览器将自动跳转到本地回调地址。")
    print("请不要关闭此程序，等待授权完成...\n")

    # 启动本地 HTTP 服务器接收回调
    print("📡 启动本地回调服务器 (http://localhost:8080)...")
    server = HTTPServer(('localhost', 8080), CallbackHandler)

    # 等待一次请求
    server.handle_request()

    # 检查是否收到授权码
    if CallbackHandler.error:
        print(f"\n❌ 授权失败: {CallbackHandler.error}")
        return

    if not CallbackHandler.authorization_code:
        print("\n❌ 未收到授权码")
        return

    # 验证 state
    if not oauth_client.verify_state(CallbackHandler.state):
        print("\n❌ State 验证失败，可能存在安全风险")
        return

    print("\n✅ 收到授权码")

    # 步骤 2: 交换访问令牌
    print("\n📋 步骤 2: 交换访问令牌")
    print("-" * 60)

    token_data = oauth_client.exchange_code_for_token(CallbackHandler.authorization_code)

    if not token_data:
        print("\n❌ 交换访问令牌失败")
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

    # 步骤 3: 保存令牌
    print("\n📋 步骤 3: 保存令牌到配置文件")
    print("-" * 60)

    save_tokens(access_token, refresh_token, expires_in)

    print("\n" + "=" * 60)
    print("🎉 OAuth 2.0 授权完成！")
    print("=" * 60)
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

