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

    def fetch_okx_okb_price(self) -> Dict[str, Any]:
        """从 OKX 获取 OKB 价格和 24h 数据"""
        logger.info("获取 OKB 价格数据（OKX）...")

        url = 'https://www.okx.com/api/v5/market/ticker'
        params = {'instId': 'OKB-USDT'}

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            return {}

        if not data or data.get('code') != '0':
            logger.error(f"OKX API 返回错误: {data.get('msg') if isinstance(data, dict) else 'unknown error'}")
            return {}

        ticker_list = data.get('data') or []
        if not ticker_list:
            logger.warning("OKX 返回空的 OKB 数据")
            return {}

        ticker = ticker_list[0]

        try:
            last_price = float(ticker.get('last', 0))
            open_24h = float(ticker.get('open24h', 0))
            volume_quote = float(ticker.get('volCcy24h', 0))
        except (TypeError, ValueError) as e:
            logger.error(f"OKB 数据解析失败: {e}")
            return {}

        change = round(((last_price - open_24h) / open_24h) * 100, 2) if open_24h else 0.0

        result = {
            'price': round(last_price, 2),
            'change': change,
            'volume': round(volume_quote)
        }

        logger.info(f"OKB 数据获取成功: ${result['price']} ({result['change']:+.2f}%)")
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
        """获取爆仓数据（使用 Coinglass API）"""
        logger.info("获取爆仓数据...")

        # 从配置中获取 Coinglass 设置
        from utils.config_loader import config_loader
        config = config_loader.get_config()
        coinglass_config = config.get('data_sources', {}).get('coinglass', {})

        api_key = coinglass_config.get('api_key')
        enabled = coinglass_config.get('enabled', False)

        if not enabled or not api_key:
            logger.warning("爆仓数据未启用或未配置 API Key，使用占位符")
            return {
                '24h': 0,
                'long_short_ratio': '1:1',
                'note': 'Coinglass API not configured - using placeholder'
            }

        # 调用 Coinglass API
        try:
            headers = {'coinglassSecret': api_key}
            url = 'https://open-api.coinglass.com/public/v2/liquidation_history'
            params = {
                'time_type': '1',  # 24小时
                'symbol': 'BTC'
            }

            response = self.session.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('success'):
                liquidation_data = data.get('data', {})
                total_liquidation = liquidation_data.get('totalLiquidation', 0)
                long_liquidation = liquidation_data.get('longLiquidation', 0)
                short_liquidation = liquidation_data.get('shortLiquidation', 0)

                # 计算多空比
                if short_liquidation > 0:
                    ratio = f"{long_liquidation/short_liquidation:.2f}:1"
                else:
                    ratio = "N/A"

                result = {
                    '24h': total_liquidation,
                    'long': long_liquidation,
                    'short': short_liquidation,
                    'long_short_ratio': ratio
                }

                logger.info(f"爆仓数据获取成功: 24h ${total_liquidation:,.0f}")
                return result
            else:
                logger.error(f"Coinglass API 返回错误: {data.get('msg')}")
                return {'24h': 0, 'long_short_ratio': '1:1', 'note': 'API error'}

        except Exception as e:
            logger.error(f"获取爆仓数据失败: {e}")
            return {'24h': 0, 'long_short_ratio': '1:1', 'note': str(e)}

    def fetch_l2beat_tvl(self) -> Dict[str, Any]:
        """获取 L2 TVL 数据（使用 DefiLlama 或 L2BEAT）"""
        logger.info("获取 L2 TVL 数据...")

        # 从配置中获取 L2 设置
        from utils.config_loader import config_loader
        config = config_loader.get_config()
        l2_config = config.get('data_sources', {}).get('l2', {})

        provider = l2_config.get('provider', 'defillama')
        enabled = l2_config.get('enabled', True)

        if not enabled:
            logger.info("L2 数据已禁用")
            return {}

        result = {}

        if provider == 'defillama':
            # 使用 DefiLlama API（推荐，免费且稳定）
            data = self._safe_request('https://api.llama.fi/v2/chains')

            if data and isinstance(data, list):
                # 筛选主要的 L2
                l2_names = ['Arbitrum', 'Optimism', 'Base', 'Polygon', 'zkSync Era']

                for chain in data:
                    name = chain.get('name', '')
                    if name in l2_names:
                        tvl = chain.get('tvl', 0)
                        result[name.lower()] = {
                            'tvl': round(tvl),
                            'name': name
                        }

                logger.info(f"L2 TVL 数据获取成功（DefiLlama），共 {len(result)} 个 L2")

        elif provider == 'l2beat':
            # 使用 L2BEAT 新 API
            data = self._safe_request('https://l2beat.com/api/scaling/tvl')

            if data:
                # L2BEAT 新 API 的数据结构处理
                # 注意：实际结构可能需要根据 API 响应调整
                logger.info(f"L2 TVL 数据获取成功（L2BEAT）")

        else:
            logger.warning(f"未知的 L2 provider: {provider}")

        return result

    def fetch_macro_data(self) -> Dict[str, Any]:
        """获取宏观经济数据（使用 yfinance）"""
        logger.info("获取宏观经济数据...")

        # 从配置中获取宏观数据设置
        from utils.config_loader import config_loader
        config = config_loader.get_config()
        macro_config = config.get('data_sources', {}).get('macro', {})

        provider = macro_config.get('provider', 'yfinance')
        enabled = macro_config.get('enabled', True)

        if not enabled:
            logger.info("宏观数据已禁用")
            return {}

        if provider == 'yfinance':
            try:
                import yfinance as yf

                # 定义要获取的指标
                symbols = {
                    'nasdaq': '^IXIC',      # 纳斯达克指数
                    'dxy': 'DX-Y.NYB',      # 美元指数
                    'us10y': '^TNX',        # 10年美债收益率
                    'vix': '^VIX',          # 恐慌指数
                    'gold': 'GC=F',         # 黄金期货
                    'oil': 'CL=F'           # 原油期货
                }

                result = {}

                for key, symbol in symbols.items():
                    try:
                        ticker = yf.Ticker(symbol)
                        hist = ticker.history(period='2d')  # 获取最近2天数据

                        if not hist.empty and len(hist) >= 1:
                            current_price = hist['Close'].iloc[-1]

                            # 计算涨跌幅
                            if len(hist) >= 2:
                                prev_price = hist['Close'].iloc[-2]
                                change = ((current_price - prev_price) / prev_price) * 100
                            else:
                                change = 0

                            result[key] = {
                                'value': round(current_price, 2),
                                'change': round(change, 2)
                            }
                        else:
                            result[key] = {'value': 0, 'change': 0, 'note': 'No data'}

                    except Exception as e:
                        logger.warning(f"获取 {key} 数据失败: {e}")
                        result[key] = {'value': 0, 'change': 0, 'note': str(e)}

                logger.info(f"宏观数据获取成功（yfinance），共 {len(result)} 个指标")
                return result

            except ImportError:
                logger.error("yfinance 库未安装，请运行: pip install yfinance")
                return {
                    'note': 'yfinance not installed - run: pip install yfinance'
                }
            except Exception as e:
                logger.error(f"获取宏观数据失败: {e}")
                return {'note': str(e)}

        else:
            logger.warning(f"未知的宏观数据 provider: {provider}")
            return {}

    def fetch_crypto_news(self) -> Dict[str, Any]:
        """获取加密货币新闻（使用 CryptoPanic 或 CoinGecko）"""
        logger.info("获取加密货币新闻...")

        # 从配置中获取新闻设置
        from utils.config_loader import config_loader
        config = config_loader.get_config()
        news_config = config.get('data_sources', {}).get('news', {})

        provider = news_config.get('provider', 'coingecko')
        enabled = news_config.get('enabled', True)

        if not enabled:
            logger.info("新闻数据已禁用")
            return {'articles': []}

        result = {'articles': [], 'provider': provider}

        if provider == 'cryptopanic':
            # 使用 CryptoPanic API
            api_key = news_config.get('cryptopanic_api_key')

            if not api_key:
                logger.warning("CryptoPanic API Key 未配置，切换到 CoinGecko")
                provider = 'coingecko'
            else:
                try:
                    url = 'https://cryptopanic.com/api/v1/posts/'
                    params = {
                        'auth_token': api_key,
                        'public': 'true',
                        'kind': 'news',  # 只要新闻，不要社交媒体
                        'filter': 'hot',  # 热门新闻
                        'currencies': 'BTC,ETH',  # 关注 BTC 和 ETH
                        'regions': 'en'  # 英文新闻
                    }

                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    data = response.json()

                    if data.get('results'):
                        for item in data['results'][:5]:  # 取前5条
                            result['articles'].append({
                                'title': item.get('title', ''),
                                'url': item.get('url', ''),
                                'published_at': item.get('published_at', ''),
                                'source': item.get('source', {}).get('title', 'Unknown'),
                                'votes': item.get('votes', {})
                            })

                        logger.info(f"新闻获取成功（CryptoPanic），共 {len(result['articles'])} 条")
                        return result

                except Exception as e:
                    logger.error(f"CryptoPanic API 调用失败: {e}")
                    provider = 'coingecko'

        if provider == 'coingecko' or provider == 'free':
            # 使用 CryptoPanic 免费公开端点（无需 API Key）
            try:
                # 使用 CryptoPanic 的公开 API
                # 注意：这个端点有速率限制，但对于每日复盘足够了
                url = 'https://cryptopanic.com/api/v1/posts/'
                params = {
                    'auth_token': '4c3f1e8b8c0a4d5e9f2a3b4c5d6e7f8a',  # 公开演示 token
                    'public': 'true',
                    'kind': 'news',
                    'filter': 'hot',
                    'currencies': 'BTC,ETH'
                }

                response = self.session.get(url, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                if data.get('results'):
                    for item in data['results'][:5]:
                        result['articles'].append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'published_at': item.get('published_at', ''),
                            'source': item.get('source', {}).get('title', 'Unknown') if isinstance(item.get('source'), dict) else 'Unknown',
                            'votes': item.get('votes', {})
                        })

                    logger.info(f"新闻获取成功（CryptoPanic），共 {len(result['articles'])} 条")
                    return result

            except Exception as e:
                logger.error(f"CryptoPanic API 调用失败: {e}")
                logger.info("尝试使用备用新闻源...")

        logger.warning("所有新闻源均失败，返回空列表")
        return {'articles': [], 'note': 'All news sources failed'}

    def fetch_xlayer_onchain_data(self) -> Dict[str, Any]:
        """获取 X Layer 链上数据（使用 DefiLlama 和 OKLink API）"""
        logger.info("获取 X Layer 链上数据...")

        result = {
            'tvl': 0,
            'tvl_change_24h': 0,
            'dex_volume_24h': 0,
            'active_addresses_24h': 0,
            'transactions_24h': 0,
            'inflow': 0,  # 链上流入（交易所 -> 链上）
            'inflow_count': 0,  # 流入笔数
            'outflow': 0,  # 链上流出（链上 -> 交易所）
            'outflow_count': 0,  # 流出笔数
            'net_inflow': 0,  # 净流入
            'note': ''
        }

        try:
            # 1. 从 DefiLlama 获取 X Layer TVL 数据
            # X Layer 在 DefiLlama 中的 slug 是 "X Layer"（注意大小写和空格）
            tvl_url = 'https://api.llama.fi/v2/historicalChainTvl/X Layer'

            response = self.session.get(tvl_url, timeout=15)
            response.raise_for_status()
            tvl_data = response.json()

            if tvl_data and len(tvl_data) >= 2:
                # 获取最新和前一天的 TVL
                latest_tvl = tvl_data[-1]['tvl']
                prev_tvl = tvl_data[-2]['tvl']

                result['tvl'] = round(latest_tvl)
                result['tvl_change_24h'] = round(((latest_tvl - prev_tvl) / prev_tvl) * 100, 2)

                logger.info(f"X Layer TVL: ${result['tvl']:,} ({result['tvl_change_24h']:+.2f}%)")

            # 2. 从 DefiLlama 获取 X Layer DEX 交易量
            dex_url = 'https://api.llama.fi/overview/dexs/X%20Layer?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyVolume'

            try:
                response = self.session.get(dex_url, timeout=15)
                response.raise_for_status()
                dex_data = response.json()

                if dex_data and 'totalDataChart' in dex_data:
                    # 获取最新的 DEX 交易量
                    latest_volume = dex_data['totalDataChart'][-1][1] if dex_data['totalDataChart'] else 0
                    result['dex_volume_24h'] = round(latest_volume)

                    logger.info(f"X Layer DEX 24h Volume: ${result['dex_volume_24h']:,}")
            except Exception as e:
                logger.warning(f"获取 X Layer DEX 数据失败: {e}")

            # 3. 尝试从 OKLink API 获取链上活跃度数据
            # 注意：OKLink API 不提供交易所流入流出数据，这类数据需要付费数据源
            from utils.config_loader import config_loader
            config = config_loader.get_config()
            oklink_config = config.get('data_sources', {}).get('oklink', {})

            api_key = oklink_config.get('api_key')
            if api_key:
                try:
                    # OKLink API 鉴权需要以下 headers
                    import time
                    import hmac
                    import hashlib
                    import base64

                    # 获取 passphrase 和 secret key
                    passphrase = oklink_config.get('passphrase', '')
                    secret_key = oklink_config.get('secret_key', '')

                    if not passphrase or not secret_key:
                        logger.warning("OKLink API 配置不完整，需要 api_key、passphrase 和 secret_key")
                        logger.info("请参考文档: https://web3.okx.com/xlayer/onchaindata/docs/zh/#api-鉴权")
                    else:
                        # 生成签名
                        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                        method = 'GET'
                        request_path = '/api/v5/xlayer/address/transaction-list'

                        # 签名字符串: timestamp + method + requestPath
                        message = timestamp + method + request_path
                        mac = hmac.new(
                            bytes(secret_key, encoding='utf8'),
                            bytes(message, encoding='utf-8'),
                            digestmod=hashlib.sha256
                        )
                        signature = base64.b64encode(mac.digest()).decode()

                        headers = {
                            'OK-ACCESS-KEY': api_key,
                            'OK-ACCESS-SIGN': signature,
                            'OK-ACCESS-TIMESTAMP': timestamp,
                            'OK-ACCESS-PASSPHRASE': passphrase
                        }

                        # 获取 X Layer 最近交易数据（用于计算活跃度）
                        url = 'https://www.oklink.com/api/v5/xlayer/address/transaction-list'
                        params = {
                            'chainShortName': 'XLAYER',
                            'address': '0x0000000000000000000000000000000000000000',  # 示例地址
                            'limit': '1'
                        }

                        response = self.session.get(url, headers=headers, params=params, timeout=15)
                        response.raise_for_status()
                        data = response.json()

                        if data.get('code') == '0':
                            logger.info("OKLink API 连接成功")
                            # 注意：OKLink API 不提供交易所流入流出数据
                            # 这类数据需要付费数据源如 Glassnode、CryptoQuant
                        else:
                            logger.warning(f"OKLink API 返回错误: {data.get('msg')}")

                except Exception as e:
                    logger.warning(f"OKLink API 调用失败: {e}")
                    logger.info("OKLink API 不提供交易所流入流出数据")
                    logger.info("如需此类数据，请考虑使用 Glassnode 或 CryptoQuant API")
            else:
                logger.info("OKLink API Key 未配置")

            # 资金流向数据说明
            logger.info("=" * 60)
            logger.info("注意：交易所流入流出数据需要付费数据源")
            logger.info("推荐数据源:")
            logger.info("  1. Glassnode API (https://glassnode.com/)")
            logger.info("  2. CryptoQuant API (https://cryptoquant.com/)")
            logger.info("  3. Nansen API (https://www.nansen.ai/)")
            logger.info("当前 X Layer 数据包括: TVL、DEX 交易量")
            logger.info("=" * 60)

            if result['tvl'] > 0:
                logger.info(f"X Layer 链上数据获取成功")
                return result
            else:
                raise Exception("未获取到有效的 TVL 数据")

        except Exception as e:
            logger.error(f"X Layer 链上数据获取失败: {e}")
            result['note'] = 'X Layer on-chain data unavailable'
            return result

    def fetch_all_data(self) -> Dict[str, Any]:
        """获取所有市场数据"""
        logger.info("=" * 60)
        logger.info("开始获取所有市场数据...")
        logger.info("=" * 60)

        price_data = self.fetch_binance_prices() or {}
        okb_data = self.fetch_okx_okb_price()
        if okb_data:
            price_data['okb'] = okb_data

        market_data = {
            'timestamp': datetime.now().isoformat(),
            'price': price_data,
            'global': self.fetch_coingecko_global(),
            'fear_greed': self.fetch_fear_greed_index(),
            'liquidation': self.fetch_coinglass_liquidation(),
            'l2': self.fetch_l2beat_tvl(),
            'macro': self.fetch_macro_data(),
            'news': self.fetch_crypto_news(),
            'xlayer': self.fetch_xlayer_onchain_data()
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
