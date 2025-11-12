# Twitter OAuth 2.0 授权快速开始指南

本指南将帮助您从零开始配置 Twitter OAuth 2.0 认证。

## 📋 前置准备

### 步骤 1: 创建 Twitter Developer 账号

1. 访问 [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. 使用您的 Twitter 账号登录
3. 如果是第一次使用，需要申请开发者账号：
   - 填写申请表单
   - 说明使用目的（例如：个人自动发推工具）
   - 等待审核（通常几分钟到几小时）

### 步骤 2: 创建 Twitter App

1. 登录 [Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. 点击 **"+ Create Project"** 或 **"+ Create App"**
3. 填写应用信息：
   - **App name**: 例如 "My Twitter Bot"
   - **Description**: 应用描述
   - **Website URL**: 可以填写 `http://localhost:5000`
   - **Callback URLs**: **重要！** 必须添加 `http://localhost:8080/callback`

### 步骤 3: 配置 OAuth 2.0

1. 在应用设置中找到 **"User authentication settings"**
2. 点击 **"Set up"** 或 **"Edit"**
3. 配置以下选项：

   **App permissions**:
   - ✅ Read
   - ✅ Write
   - ⬜ Direct Messages (可选)

   **Type of App**:
   - ✅ Web App, Automated App or Bot

   **App info**:
   - **Callback URI**: `http://localhost:8080/callback` （必须精确匹配）
   - **Website URL**: `http://localhost:5000`

4. 点击 **"Save"**

### 步骤 4: 获取 Client ID 和 Client Secret

1. 保存设置后，会显示：
   - **Client ID**: 类似 `aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890`
   - **Client Secret**: 类似 `aBcDeFgHiJkLmNoPqRsTuVwXyZ1234567890aBcDeFgHiJkL`

2. **重要**: 立即复制并保存这些信息，Client Secret 只显示一次！

## 🔧 配置项目

### 步骤 1: 填写配置文件

编辑 `config/config.yaml`，填入您的凭据：

```yaml
twitter:
  # OAuth 2.0 Client ID（必填）
  client_id: "your_client_id_here"
  
  # OAuth 2.0 Client Secret（必填）
  client_secret: "your_client_secret_here"
  
  # 以下字段暂时留空，授权后会自动填充
  access_token: ""
  refresh_token: ""
  token_expires_at: ""
```

### 步骤 2: 配置代理（如果需要）

如果您需要通过代理访问 Twitter API：

```yaml
proxy:
  socks5_url: "socks5://username:password@proxy_host:port"
  enabled: true
```

如果不需要代理：

```yaml
proxy:
  enabled: false
```

## 🚀 运行授权流程

### 方式 1: 使用授权工具（推荐）

运行授权工具：

```bash
python tools/oauth2_authorize.py
```

工具会：
1. ✅ 读取您的 Client ID 和 Client Secret
2. ✅ 生成授权 URL
3. ✅ 启动本地回调服务器（端口 8080）
4. ✅ 等待您在浏览器中完成授权
5. ✅ 自动交换 access_token 和 refresh_token
6. ✅ 自动保存到 `config/config.yaml`

### 方式 2: 手动授权（高级用户）

如果自动工具无法使用，可以手动完成授权流程。详见 [OAuth 2.0 使用指南](OAUTH2_GUIDE.md)。

## ✅ 验证配置

运行快速测试：

```bash
python tools/quick_test.py
```

如果看到以下输出，说明配置成功：

```
✅ 所有基本配置测试通过！

📝 配置摘要:
   - Access Token: 已配置 (91 字符)
   - Refresh Token: 已配置
   - 代理: 已启用/未启用
```

## 🎯 开始使用

配置完成后，启动应用：

```bash
python app.py
```

或使用启动脚本：

```bash
python start.py
```

## ❓ 常见问题

### Q1: 授权时显示 "Invalid callback URL"

**原因**: 回调 URL 配置不正确

**解决方案**:
1. 检查 Twitter App 设置中的 Callback URL 是否为 `http://localhost:8080/callback`
2. 确保 URL 完全匹配，包括协议（http）、端口（8080）和路径（/callback）

### Q2: 无法访问 Twitter Developer Portal

**原因**: 可能需要代理

**解决方案**:
1. 使用代理访问 Twitter Developer Portal
2. 或使用 VPN

### Q3: Client Secret 丢失了怎么办？

**解决方案**:
1. 在 Twitter Developer Portal 中重新生成 Client Secret
2. 更新 `config/config.yaml` 中的配置
3. 重新运行授权流程

### Q4: Token 过期了怎么办？

**不用担心！** 系统会自动刷新 Token：
- 系统会在 Token 过期前 5 分钟自动刷新
- 使用 `refresh_token` 获取新的 `access_token`
- 新 Token 会自动保存到配置文件

如果自动刷新失败，重新运行授权工具：

```bash
python tools/oauth2_authorize.py
```

## 📚 更多文档

- [OAuth 2.0 详细指南](OAUTH2_GUIDE.md)
- [实现说明文档](AUTH_IMPLEMENTATION.md)
- [Twitter OAuth 2.0 官方文档](https://developer.twitter.com/en/docs/authentication/oauth-2-0)

## 🆘 需要帮助？

如果遇到问题：
1. 查看日志文件: `logs/twitter_bot.log`
2. 运行测试脚本: `python tools/quick_test.py`
3. 提交 Issue: [GitHub Issues](https://github.com/qiqi-feeder/twitter_bot/issues)

