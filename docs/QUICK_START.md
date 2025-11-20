# 🚀 快速开始 - Web3 每日大盘复盘

## 📝 5 分钟快速上手

### 步骤 1: 测试数据获取

```bash
python tools/test_recap_with_prompt.py
```

**这个命令会：**
1. ✅ 从 Binance、CoinGecko 等 API 获取真实市场数据
2. ✅ 使用 `prompt/system_prompt.md` 作为系统提示词
3. ✅ 调用 LLM 生成复盘 Thread
4. ✅ 显示生成的每条推文
5. ✅ 保存结果到 `data/recap_output.json`

**预期输出：**
```
🚀 开始测试大盘复盘功能（使用 prompt 文件夹）

============================================================
步骤 1/3: 获取市场数据
============================================================
✅ 市场数据获取成功
  BTC: $91737.05 (+0.13%)
  ETH: $3001.25 (-3.25%)
  总市值: $3,214,876,752,513
  BTC 占比: 57.02%
  恐惧贪婪指数: 11 (Extreme Fear)

============================================================
步骤 2/3: 使用 LLM 生成复盘内容
============================================================
✅ LLM 生成成功

============================================================
步骤 3/3: 生成的复盘 Thread
============================================================

共生成 5 条推文:

============================================================
Tweet 1/5 (长度: 245 字符)
============================================================
📊 11月20日 Web3大盘复盘 | BTC 微涨守住 $91K，山寨币继续承压 🩸

市场情绪：极度恐惧（11）
核心叙事：流动性枯竭，PVP 模式延续

#Crypto #Bitcoin #Web3
...
```

---

### 步骤 2: 自定义系统提示词

编辑 `prompt/system_prompt.md` 文件，修改：

- **角色定位**：改变分析师的风格
- **输出结构**：增减复盘板块
- **语言风格**：调整专业程度

**示例修改：**

```markdown
## Role
你是一名专业的加密货币市场分析师，风格简洁明了。

## Goal
生成 3-4 条推文的每日复盘 Thread。

## Output Structure

**Tweet 1: 核心数据**
- BTC/ETH 价格和涨跌
- 总市值和情绪指数

**Tweet 2: 市场分析**
- 价格走势分析
- 交易量变化

**Tweet 3: 总结**
- 一句话总结
- 明日关注
```

保存后，再次运行测试脚本即可看到效果。

---

### 步骤 3: 启用定时自动发布

1. **编辑配置文件** `config/config.yaml`：

```yaml
scheduler:
  # 时区设置
  timezone: "Asia/Shanghai"  # 或 "America/New_York"
  
  # 每日复盘配置
  daily_recap:
    enabled: true        # 启用自动复盘
    recap_time: "20:00"  # 每天晚上 8 点
```

2. **启动系统**：

```bash
python app.py
```

3. **查看日志**：

```bash
tail -f logs/twitter_bot.log
```

系统会在每天 20:00 自动执行：
- 获取市场数据
- 生成复盘 Thread
- 发布到 Twitter

---

## 🎯 常用命令

### 测试相关

```bash
# 测试完整流程（不发布）
python tools/test_recap_with_prompt.py

# 仅测试数据获取
python -c "from data_sources.fetch_real_data import fetch_all_market_data; fetch_all_market_data(save_to_file=True)"

# 查看生成的内容
cat data/recap_output.json
```

### 手动发布

```bash
# 启动系统（如果未启动）
python app.py

# 在另一个终端，手动触发发布
curl -X POST http://localhost:5000/recap/manual
```

### 查看日志

```bash
# 实时查看日志
tail -f logs/twitter_bot.log

# 查看最近 50 行
tail -n 50 logs/twitter_bot.log

# 搜索错误
grep ERROR logs/twitter_bot.log
```

---

## 📂 重要文件说明

| 文件路径 | 说明 | 是否可修改 |
|---------|------|-----------|
| `prompt/system_prompt.md` | 系统提示词（定义复盘风格和结构） | ✅ 可修改 |
| `config/config.yaml` | 系统配置（API Key、定时任务等） | ✅ 可修改 |
| `data/market.json` | 最新市场数据缓存 | ❌ 自动生成 |
| `data/recap_output.json` | 最新生成的复盘内容 | ❌ 自动生成 |
| `tools/test_recap_with_prompt.py` | 测试脚本 | ⚠️ 可修改（高级） |

---

## 🔧 工作流程图

```
┌──────────────────────────────────────────────────────────┐
│                     定时任务 / 手动触发                    │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   1. 获取市场数据              │
         │   - Binance API (BTC/ETH)     │
         │   - CoinGecko API (市值)      │
         │   - alternative.me (情绪)     │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   2. 构建提示词                │
         │   - 系统提示词: system_prompt.md │
         │   - 用户提示词: 市场数据       │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   3. 调用 LLM 生成内容         │
         │   - OpenAI API                │
         │   - 模型: gpt-4 / gpt-3.5     │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   4. 拆分为 Twitter Thread    │
         │   - 每条推文 ≤ 280 字符        │
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   5. 发布到 Twitter           │
         │   - 使用 in_reply_to 串联     │
         │   - 延迟发送避免限流           │
         └───────────────────────────────┘
```

---

## ❓ 常见问题

### Q1: 如何修改复盘的风格？

**A:** 编辑 `prompt/system_prompt.md` 文件，修改 `Role` 和 `Constraints & Tone` 部分。

### Q2: 如何修改复盘的内容结构？

**A:** 编辑 `prompt/system_prompt.md` 文件，修改 `Output Structure` 部分。

### Q3: 如何更换 LLM 模型？

**A:** 编辑 `config/config.yaml`，修改 `openai.model` 字段：
```yaml
openai:
  model: "gpt-4"  # 或 "gpt-3.5-turbo"
```

### Q4: 如何修改定时发布时间？

**A:** 编辑 `config/config.yaml`，修改 `scheduler.daily_recap.recap_time` 字段：
```yaml
scheduler:
  daily_recap:
    recap_time: "20:00"  # 改为你想要的时间
```

### Q5: 测试时不想发布到 Twitter 怎么办？

**A:** 使用测试脚本：
```bash
python tools/test_recap_with_prompt.py
```
这个脚本只会生成内容，不会发布。

---

## 📚 更多文档

- [完整使用指南](RECAP_USAGE_GUIDE.md) - 详细的功能说明和配置
- [API 接口文档](../README.md#api-接口) - 所有 API 接口说明
- [故障排查](RECAP_USAGE_GUIDE.md#故障排查) - 常见问题解决方案

---

## 🎉 开始使用

现在就运行测试脚本试试吧：

```bash
python tools/test_recap_with_prompt.py
```

祝你使用愉快！🚀

