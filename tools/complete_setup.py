#!/usr/bin/env python3
"""
完整设置流程 - 一键完成配置和授权
"""

import sys
import subprocess
from pathlib import Path


def print_header():
    """打印标题"""
    print("=" * 70)
    print("🚀 Twitter Bot 完整设置向导")
    print("=" * 70)
    print("\n本向导将引导您完成以下步骤:")
    print("   1. 配置 Twitter OAuth 2.0 凭据 (Client ID & Secret)")
    print("   2. 运行授权流程获取 access_token")
    print("   3. 验证配置是否正确")
    print()


def run_step(step_name, script_path, description):
    """运行一个步骤"""
    print("\n" + "=" * 70)
    print(f"📋 {step_name}")
    print("=" * 70)
    print(f"{description}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=Path(__file__).parent.parent,
            check=False
        )
        
        if result.returncode != 0:
            print(f"\n⚠️  {step_name} 未成功完成")
            response = input("是否继续下一步? (y/N): ").strip().lower()
            if response != 'y':
                return False
        
        return True
    
    except Exception as e:
        print(f"\n❌ 运行 {step_name} 时出错: {e}")
        return False


def main():
    """主函数"""
    print_header()
    
    # 步骤 1: 配置凭据
    if not run_step(
        "步骤 1: 配置 OAuth 2.0 凭据",
        "tools/setup_config.py",
        "请输入您的 Twitter App Client ID 和 Client Secret"
    ):
        print("\n❌ 设置已取消")
        return
    
    # 步骤 2: 运行授权
    print("\n" + "=" * 70)
    print("📋 步骤 2: OAuth 2.0 授权")
    print("=" * 70)
    print("接下来将打开浏览器进行授权\n")
    
    response = input("准备好了吗? 按回车继续...").strip()
    
    if not run_step(
        "步骤 2: OAuth 2.0 授权",
        "tools/oauth2_authorize.py",
        "请在浏览器中完成授权"
    ):
        print("\n⚠️  授权未完成")
        print("您可以稍后手动运行: python tools/oauth2_authorize.py")
        return
    
    # 步骤 3: 验证配置
    if not run_step(
        "步骤 3: 验证配置",
        "tools/quick_test.py",
        "验证配置是否正确"
    ):
        print("\n⚠️  配置验证未通过")
        print("请检查配置文件: config/config.yaml")
        return
    
    # 完成
    print("\n" + "=" * 70)
    print("🎉 设置完成！")
    print("=" * 70)
    print("\n您的 Twitter Bot 已经配置完成，可以开始使用了！\n")
    print("🚀 启动应用:")
    print("   python app.py")
    print("\n📖 查看文档:")
    print("   README.md - 项目说明")
    print("   docs/GET_STARTED.md - 快速开始")
    print("   docs/OAUTH2_GUIDE.md - OAuth 2.0 详细指南")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 设置已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()

