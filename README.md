# Twitter 自动发推系统

基于 Flask 框架的 Twitter 自动发推系统，使用 Twitter API v2 和 OpenAI API 实现智能推文生成和定时发布功能。

## 功能特性

- 🤖 **智能推文生成**: 使用 OpenAI GPT 模型生成有趣且有价值的推文内容
- ⏰ **定时自动发推**: 支持每天多次定时发推，时间可配置
- 📊 **Web3 每日大盘复盘**: 自动获取真实市场数据，生成专业复盘 Thread
- 🌐 **代理支持**: 所有 API 请求支持 SOCKS5 代理
- 🔧 **手动触发**: 提供 Web API 接口支持手动发推和复盘
- 📈 **实时数据**: 从 Binance、CoinGecko、L2BEAT 等获取真实市场数据
- 🧵 **Thread 支持**: 自动拆分和发布 Twitter Thread
- 📊 **状态监控**: 实时监控系统各组件状态
- 📝 **日志记录**: 详细的日志记录，支持文件和控制台输出
- ⚙️ **配置化管理**: 所有配置项统一管理，易于维护

## 项目结构

```
twitter_auto_poster/
│
├── app.py                      # Flask主入口（启动调度和Web服务）
│
├── config/
│   ├── config.yaml              # 全局配置文件
│   └── __init__.py
│
├── auth/
│   ├── token_manager.py         # 管理access_token刷新
│   └── __init__.py
│
├── twitter/
│   ├── api_client.py            # 封装发推逻辑（走代理）
│   └── __init__.py
│
├── llm/
│   ├── llm_client.py            # 调用LLM生成推文
│   └── __init__.py
│
├── scheduler/
│   ├── job_scheduler.py         # 定时任务调度模块
│   └── __init__.py
│
├── data_sources/                # 数据源模块（新增）
│   ├── fetch_real_data.py       # 获取真实市场数据
│   └── __init__.py
│
├── recap/                       # 大盘复盘模块（新增）
│   ├── generate_summary.py      # 生成复盘内容
│   ├── post_thread.py           # 发布 Thread
│   └── __init__.py
│
├── templates/                   # 模板文件（新增）
│   └── recap_template.md        # 复盘模板
│
├── data/                        # 数据文件（新增）
│   └── market.json              # 市场数据缓存
│
├── utils/
│   ├── proxy.py                 # socks5代理管理
│   ├── config_loader.py         # 读取配置
│   ├── logger.py                # 日志输出
│   └── __init__.py
│
├── requirements.txt
└── README.md
```

## 环境要求

- Python >= 3.9
- Twitter Developer Account (API v2 访问权限)
- OpenAI API Key

## 🚀 快速开始

### 本地环境

#### 方式 1: 一键设置（推荐新用户）

```bash
# 1. 克隆项目
git clone https://github.com/qiqi-feeder/twitter_bot.git
cd twitter_bot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行完整设置向导
python tools/complete_setup.py
```

设置向导会自动引导您完成：
- ✅ 配置 Twitter OAuth 2.0 凭据 (Client ID & Secret)
- ✅ 浏览器授权获取 Access Token
- ✅ 验证配置是否正确

### 远程服务器（SSH 连接）

如果您通过 SSH 连接到远程 Linux 服务器：

```bash
# 1. 在服务器上克隆项目
git clone https://github.com/qiqi-feeder/twitter_bot.git
cd twitter_bot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 Client ID 和 Secret
vim config/config.yaml

# 4. 运行远程授权工具
python tools/oauth2_authorize_remote.py
```

**授权流程**:
1. 工具生成授权 URL
2. 复制 URL 到本地浏览器
3. 在浏览器完成授权
4. 从浏览器地址栏复制授权码
5. 粘贴到服务器终端

详细步骤请参考：[远程服务器设置指南](docs/REMOTE_SERVER_SETUP.md)

### 方式 2: 分步设置

#### 步骤 1: 克隆项目

```bash
git clone https://github.com/qiqi-feeder/twitter_bot.git
cd twitter_bot
```

#### 步骤 2: 安装依赖

```bash
pip install -r requirements.txt
```

#### 步骤 3: 配置 OAuth 2.0 凭据

运行配置向导：

```bash
python tools/setup_config.py
```

或手动编辑 `config/config.yaml`，填入您的 Twitter App 凭据。

#### 步骤 4: 获取 Access Token

运行授权工具：

```bash
python tools/oauth2_authorize.py
```

在浏览器中完成授权后，Token 会自动保存。

#### 步骤 5: 验证配置

```bash
python tools/quick_test.py
```

## 详细配置说明

#### Twitter API 配置

**推荐方式：OAuth 2.0（自动刷新 Token）**

1. 访问 [Twitter Developer Portal](https://developer.twitter.com/)
2. 创建应用并启用 OAuth 2.0
3. 获取 Client ID 和 Client Secret
4. 配置回调 URL: `http://localhost:8080/callback`
5. 使用授权工具获取 Token：
   ```bash
   python tools/oauth2_authorize.py
   ```

详细步骤请参考：[OAuth 2.0 认证指南](docs/OAUTH2_GUIDE.md)

**传统方式：OAuth 1.0a**

如果您已有 OAuth 1.0a 凭据，也可以继续使用：
- Bearer Token
- Consumer Key (API Key)
- Consumer Secret (API Secret)
- Access Token
- Access Token Secret

#### OpenAI API 配置
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 获取 API Key

#### 代理配置（可选）
如果需要使用代理，配置 SOCKS5 代理地址：
```yaml
proxy:
  socks5_url: "socks5://username:password@127.0.0.1:1080"
  enabled: true
```

## 运行系统

### 启动应用

```bash
python app.py
```

系统启动后会：
1. 验证所有 API 凭据
2. 测试网络连接
3. 启动定时任务调度器
4. 启动 Flask Web 服务

### 访问 Web 界面

打开浏览器访问：`http://localhost:5000`

## API 接口

### 1. 系统状态检查
```
GET /status
```

### 2. 手动发推
```
POST /tweet/post
Content-Type: application/json

{
    "content": "自定义推文内容（可选）"
}
```

### 3. 生成推文内容
```
POST /tweet/generate
Content-Type: application/json

{
    "prompt": "自定义提示词（可选）",
    "count": 1
}
```

### 4. 手动触发大盘复盘（新增）
```
POST /recap/manual
Content-Type: application/json
```

完整流程：获取市场数据 → 生成复盘 Thread → 发布到 Twitter

### 5. 获取市场数据（新增）
```
POST /recap/fetch-data
Content-Type: application/json
```

仅获取市场数据并保存到 `data/market.json`

### 6. 生成复盘内容（新增）
```
POST /recap/generate
Content-Type: application/json

{
    "custom_prompt": "自定义提示词（可选）"
}
```

仅生成复盘内容，不发布

### 7. 获取用户信息
```
GET /user/info
```

### 8. 获取最近推文
```
GET /tweets/recent?count=5
```

## 配置说明

### 定时任务配置（支持时区设置）

```yaml
scheduler:
  tweets_per_day: 1
  tweet_times:
    - "08:00"  # 早上8点（基于设置的时区）

  # 时区设置 - 支持美国时间
  # America/New_York - 美国东部时间 (EST/EDT)
  # America/Los_Angeles - 美国太平洋时间 (PST/PDT)
  # America/Chicago - 美国中部时间 (CST/CDT)
  # America/Denver - 美国山地时间 (MST/MDT)
  # Asia/Shanghai - 中国时间
  timezone: "America/New_York"

  # 固定推文内容（可选）
  # 如果设置，则每次发送固定内容
  # 如果为 null 或删除此行，则使用 LLM 生成
  fixed_content: "Good morning! 🌅 Have a great day! #DailyGreeting"

  # 每日大盘复盘配置（新增）
  daily_recap:
    enabled: true           # 是否启用每日大盘复盘
    recap_time: "20:00"     # 复盘时间（24小时制）
```

**重要说明**:
- ✅ 系统会按照配置的时区执行任务，与服务器所在时区无关
- ✅ 自动处理夏令时转换
- ✅ 支持固定内容或 LLM 生成内容
- 📖 详细说明：[时区设置指南](docs/SCHEDULER_TIMEZONE_GUIDE.md)

**测试时区设置**:
```bash
python tools/test_scheduler.py
```

### 推文生成配置

```yaml
openai:
  model: "gpt-3.5-turbo"
  prompt_template: |
    请生成一条有趣且有价值的推文，内容应该：
    1. 长度在100-280字符之间
    2. 包含实用信息或有趣观点
    3. 适合在Twitter上分享
    4. 语言风格轻松友好
```

### 日志配置

```yaml
logging:
  level: "INFO"
  file_path: "logs/twitter_bot.log"
  console_output: true
```

## 使用示例

### 手动发推

```bash
curl -X POST http://localhost:5000/tweet/post \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, Twitter! 🚀"}'
```

### 生成推文内容

```bash
curl -X POST http://localhost:5000/tweet/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 3}'
```

## 故障排除

### 1. Twitter API 错误
- 检查 API 凭据是否正确
- 确认应用权限包含"Read and Write"
- 验证 Access Token 是否有效

### 2. OpenAI API 错误
- 检查 API Key 是否有效
- 确认账户有足够的配额
- 检查网络连接

### 3. 代理连接问题
- 验证代理地址和端口
- 检查代理认证信息
- 测试代理是否正常工作

### 4. 定时任务不执行
- 检查系统时间和时区设置
- 查看日志文件中的错误信息
- 确认调度器是否正常启动

## 开发说明

### 添加新功能

1. 在相应模块中添加功能代码
2. 更新配置文件（如需要）
3. 添加相应的 API 接口
4. 更新文档

### 测试

```bash
# 测试系统状态
curl http://localhost:5000/status

# 测试推文生成
curl -X POST http://localhost:5000/tweet/generate
```

## 注意事项

1. **API 限制**: 注意 Twitter API 和 OpenAI API 的速率限制
2. **内容审核**: 生成的推文内容可能需要人工审核
3. **安全性**: 妥善保管 API 密钥，不要提交到版本控制
4. **合规性**: 确保推文内容符合 Twitter 社区准则

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请通过 Issue 联系。
