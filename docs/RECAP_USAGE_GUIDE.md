# Web3 每日大盘复盘功能使用说明

## 📋 目录

1. [功能概述](#功能概述)
2. [系统架构](#系统架构)
3. [快速开始](#快速开始)
4. [配置说明](#配置说明)
5. [使用方式](#使用方式)
6. [自定义系统提示词](#自定义系统提示词)
7. [API 接口](#api-接口)
8. [故障排查](#故障排查)

---

## 功能概述

Web3 每日大盘复盘功能可以：

✅ **自动获取真实市场数据**
- BTC/ETH 价格和交易量（Binance API）
- 全球市值和 BTC 占比（CoinGecko API）
- 恐惧贪婪指数（alternative.me API）
- Layer 2 TVL 数据（L2BEAT API）

✅ **智能生成专业复盘**
- 使用自定义系统提示词（`prompt/system_prompt.md`）
- 基于真实数据生成分析内容
- 自动拆分为 Twitter Thread 格式

✅ **自动发布到 Twitter**
- 支持定时自动发布
- 支持手动触发发布
- 自动串联 Thread 推文

---

## 系统架构

```
┌─────────────────┐
│  定时任务/手动  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  1. 获取数据    │ ← Binance, CoinGecko, etc.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. 生成复盘    │ ← prompt/system_prompt.md
│  (LLM + Prompt) │ ← data/market.json
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. 发布 Thread │ → Twitter API
└─────────────────┘
```

---

## 快速开始

### 方式 1: 测试完整流程（不发布）

```bash
# 测试数据获取 + 内容生成（使用 prompt/system_prompt.md）
python tools/test_recap_with_prompt.py
```

**输出内容：**
- ✅ 获取并显示市场数据
- ✅ 使用系统提示词生成复盘 Thread
- ✅ 显示生成的每条推文
- ✅ 保存到 `data/recap_output.json`

### 方式 2: 启动定时任务

1. **配置定时任务**（编辑 `config/config.yaml`）：

```yaml
scheduler:
  daily_recap:
    enabled: true        # 启用每日复盘
    recap_time: "20:00"  # 每天晚上 8 点执行
```

2. **启动系统**：

```bash
python app.py
```

系统会在每天 20:00 自动执行：获取数据 → 生成复盘 → 发布到 Twitter

### 方式 3: 手动触发发布

```bash
# 使用 curl 调用 API
curl -X POST http://localhost:5000/recap/manual
```

或使用 Python：

```python
import requests

response = requests.post('http://localhost:5000/recap/manual')
result = response.json()

if result['success']:
    print(f"发布成功！Thread URL: {result['data']['thread_url']}")
else:
    print(f"发布失败: {result['error']}")
```

---

## 配置说明

### 1. 系统提示词配置

系统提示词文件位置：`prompt/system_prompt.md`

**当前系统提示词特点：**
- 角色定位：专业 Web3 市场分析师 + 推特 KOL
- 风格：观点犀利、数据驱动、拒绝废话
- 输出结构：8 个固定板块（标题、总览、宏观、核心数据、重点币种、链上数据、重磅新闻、明日关注）

**修改系统提示词：**

直接编辑 `prompt/system_prompt.md` 文件，下次生成时会自动使用新的提示词。

### 2. 定时任务配置

编辑 `config/config.yaml`：

```yaml
scheduler:
  # 时区设置（重要！）
  timezone: "Asia/Shanghai"  # 中国时间
  # timezone: "America/New_York"  # 美国东部时间
  
  # 每日复盘配置
  daily_recap:
    enabled: true        # 是否启用
    recap_time: "20:00"  # 执行时间（24小时制）
```

### 3. LLM 模型配置

编辑 `config/config.yaml`：

```yaml
openai:
  api_key: "sk-your-api-key-here"
  model: "gpt-4"  # 或 "gpt-3.5-turbo"
```

**推荐模型：**
- `gpt-4`: 质量最高，适合正式发布
- `gpt-3.5-turbo`: 速度快，成本低，适合测试

---

## 使用方式

### 场景 1: 开发测试

**目标：** 测试数据获取和内容生成，不发布到 Twitter

```bash
# 1. 仅获取数据
python -c "from data_sources.fetch_real_data import fetch_all_market_data; fetch_all_market_data(save_to_file=True)"

# 2. 测试完整流程（获取数据 + 生成内容）
python tools/test_recap_with_prompt.py

# 3. 查看生成的内容
cat data/recap_output.json
```

### 场景 2: 手动发布

**目标：** 手动触发一次完整的复盘发布

```bash
# 方式 1: 使用 API
curl -X POST http://localhost:5000/recap/manual

# 方式 2: 使用 Python 脚本
python -c "
import requests
r = requests.post('http://localhost:5000/recap/manual')
print(r.json())
"
```

### 场景 3: 定时自动发布

**目标：** 每天固定时间自动发布

1. 配置 `config/config.yaml`：
   ```yaml
   scheduler:
     daily_recap:
       enabled: true
       recap_time: "20:00"
   ```

2. 启动系统：
   ```bash
   python app.py
   ```

3. 系统会在每天 20:00 自动执行

### 场景 4: 仅生成内容不发布

**目标：** 生成复盘内容，人工审核后再发布

```bash
# 调用生成接口
curl -X POST http://localhost:5000/recap/generate

# 返回结果包含生成的 Thread，但不会发布
```

---

## 自定义系统提示词

### 当前提示词结构

`prompt/system_prompt.md` 包含：

1. **Role（角色定位）**
   - 专业 Web3 市场分析师
   - 推特 KOL 风格

2. **Goal（目标）**
   - 生成高质量 Twitter Thread

3. **Constraints & Tone（约束和语气）**
   - 格式严格
   - 使用 Emoji
   - Crypto Native 术语

4. **Output Structure（输出结构）**
   - 8 个固定板块
   - 每个板块的具体要求

### 修改提示词的建议

**✅ 推荐修改：**
- 调整语言风格（更正式/更轻松）
- 增减输出板块
- 修改 Emoji 使用规则
- 调整篇幅要求

**❌ 不建议修改：**
- 删除"使用真实数据"的约束
- 删除"不编造数字"的要求

### 示例：简化版提示词

如果你想要更简洁的复盘，可以修改为：

```markdown
## Role
你是一名专业的加密货币市场分析师。

## Goal
根据提供的市场数据，生成简洁的每日复盘 Twitter Thread（3-4 条推文）。

## Output Structure

**Tweet 1: 核心数据**
- BTC/ETH 价格和涨跌
- 总市值和 BTC 占比
- 恐惧贪婪指数

**Tweet 2: 市场分析**
- 简短分析价格走势
- 交易量变化

**Tweet 3: 总结展望**
- 一句话总结
- 明日关注点
```

---

## API 接口

### 1. 手动触发完整复盘

```http
POST /recap/manual
```

**功能：** 获取数据 → 生成复盘 → 发布 Thread

**返回示例：**
```json
{
  "success": true,
  "message": "大盘复盘发布成功",
  "data": {
    "thread_url": "https://twitter.com/user/status/123456789",
    "tweet_count": 5,
    "tweets": [...]
  }
}
```

### 2. 仅获取市场数据

```http
POST /recap/fetch-data
```

**功能：** 获取市场数据并保存到 `data/market.json`

### 3. 仅生成复盘内容

```http
POST /recap/generate
Content-Type: application/json

{
  "custom_prompt": "重点关注 BTC 走势"  // 可选
}
```

**功能：** 生成复盘内容，但不发布

---

## 故障排查

### 问题 1: 数据获取失败

**症状：** `获取市场数据失败`

**解决方案：**
1. 检查代理配置（如果需要）
2. 检查网络连接
3. 查看具体错误日志

```bash
# 测试数据获取
python -c "from data_sources.fetch_real_data import fetch_all_market_data; fetch_all_market_data()"
```

### 问题 2: LLM 生成失败

**症状：** `生成复盘 Thread 失败`

**解决方案：**
1. 检查 OpenAI API Key 是否正确
2. 检查 API 余额
3. 检查网络连接（可能需要代理）

```bash
# 测试 LLM 连接
python -c "from llm.llm_client import llm_client; print(llm_client.validate_api_key())"
```

### 问题 3: Twitter 发布失败

**症状：** `发布 Thread 失败`

**解决方案：**
1. 检查 Twitter OAuth 2.0 Token 是否有效
2. 检查 Token 权限（需要 `tweet.write`）
3. 检查是否超过 Twitter 限流

```bash
# 测试 Twitter 连接
python -c "from twitter.api_client import twitter_client; print(twitter_client.test_connection())"
```

### 问题 4: 系统提示词未生效

**症状：** 生成的内容格式不符合预期

**解决方案：**
1. 确认 `prompt/system_prompt.md` 文件存在
2. 确认文件编码为 UTF-8
3. 重启系统

```bash
# 检查提示词文件
cat prompt/system_prompt.md
```

---

## 📞 获取帮助

如有问题，请查看：
- 日志文件：`logs/twitter_bot.log`
- 测试脚本：`tools/test_recap_with_prompt.py`
- 数据文件：`data/market.json`、`data/recap_output.json`

