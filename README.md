# Twitter 自动发推系统

基于 Flask 框架的 Twitter 自动发推系统，使用 Twitter API v2 和 OpenAI API 实现智能推文生成和定时发布功能。

## 功能特性

- 🤖 **智能推文生成**: 使用 OpenAI GPT 模型生成有趣且有价值的推文内容
- ⏰ **定时自动发推**: 支持每天多次定时发推，时间可配置
- 🌐 **代理支持**: 所有 API 请求支持 SOCKS5 代理
- 🔧 **手动触发**: 提供 Web API 接口支持手动发推
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

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd twitter_auto_poster
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置系统

复制配置文件并填入你的 API 凭据：

```bash
cp config/config.yaml config/config.yaml.local
```

编辑 `config/config.yaml`，填入以下信息：

#### Twitter API 配置
1. 访问 [Twitter Developer Portal](https://developer.twitter.com/)
2. 创建应用并获取以下凭据：
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

### 4. 获取用户信息
```
GET /user/info
```

### 5. 获取最近推文
```
GET /tweets/recent?count=5
```

## 配置说明

### 定时任务配置

```yaml
scheduler:
  tweets_per_day: 2
  tweet_times:
    - "09:00"  # 上午9点
    - "18:00"  # 下午6点
  timezone: "Asia/Shanghai"
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
