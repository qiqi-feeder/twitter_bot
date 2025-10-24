#!/usr/bin/env python3
"""
Twitter 自动发推系统启动脚本
提供更友好的启动方式和错误处理
"""

import os
import sys
import subprocess
from pathlib import Path


def check_python_version():
    """检查 Python 版本"""
    if sys.version_info < (3, 9):
        print("❌ 错误: 需要 Python 3.9 或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    
    print(f"✅ Python 版本检查通过: {sys.version.split()[0]}")
    return True


def check_dependencies():
    """检查依赖是否安装"""
    try:
        import flask
        import requests
        import schedule
        import yaml
        import openai
        import tweepy
        
        print("✅ 依赖包检查通过")
        return True
        
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("请运行: pip install -r requirements.txt")
        return False


def check_config():
    """检查配置文件"""
    config_path = Path("config/config.yaml")
    
    if not config_path.exists():
        print("❌ 配置文件不存在: config/config.yaml")
        return False
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 检查必要的配置项
        required_sections = ['twitter', 'openai', 'proxy', 'scheduler', 'flask', 'logging']
        missing_sections = []
        
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ 配置文件缺少必要部分: {', '.join(missing_sections)}")
            return False
        
        print("✅ 配置文件检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置文件格式错误: {e}")
        return False


def create_directories():
    """创建必要的目录"""
    directories = ['logs']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ 目录结构检查通过")


def main():
    """主函数"""
    print("🚀 Twitter 自动发推系统启动检查")
    print("=" * 50)
    
    # 检查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查配置
    if not check_config():
        sys.exit(1)
    
    # 创建目录
    create_directories()
    
    print("=" * 50)
    print("✅ 所有检查通过，正在启动系统...")
    print()
    
    try:
        # 启动主应用
        os.system("python app.py")
        
    except KeyboardInterrupt:
        print("\n👋 系统已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
