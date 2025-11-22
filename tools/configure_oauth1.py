#!/usr/bin/env python3
"""
配置 OAuth 1.0a 凭据到 config.local.yaml
"""
import yaml
from pathlib import Path

def add_oauth1_credentials():
    """添加 OAuth 1.0a 凭据到配置文件"""
    config_path = Path("config/config.local.yaml")
    
    # 读取现有配置
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}
    
    # 确保 twitter 配置存在
    if 'twitter' not in config:
        config['twitter'] = {}
    
    print("=" * 70)
    print("配置 Twitter OAuth 1.0a 凭据（用于媒体上传）")
    print("=" * 70)
    print("\n从 Twitter Developer Portal 获取以下信息：")
    print("https://developer.twitter.com/en/portal/dashboard")
    print("→ 选择您的 App → Keys and tokens\n")
    
    # 获取用户输入
    consumer_key = input("Consumer Key (API Key): ").strip()
    consumer_secret = input("Consumer Secret (API Secret): ").strip()
    access_token = input("Access Token: ").strip()
    access_token_secret = input("Access Token Secret: ").strip()
    
    # 更新配置
    config['twitter']['consumer_key'] = consumer_key
    config['twitter']['consumer_secret'] = consumer_secret
    config['twitter']['access_token_1_0a'] = access_token
    config['twitter']['access_token_secret'] = access_token_secret
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ OAuth 1.0a 凭据已保存到: {config_path}")
    print("\n配置的凭据:")
    print(f"  Consumer Key: {consumer_key[:20]}...")
    print(f"  Consumer Secret: {consumer_secret[:20]}...")
    print(f"  Access Token: {access_token[:20]}...")
    print(f"  Access Token Secret: {access_token_secret[:20]}...")
    print("\n⚠️  请妥善保管这些凭据，不要提交到 git！")

if __name__ == '__main__':
    try:
        add_oauth1_credentials()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
