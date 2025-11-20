"""
真实数据获取模块
从多个可信 API 获取加密货币市场数据
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import requests
from utils.logger import logger
from utils.proxy import proxy_manager


class MarketDataFetcher:
    """市场数据获取器"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # 配置代理
        if proxy_manager.is_proxy_enabled():
            proxies = proxy_manager.get_proxies()
            if proxies:
                self.session.proxies.update(proxies)
                logger.info("数据获取器已配置代理")
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _safe_request(self, url: str, timeout: int = 10) -> Optional[Dict]:
        """安全的 HTTP 请求，带错误处理"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            return None
    
    def fetch_binance_prices(self) -> Dict[str, Any]:
        """从 Binance 获取 BTC 和 ETH 价格"""
        logger.info("获取 Binance 价格数据...")
        
        btc_data = self._safe_request('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
        eth_data = self._safe_request('https://api.binance.com/api/v3/ticker/24hr?symbol=ETHUSDT')
        
        result = {}
        
        if btc_data:
            result['btc'] = {
                'price': round(float(btc_data['lastPrice']), 2),
                'change': round(float(btc_data['priceChangePercent']), 2),
                'volume': round(float(btc_data['quoteVolume']))
            }
        
        if eth_data:
            result['eth'] = {
                'price': round(float(eth_data['lastPrice']), 2),
                'change': round(float(eth_data['priceChangePercent']), 2),
                'volume': round(float(eth_data['quoteVolume']))
            }
        
        logger.info(f"Binance 数据获取成功: BTC ${result.get('btc', {}).get('price')}, ETH ${result.get('eth', {}).get('price')}")
        return result
    
    def fetch_coingecko_global(self) -> Dict[str, Any]:
        """从 CoinGecko 获取全球市场数据"""
        logger.info("获取 CoinGecko 全球市场数据...")
        
        data = self._safe_request('https://api.coingecko.com/api/v3/global')
        
        if not data or 'data' not in data:
            return {}
        
        global_data = data['data']
        result = {
            'market_cap': round(global_data.get('total_market_cap', {}).get('usd', 0)),
            'change': round(global_data.get('market_cap_change_percentage_24h_usd', 0), 2),
            'btc_dominance': round(global_data.get('market_cap_percentage', {}).get('btc', 0), 2),
            'eth_dominance': round(global_data.get('market_cap_percentage', {}).get('eth', 0), 2)
        }
        
        logger.info(f"全球市场数据获取成功: 总市值 ${result['market_cap']:,}")
        return result
    
    def fetch_fear_greed_index(self) -> Dict[str, Any]:
        """获取恐惧贪婪指数"""
        logger.info("获取恐惧贪婪指数...")
        
        data = self._safe_request('https://api.alternative.me/fng/')
        
        if not data or 'data' not in data or len(data['data']) == 0:
            return {}
        
        fng_data = data['data'][0]
        result = {
            'value': int(fng_data.get('value', 50)),
            'classification': fng_data.get('value_classification', 'Neutral')
        }
        
        logger.info(f"恐惧贪婪指数: {result['value']} ({result['classification']})")
        return result

    def fetch_coinglass_liquidation(self) -> Dict[str, Any]:
        """获取爆仓数据（使用 Coinglass 或备用源）"""
        logger.info("获取爆仓数据...")

        # 注意：Coinglass API 可能需要 API key，这里使用模拟数据作为示例
        # 实际使用时需要注册并获取 API key
        # 或者使用其他公开的爆仓数据源

        # 备用方案：使用 CoinGlass 公开数据或其他源
        # 这里返回一个占位符，实际项目中需要配置真实 API
        result = {
            '24h': 0,  # 24小时爆仓金额（美元）
            'long_short_ratio': '1:1',  # 多空比
            'note': 'Coinglass API requires API key - using placeholder'
        }

        logger.warning("爆仓数据使用占位符，需要配置 Coinglass API key")
        return result

    def fetch_l2beat_tvl(self) -> Dict[str, Any]:
        """获取 L2 TVL 数据"""
        logger.info("获取 L2BEAT TVL 数据...")

        data = self._safe_request('https://l2beat.com/api/tvl')

        if not data:
            return {}

        # 提取主要 L2 的 TVL
        result = {}

        # L2BEAT API 返回的数据结构可能变化，这里做基本处理
        if isinstance(data, dict) and 'layers2s' in data:
            for l2 in data['layers2s'][:5]:  # 取前5个
                name = l2.get('name', 'Unknown')
                tvl = l2.get('tvl', {}).get('value', 0)
                result[name.lower()] = {
                    'tvl': round(tvl),
                    'name': name
                }

        logger.info(f"L2 TVL 数据获取成功，共 {len(result)} 个 L2")
        return result

    def fetch_macro_data(self) -> Dict[str, Any]:
        """获取宏观经济数据"""
        logger.info("获取宏观经济数据...")

        # 注意：Yahoo Finance 等需要特殊处理或使用 yfinance 库
        # 这里提供占位符，实际使用时需要配置
        result = {
            'nasdaq': 0,
            'dxy': 0,
            'vix': 0,
            'us10y': 0,
            'gold': 0,
            'oil': 0,
            'note': 'Macro data requires yfinance or other financial API'
        }

        logger.warning("宏观数据使用占位符，建议使用 yfinance 库获取真实数据")
        return result

    def fetch_all_data(self) -> Dict[str, Any]:
        """获取所有市场数据"""
        logger.info("=" * 60)
        logger.info("开始获取所有市场数据...")
        logger.info("=" * 60)

        market_data = {
            'timestamp': datetime.now().isoformat(),
            'price': self.fetch_binance_prices(),
            'global': self.fetch_coingecko_global(),
            'fear_greed': self.fetch_fear_greed_index(),
            'liquidation': self.fetch_coinglass_liquidation(),
            'l2': self.fetch_l2beat_tvl(),
            'macro': self.fetch_macro_data()
        }

        logger.info("=" * 60)
        logger.info("所有市场数据获取完成")
        logger.info("=" * 60)

        return market_data


def fetch_all_market_data(save_to_file: bool = True) -> Dict[str, Any]:
    """
    获取所有市场数据并可选保存到文件

    Args:
        save_to_file: 是否保存到 data/market.json

    Returns:
        市场数据字典
    """
    fetcher = MarketDataFetcher()
    data = fetcher.fetch_all_data()

    if save_to_file:
        # 确保 data 目录存在
        os.makedirs('data', exist_ok=True)

        # 保存到文件
        file_path = 'data/market.json'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"市场数据已保存到: {file_path}")

    return data


if __name__ == '__main__':
    # 测试数据获取
    data = fetch_all_market_data(save_to_file=True)
    print(json.dumps(data, indent=2, ensure_ascii=False))

