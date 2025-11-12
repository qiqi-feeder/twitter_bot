#!/usr/bin/env python3
"""
配置向导 - 帮助用户配置 Twitter OAuth 2.0 凭据
"""

import sys
import yaml
from pathlib import Path


def print_header():
    """打印标题"""
    print("=" * 70)
    print("🔧 Twitter Bot 配置向导")
    print("=" * 70)
    print("\n本向导将帮助您配置 Twitter OAuth 2.0 认证\n")


def print_instructions():
    """打印获取凭据的说明"""
    print("📋 如何获取 Twitter OAuth 2.0 凭据？")
    print("-" * 70)
    print("\n1. 访问 Twitter Developer Portal:")
    print("   🔗 https://developer.twitter.com/en/portal/dashboard\n")
    print("2. 登录您的 Twitter 开发者账号\n")
    print("3. 创建或选择一个应用 (App)\n")
    print("4. 在应用设置中:")
    print("   - 找到 'User authentication settings'")
    print("   - 点击 'Set up' 或 'Edit'")
    print("   - 配置 OAuth 2.0 设置\n")
    print("5. 重要配置:")
    print("   - App permissions: Read and Write")
    print("   - Type of App: Web App, Automated App or Bot")
    print("   - Callback URI: http://localhost:8080/callback")
    print("   - Website URL: http://localhost:5000\n")
    print("6. 保存后，您会看到:")
    print("   - Client ID")
    print("   - Client Secret (只显示一次，请立即保存！)\n")
    print("-" * 70)


def get_input(prompt, required=True, default=""):
    """获取用户输入"""
    while True:
        if default:
            value = input(f"{prompt} [{default}]: ").strip()
            if not value:
                value = default
        else:
            value = input(f"{prompt}: ").strip()
        
        if value or not required:
            return value
        
        print("❌ 此项为必填项，请输入有效值")


def load_config():
    """加载现有配置"""
    config_path = Path("config/config.yaml")
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        print("请确保在项目根目录运行此脚本")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_config(config):
    """保存配置"""
    config_path = Path("config/config.yaml")
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    print(f"\n✅ 配置已保存到: {config_path}")


def main():
    """主函数"""
    print_header()
    
    # 加载现有配置
    config = load_config()
    if not config:
        return
    
    twitter_config = config.get('twitter', {})
    
    # 显示说明
    print_instructions()
    
    print("\n📝 请输入您的 Twitter OAuth 2.0 凭据")
    print("-" * 70)
    
    # 获取 Client ID
    current_client_id = twitter_config.get('client_id', '')
    if current_client_id and current_client_id != 'your_client_id_here':
        print(f"\n当前 Client ID: {current_client_id[:30]}...")
        update = get_input("是否更新 Client ID? (y/N)", required=False, default="N")
        if update.lower() != 'y':
            client_id = current_client_id
        else:
            client_id = get_input("\n请输入新的 Client ID", required=True)
    else:
        client_id = get_input("\n请输入 Client ID", required=True)
    
    # 获取 Client Secret
    current_client_secret = twitter_config.get('client_secret', '')
    if current_client_secret and current_client_secret != 'your_client_secret_here':
        print(f"\n当前 Client Secret: {current_client_secret[:20]}...")
        update = get_input("是否更新 Client Secret? (y/N)", required=False, default="N")
        if update.lower() != 'y':
            client_secret = current_client_secret
        else:
            client_secret = get_input("\n请输入新的 Client Secret", required=False)
    else:
        client_secret = get_input("\n请输入 Client Secret (可选，直接回车跳过)", required=False)
    
    # 更新配置
    twitter_config['client_id'] = client_id
    if client_secret:
        twitter_config['client_secret'] = client_secret
    
    config['twitter'] = twitter_config
    
    # 保存配置
    save_config(config)
    
    # 显示摘要
    print("\n" + "=" * 70)
    print("✅ 配置完成！")
    print("=" * 70)
    print("\n📝 配置摘要:")
    print(f"   Client ID: {client_id[:30]}...")
    if client_secret:
        print(f"   Client Secret: {client_secret[:20]}...")
    else:
        print("   Client Secret: 未配置（公共客户端模式）")
    
    print("\n🚀 下一步:")
    print("   1. 运行授权工具获取 access_token:")
    print("      python tools/oauth2_authorize.py")
    print("\n   2. 或查看详细指南:")
    print("      docs/GET_STARTED.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 配置已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

