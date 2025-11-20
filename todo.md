✅ Web3 每日复盘自动化系统（自动发推 + 真实数据填充）设计文档

目的：构建一个 完全基于真实数据 的自动生成 Web3 大盘复盘（Crypto Daily Recap）系统，自动生成推特 Thread 并每日定时发布。

# 📌 1. 系统目标（System Goal）

构建一套自动化流水线，能够：

每天定时执行（如北京时间 20:00）

从多个可信 API 获取真实数据（行情、链上数据、宏观指数、TVL 等）

把数据结构化成一个大 JSON（LLM 不允许修改数字）

读取预先写好的复盘模板（Markdown Prompt）

使用 LLM 生成高质量复盘长文（Thread）

使用 Twitter API 自动发布

可扩展：自动回复、自动生成资讯、自动监控热点

# 📌 2. 系统架构（Architecture Overview）
┌─────────────────┐      ┌──────────────────────────────┐
│   Scheduler     │ ---> │  fetch_real_data.py          │
│ (cron/APScheduler)│    │ （抓取所有真实数据）          │
└─────────────────┘      └──────────────────────────────┘
                                  |
                                  v
                          ┌─────────────────┐
                          │ market.json      │
                          │ （全量真实数据） │
                          └─────────────────┘
                                  |
                                  v
                    ┌─────────────────────────┐
                    │ generate_summary.py      │
                    │ 读取 template.md         │
                    │ 调用 LLM 生成复盘 Thread │
                    └─────────────────────────┘
                                  |
                                  v
                    ┌─────────────────────────┐
                    │  post_to_twitter.py     │
                    │    自动发推 Thread       │
                    └─────────────────────────┘

# 📌 3. 模块设计（Modules）
### 3.1 fetch_real_data.py（真实数据抓取模块）

职责：

调用所有 API

解析并返回 结构化 JSON

所有数字必须真实，没有任何推测或模型生成内容

若某 API 超时 → fallback 到另一个数据源

数据来源（建议）：

类别	推荐 API
BTC/ETH 行情	Binance API / CoinGecko API
全市场市值	CoinGecko Global API
爆仓	Coinglass API
恐惧贪婪指数	alternative.me
L2 TVL	L2BEAT API
ETH Gas, Burn	Ultrasound.money
宏观指数（DXY, 纳指, 美债）	Yahoo Finance
新闻	CryptoPanic API
Token 解锁	TokenUnlocks API

输出：market.json

示例结构：

{
  "timestamp": "2025-11-20T20:00:00+08:00",
  "price": {
    "btc": { "price": 95300, "change": 1.1, "volume": 23000000000 },
    "eth": { "price": 3480, "change": -2.5, "volume": 15000000000 }
  },
  "global": {
    "market_cap": 3180000000000,
    "change": -1.9,
    "btc_dominance": 57.2
  },
  "liquidation": {
    "24h": 520000000,
    "long_short_ratio": "1:1.3"
  },
  "macro": {
    "nasdaq": 22564.23,
    "dxy": 105.3,
    "vix": 16.2,
    "us10y": 4.15,
    "gold": 2620,
    "oil": 74.5
  },
  "l2": {
    "xlayer": { "tvl": 8500000000, "active_users": 2000000 }
  },
  "news": [
    { "title": "...", "impact": "bullish" },
    { "title": "...", "impact": "bearish" }
  ],
  "unlocks": [
    { "token": "APT", "amount": 200000000 }
  ]
}

### 3.2 template.md（复盘模板）

使用你已经上传的复盘模板（严格格式化结构）：

👉 模板路径
system_prompt.md
（用于 LLM system prompt）


ec63ad84-62eb-4cb6-8b4b-a4ccb68…

模型不得修改结构。

### 3.3 generate_summary.py（生成复盘内容）

职责：

加载 template.md

加载 market.json（真实数据）

构造 LLM Prompt

生成一篇完整 Thread

确保模型不生成任何数字，只能复述 JSON 里的真实数据

关键提示：

LLM 调用时必须强制：

注意：所有数字必须**完全使用我提供的数据**。
不得编造、推测或推断任何新数字。
不得更改 market.json 中的任何数值。

### 3.4 post_to_twitter.py（发布模块）

职责：

使用 Twitter API（V2 或 V1.1）

自动拆分长文为 Thread

自动发布

失败时重试

日志记录

### 3.5 Scheduler（定时任务系统）

可选：

Linux cron

APScheduler

Node-schedule（如后端为 Node）

PM2 cron

Cloudflare Workers（无服务器方案）

推荐 APScheduler：

每天北京时间 20:00 自动运行：
- fetch_real_data()
- generate_summary()
- post_to_twitter()

# 📌 4. LLM 调用示例（Pseudo Code）
system_prompt = open("template.md", encoding="utf-8").read()
market_data = json.load(open("market.json", encoding="utf-8"))

user_prompt = f"""
以下是今天的全部真实市场数据：
{json.dumps(market_data, indent=2)}

请根据 template.md 的结构生成每日复盘 Thread。
注意：你不能修改任何数字，不能推测数字，只能使用我提供的 market.json 数据。
"""

response = client.chat.completions.create(
    model="gpt-4.1",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
)

# 📌 5. 系统的关键设计原则

所有数字均来自 API，不得让 LLM 生成

模板固定 → 保持风格统一

模型只做语言加工，不参与数值计算

所有数据写入 market.json，方便调试

错误数据自动 fallback

日志清晰用于排查异常

# 📌 6. 推荐 API 列表（可直接使用）
Crypto 数据

Binance: https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT

CoinGecko: /global, /coins/markets, /coins/{id}

Coinglass: 爆仓数据

CryptoPanic: 新闻

链上数据

L2BEAT: https://api.l2beat.com/api/tvl

Ultrasound.money: https://ultrasound.money/api/

宏观数据

Yahoo Finance (yfinance Python 库)

# 📌 7. 项目结构建议（最终目录）
/crypto-daily-system
│
├── data/
│   ├── market.json
│   └── logs/
│
├── templates/
│   └── template.md   ← 你上传的复盘模板
│
├── src/
│   ├── fetch_real_data.py
│   ├── generate_summary.py
│   ├── post_to_twitter.py
│   └── utils.py
│
├── scheduler/
│   └── daily_job.py
│
├── README.md
└── requirements.txt

# 📌 8. 系统工作流总结（Workflow Summary）
1）每天定时 → Scheduler
2）抓真实数据 → fetch_real_data.py
3）数据写入 market.json
4）加载 template.md + market.json → generate_summary.py
5）LLM 生成高质量 Thread（仅加工文本，不产生数字）
6）post_to_twitter.py 自动发推