# 定时任务时区设置指南

本指南说明如何配置 Twitter Bot 的定时任务时区，使其按照美国时间或其他时区执行。

## 🌍 时区配置

### 配置文件位置

`config/config.yaml` 中的 `scheduler` 部分：

```yaml
scheduler:
  tweets_per_day: 1
  tweet_times:
    - "08:00"  # 早上8点
  timezone: "America/New_York"  # 美国东部时间
  fixed_content: "Good morning! 🌅 Have a great day!"
```

## 🇺🇸 美国时区选项

### 主要时区

| 时区代码 | 时区名称 | 说明 | 与UTC时差 |
|---------|---------|------|----------|
| `America/New_York` | 东部时间 (EST/EDT) | 纽约、华盛顿、迈阿密 | UTC-5/-4 |
| `America/Los_Angeles` | 太平洋时间 (PST/PDT) | 洛杉矶、旧金山、西雅图 | UTC-8/-7 |
| `America/Chicago` | 中部时间 (CST/CDT) | 芝加哥、休斯顿、达拉斯 | UTC-6/-5 |
| `America/Denver` | 山地时间 (MST/MDT) | 丹佛、凤凰城、盐湖城 | UTC-7/-6 |

### 夏令时说明

- **EST/EDT**: 东部标准时间/东部夏令时
- **PST/PDT**: 太平洋标准时间/太平洋夏令时
- **CST/CDT**: 中部标准时间/中部夏令时
- **MST/MDT**: 山地时间/山地夏令时

系统会自动处理夏令时转换，无需手动调整。

## 🌏 其他常用时区

| 时区代码 | 时区名称 | 说明 |
|---------|---------|------|
| `Asia/Shanghai` | 中国标准时间 | UTC+8 |
| `Europe/London` | 英国时间 | UTC+0/+1 |
| `Asia/Tokyo` | 日本标准时间 | UTC+9 |
| `Australia/Sydney` | 澳大利亚东部时间 | UTC+10/+11 |
| `UTC` | 协调世界时 | UTC+0 |

## ⚙️ 配置示例

### 示例 1: 美国东部时间早上8点发推

```yaml
scheduler:
  tweets_per_day: 1
  tweet_times:
    - "08:00"
  timezone: "America/New_York"
  fixed_content: "Good morning from the East Coast! 🌅"
```

### 示例 2: 美国太平洋时间早上8点发推

```yaml
scheduler:
  tweets_per_day: 1
  tweet_times:
    - "08:00"
  timezone: "America/Los_Angeles"
  fixed_content: "Good morning from the West Coast! 🌊"
```

### 示例 3: 每天多次发推（不同时区）

```yaml
scheduler:
  tweets_per_day: 2
  tweet_times:
    - "08:00"  # 早上8点
    - "20:00"  # 晚上8点
  timezone: "America/Chicago"
  fixed_content: null  # 使用 LLM 生成内容
```

### 示例 4: 使用 LLM 生成内容

```yaml
scheduler:
  tweets_per_day: 1
  tweet_times:
    - "08:00"
  timezone: "America/New_York"
  fixed_content: null  # 或者完全删除这一行
```

## 🔧 固定内容 vs LLM 生成

### 固定内容

**优点**:
- ✅ 内容可控，每次发送相同内容
- ✅ 不消耗 OpenAI API 额度
- ✅ 响应速度快

**缺点**:
- ❌ 内容重复，可能显得单调
- ❌ 需要手动更新内容

**配置**:
```yaml
fixed_content: "Good morning! 🌅 Have a great day! #DailyGreeting"
```

### LLM 生成内容

**优点**:
- ✅ 内容多样化，每次不同
- ✅ 可以根据提示词生成相关内容
- ✅ 更加智能和灵活

**缺点**:
- ❌ 消耗 OpenAI API 额度
- ❌ 需要网络请求，可能较慢
- ❌ 内容质量取决于 LLM 模型

**配置**:
```yaml
fixed_content: null  # 或删除此行
```

## 🧪 测试时区设置

### 运行测试脚本

```bash
python tools/test_scheduler.py
```

**输出示例**:
```
============================================================
  时区信息测试
============================================================
配置的时区: America/New_York

当前各时区时间:
  美国东部时间          (America/New_York        ): 2024-02-20 08:30:15 EST
  美国太平洋时间        (America/Los_Angeles     ): 2024-02-20 05:30:15 PST
  美国中部时间          (America/Chicago         ): 2024-02-20 07:30:15 CST
  中国时间              (Asia/Shanghai           ): 2024-02-20 21:30:15 CST
  协调世界时            (UTC                     ): 2024-02-20 13:30:15 UTC

============================================================
  调度器状态
============================================================
运行状态: 运行中
任务数量: 1
当前时间: 2024-02-20 08:30:15 EST
时区设置: America/New_York
下次运行: 2024-02-21 08:00:00 EST

发推时间点:
  - 08:00

固定内容: Good morning! 🌅 Have a great day! #DailyGreeting
```

### 手动验证

```bash
# 查看调度器状态
curl http://localhost:5000/scheduler/status

# 手动触发发推（测试）
curl -X POST http://localhost:5000/tweet/post
```

## 📊 时区转换参考

### 美国东部时间 (EST/EDT) 早上8点对应其他时区

| 时区 | 时间 |
|------|------|
| 美国东部 (New York) | 08:00 |
| 美国中部 (Chicago) | 07:00 |
| 美国山地 (Denver) | 06:00 |
| 美国太平洋 (Los Angeles) | 05:00 |
| 中国 (Shanghai) | 21:00 (当天晚上) |
| 英国 (London) | 13:00 (下午1点) |
| UTC | 13:00 |

## ⚠️ 重要注意事项

### 1. 服务器时区 vs 配置时区

- **服务器时区**: 您的 Linux 服务器可能运行在任何时区
- **配置时区**: 在 `config.yaml` 中设置的时区
- **实际执行**: 系统会按照**配置时区**执行任务，与服务器时区无关

**示例**:
```
服务器时区: Asia/Shanghai (中国时间)
配置时区: America/New_York (美国东部时间)
发推时间: 08:00

实际执行: 美国东部时间早上8点
         = 中国时间晚上9点 (21:00)
```

### 2. 夏令时自动处理

系统使用 `pytz` 库，会自动处理夏令时转换：

- **夏令时开始**: 时钟向前拨1小时
- **夏令时结束**: 时钟向后拨1小时
- **无需手动调整**: 系统自动处理

### 3. 时区代码必须准确

使用标准的 IANA 时区数据库代码：

✅ **正确**:
- `America/New_York`
- `America/Los_Angeles`

❌ **错误**:
- `EST` (不推荐，不处理夏令时)
- `US/Eastern` (已弃用)
- `New York` (无效)

## 🔄 动态更新时区

### 通过 API 更新

```bash
# 更新时区和发推时间
curl -X POST http://localhost:5000/scheduler/update \
  -H "Content-Type: application/json" \
  -d '{
    "tweet_times": ["08:00", "20:00"],
    "timezone": "America/Los_Angeles",
    "fixed_content": "Hello from LA! 🌴"
  }'
```

### 通过配置文件更新

1. 编辑 `config/config.yaml`
2. 重启应用: `python app.py`

## 📚 相关资源

- [IANA 时区数据库](https://www.iana.org/time-zones)
- [pytz 文档](https://pythonhosted.org/pytz/)
- [美国时区地图](https://www.timeanddate.com/time/us/time-zones-background.html)
- [世界时区转换器](https://www.timeanddate.com/worldclock/converter.html)

## 💡 最佳实践

1. **选择合适的时区**: 根据目标受众选择时区
2. **考虑夏令时**: 使用标准时区代码，让系统自动处理
3. **测试验证**: 使用 `test_scheduler.py` 验证配置
4. **监控日志**: 查看 `logs/twitter_bot.log` 确认执行时间
5. **固定内容**: 对于每日问候等场景，使用固定内容更可靠

