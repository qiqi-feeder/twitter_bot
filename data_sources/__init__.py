"""
数据源模块
用于从各种 API 获取真实的加密货币市场数据
"""

from .fetch_real_data import fetch_all_market_data

__all__ = ['fetch_all_market_data']

