# API Keys 配置指南

本文档详细说明如何获取和配置所有需要的 API Key。

---

## 📊 当前状态

| 数据源 | 状态 | 是否必需 | 说明 |
|--------|------|----------|------|
| ✅ Binance | 已配置 | 必需 | BTC/ETH 价格数据（无需 API Key） |
| ✅ CoinGecko | 已配置 | 必需 | 全球市值数据（无需 API Key） |
| ✅ Fear & Greed Index | 已配置 | 必需 | 恐惧贪婪指数（无需 API Key） |
| ⚠️ Coinglass | **未配置** | 可选 | 爆仓数据 |
| ✅ DefiLlama | 已配置 | 推荐 | Layer 2 TVL 数据（无需 API Key） |
| ✅ yfinance | 已配置 | 推荐 | 美股、美债、黄金、原油等（无需 API Key） |
| ✅ CoinGecko News | 已配置 | 推荐 | 加密货币新闻（无需 API Key） |
| ⚠️ Coinglass | **未配置** | 可选 | 爆仓数据 |
| ⚠️ CryptoPanic | **未配置** | 可选 | 专业加密新闻（更详细） |

---

## 1️⃣ Coinglass API - 爆仓数据

### 📌 获取步骤

1. **访问官网**：https://www.coinglass.com/
2. **注册账号**：点击右上角 "Sign Up"
3. **获取 API Key**：
   - 登录后访问：https://www.coinglass.com/api
   - 或者进入 "Account" → "API Management"
   - 点击 "Create API Key"
   - 复制生成的 API Key

### 💰 价格

- **免费版**：每天 100 次请求（足够日常使用）
- **付费版**：$29/月起，更高请求限制

### ⚙️ 配置方法

在 `config/config.local.yaml` 中添加：

```yaml
data_sources:
  coinglass:
    api_key: "your_coinglass_api_key_here"
    enabled: true
```

### 📝 API 文档

- 官方文档：https://www.coinglass.com/api/docs
- 爆仓数据端点：`/api/futures/liquidation_history`

---

## 2️⃣ L2BEAT API - Layer 2 TVL 数据

### ⚠️ 当前问题

L2BEAT 的公开 API 端点已变更，原 `https://l2beat.com/api/tvl` 返回 404。

### 🔧 解决方案

**方案 1：使用新的 API 端点**

L2BEAT 现在使用 GitHub 托管的 JSON 数据：

```
https://l2beat.com/api/scaling/tvl
```

**方案 2：使用 DefiLlama API（推荐）**

DefiLlama 提供免费的 L2 TVL 数据，无需 API Key：

```
https://api.llama.fi/v2/chains
```

### ⚙️ 配置方法

在 `config/config.local.yaml` 中添加：

```yaml
data_sources:
  l2:
    provider: "defillama"  # 或 "l2beat"
    enabled: true
```

### 📝 API 文档

- L2BEAT：https://l2beat.com/scaling/tvl
- DefiLlama：https://defillama.com/docs/api

---

## 3️⃣ 宏观数据 API - 美股、美债、黄金、原油

### 📌 推荐方案：使用 yfinance 库（免费）

**yfinance** 是一个免费的 Python 库，可以获取 Yahoo Finance 的数据。

### 🔧 安装

```bash
pip install yfinance
```

### ⚙️ 配置方法

在 `config/config.local.yaml` 中添加：

```yaml
data_sources:
  macro:
    provider: "yfinance"
    enabled: true
    symbols:
      nasdaq: "^IXIC"      # 纳斯达克指数
      dxy: "DX-Y.NYB"      # 美元指数
      us10y: "^TNX"        # 10年美债收益率
      vix: "^VIX"          # 恐慌指数
      gold: "GC=F"         # 黄金期货
      oil: "CL=F"          # 原油期货
```

### 📝 代码示例

```python
import yfinance as yf

# 获取纳斯达克指数
nasdaq = yf.Ticker("^IXIC")
data = nasdaq.history(period="1d")
price = data['Close'].iloc[-1]
change = ((data['Close'].iloc[-1] - data['Open'].iloc[0]) / data['Open'].iloc[0]) * 100
```

---

## 4️⃣ CryptoPanic API - 专业加密新闻（可选）

### 📌 获取步骤

1. **访问官网**：https://cryptopanic.com/
2. **注册账号**：点击右上角 "Sign Up"
3. **获取 API Key**：
   - 登录后访问：https://cryptopanic.com/developers/api/
   - 点击 "Get your free API key"
   - 复制生成的 API Key

### 💰 价格

- **免费版**：每天 1,000 次请求（足够使用）
- **付费版**：$9.99/月起，更高请求限制和高级功能

### ⚙️ 配置方法

在 `config/config.local.yaml` 中添加：

```yaml
data_sources:
  news:
    provider: "cryptopanic"  # 切换到 CryptoPanic
    enabled: true
    cryptopanic_api_key: "your_cryptopanic_api_key_here"
```

### 📝 API 文档

- 官方文档：https://cryptopanic.com/developers/api/
- 特点：
  - 专注于加密货币新闻
  - 支持按币种筛选（BTC, ETH 等）
  - 提供新闻热度评分
  - 支持多种语言

### 🆚 CoinGecko News vs CryptoPanic

| 特性 | CoinGecko News | CryptoPanic |
|------|----------------|-------------|
| 价格 | 完全免费 | 免费版 1000次/天 |
| API Key | 不需要 | 需要 |
| 新闻质量 | 一般 | 更专业 |
| 新闻数量 | 较少 | 更多 |
| 热度评分 | 无 | 有 |
| 推荐度 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**建议**：
- 新手：使用 CoinGecko News（免费，无需配置）
- 进阶：使用 CryptoPanic（更专业，需要注册）

---

## 5️⃣ 其他可选数据源

### 🔹 CoinMarketCap API

- **用途**：更详细的币种数据、市场排名
- **获取**：https://coinmarketcap.com/api/
- **价格**：免费版每月 10,000 次请求

### 🔹 Glassnode API

- **用途**：链上数据、矿工数据、交易所流入流出
- **获取**：https://glassnode.com/
- **价格**：$29/月起

### 🔹 Messari API

- **用途**：项目基本面数据、研报
- **获取**：https://messari.io/api
- **价格**：免费版有限制

---

## ✅ 完整配置示例

在 `config/config.local.yaml` 中：

```yaml
# LLM API 配置
openai:
  provider: "grok"
  grok_api_key: "xai-your-key-here"
  model: "grok-4-fast-reasoning"

# 数据源配置
data_sources:
  # Coinglass 爆仓数据
  coinglass:
    api_key: "your_coinglass_api_key"
    enabled: true
  
  # L2 TVL 数据
  l2:
    provider: "defillama"  # 或 "l2beat"
    enabled: true
  
  # 宏观数据
  macro:
    provider: "yfinance"
    enabled: true
```

---

## 🚀 下一步

1. **最小配置**（推荐先这样）：
   - 只配置 Grok API Key
   - 使用免费的 yfinance 获取宏观数据
   - L2 和爆仓数据暂时跳过

2. **完整配置**：
   - 注册 Coinglass 获取爆仓数据
   - 使用 DefiLlama 获取 L2 数据
   - 安装 yfinance 获取宏观数据

---

## 📞 需要帮助？

如果在配置过程中遇到问题，请告诉我具体的错误信息！

