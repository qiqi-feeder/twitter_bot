# 每日定时发推设置指南

本指南说明如何设置和使用每日定时发推功能。

## 🎯 功能概述

- ✅ 每天美国东部时间早上 8:00 自动发推
- ✅ 支持固定内容或 LLM 生成内容
- ✅ 自动处理夏令时转换
- ✅ 与服务器所在时区无关

## 📋 当前配置

### 配置文件：`config/config.yaml`

```yaml
scheduler:
  tweets_per_day: 1
  tweet_times:
    - "08:00"  # 美国东部时间早上8点
  timezone: "America/New_York"  # 美国东部时间
  fixed_content: "Good morning! 🌅 Have a great day! #DailyGreeting"
```

### 实际执行时间

如果您的服务器在中国：
- **配置时间**: 美国东部时间 08:00
- **实际执行**: 中国时间 21:00（晚上9点）
- **系统自动转换**: 无需手动计算

## 🚀 快速开始

### 步骤 1: 安装依赖

```bash
# 方式 1: 使用 pip
pip install -r requirements.txt

# 方式 2: 使用安装脚本（Windows）
install_dependencies.bat
```

### 步骤 2: 配置 Twitter OAuth 2.0

如果还没有配置 Token，运行授权工具：

```bash
# 远程服务器（SSH 连接）
python tools/oauth2_authorize_remote.py

# 本地环境
python tools/oauth2_authorize.py
```

### 步骤 3: 测试调度器

```bash
python tools/test_scheduler.py
```

**预期输出**:

```
============================================================
  Twitter Bot 定时任务调度器测试
============================================================

============================================================
  时区信息测试
============================================================
配置的时区: America/New_York

当前各时区时间:
  美国东部时间          : 2025-11-13 08:31:04 EST
  美国太平洋时间        : 2025-11-13 05:31:04 PST
  中国时间             : 2025-11-13 21:31:04 CST

============================================================
  调度器配置
============================================================
时区设置: America/New_York
每日发推次数: 1
发推时间点: ['08:00']
固定内容: Good morning! 🌅 Have a great day! #DailyGreeting

============================================================
  时间计算测试
============================================================
当前时间 (America/New_York): 2025-11-13 08:31:04 EST

计划的发推时间:
  - 每天 08:00 (America/New_York)
    下次执行: 2025-11-14 08:00:00 EST
    距离现在: 23 小时 28 分钟

============================================================
  调度器导入测试
============================================================
✓ JobScheduler 类导入成功
✓ JobScheduler 实例创建成功
  时区: America/New_York
  运行状态: 未启动
  已配置任务数: 1
    - 每天 08:00 发推 (ID: tweet_08:00)

============================================================
  测试完成
============================================================
✓ 所有测试通过
```

### 步骤 4: 启动应用

```bash
python app.py
```

**预期日志**:

```
INFO - 调度器初始化完成，时区: America/New_York
INFO - 已设置定时发推任务: 每天 08:00 (America/New_York)
INFO - 定时任务调度器已启动
INFO - 下次发推时间: 2025-11-14 08:00:00 EST
INFO - Flask 应用启动成功
```

## ⚙️ 配置选项

### 选项 1: 固定内容（当前配置）

**适用场景**: 每日问候、固定提醒

```yaml
scheduler:
  tweet_times:
    - "08:00"
  timezone: "America/New_York"
  fixed_content: "Good morning! 🌅 Have a great day! #DailyGreeting"
```

**优点**:
- ✅ 内容可控，每次相同
- ✅ 不消耗 OpenAI API 额度
- ✅ 响应速度快

### 选项 2: LLM 生成内容

**适用场景**: 需要多样化、智能化的内容

```yaml
scheduler:
  tweet_times:
    - "08:00"
  timezone: "America/New_York"
  fixed_content: null  # 或删除此行
```

**优点**:
- ✅ 内容多样化，每次不同
- ✅ 更加智能和灵活

**注意**: 需要配置 OpenAI API Key

### 选项 3: 多次发推

```yaml
scheduler:
  tweets_per_day: 2
  tweet_times:
    - "08:00"  # 早上8点
    - "20:00"  # 晚上8点
  timezone: "America/New_York"
  fixed_content: null  # 使用 LLM 生成
```

### 选项 4: 更换时区

```yaml
scheduler:
  tweet_times:
    - "08:00"
  # 美国太平洋时间（洛杉矶、旧金山）
  timezone: "America/Los_Angeles"
  fixed_content: "Good morning from the West Coast! 🌊"
```

**可用时区**:
- `America/New_York` - 美国东部时间
- `America/Los_Angeles` - 美国太平洋时间
- `America/Chicago` - 美国中部时间
- `America/Denver` - 美国山地时间
- `Asia/Shanghai` - 中国时间

## 🔍 验证和监控

### 查看日志

```bash
tail -f logs/twitter_bot.log
```

### 查看调度器状态

```bash
curl http://localhost:5000/scheduler/status
```

### 手动触发发推（测试）

```bash
curl -X POST http://localhost:5000/tweet/post
```

## ⚠️ 常见问题

### 1. 调度器没有执行

**检查**:
- 确认应用正在运行
- 查看日志文件
- 确认时区配置正确

### 2. 时间不对

**原因**: 可能是时区配置错误

**解决**:
```bash
# 运行测试工具查看时区
python tools/test_scheduler.py
```

### 3. LLM 生成失败

**原因**: OpenAI API Key 未配置或无效

**解决**:
- 检查 `config/config.yaml` 中的 `openai.api_key`
- 使用固定内容代替 LLM 生成

### 4. Twitter API 错误

**原因**: Token 过期或无效

**解决**:
```bash
# 重新授权
python tools/oauth2_authorize_remote.py
```

## 📚 相关文档

- [时区设置指南](SCHEDULER_TIMEZONE_GUIDE.md)
- [远程服务器设置](REMOTE_SERVER_SETUP.md)
- [OAuth 2.0 指南](OAUTH2_GUIDE.md)
- [Token 刷新指南](TOKEN_REFRESH_GUIDE.md)

## 🎉 总结

现在您的 Twitter Bot 已经配置好每日定时发推功能：

- ✅ 每天美国东部时间早上 8:00 自动发推
- ✅ 发送固定内容："Good morning! 🌅 Have a great day! #DailyGreeting"
- ✅ 自动处理时区转换和夏令时
- ✅ 可随时切换为 LLM 生成内容

**启动应用后，系统会自动在每天早上 8:00（美国东部时间）发送推文！**

