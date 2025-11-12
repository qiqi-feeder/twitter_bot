# Token 过期处理指南

本文档说明如何处理 Twitter OAuth 2.0 Token 过期的情况。

## 🔍 如何判断 Token 是否过期？

### 症状

1. **应用日志显示错误**:
   ```
   ERROR - 刷新访问令牌失败
   ERROR - 访问令牌刷新失败
   ```

2. **API 请求失败**:
   ```
   401 Unauthorized
   Invalid or expired token
   ```

3. **快速测试失败**:
   ```bash
   python tools/quick_test.py
   # 显示: ❌ OAuth 2.0 凭据验证失败
   ```

## 🔄 自动刷新机制

系统会自动刷新 Token，**通常您不需要手动干预**。

### 自动刷新条件

- Token 即将过期（提前 5 分钟）
- Token 已过期
- 首次使用时没有过期时间信息

### 自动刷新流程

```
应用启动 → 检查 Token → 即将过期？
                           ↓ 是
                使用 refresh_token 自动刷新
                           ↓
                保存新 Token 到配置文件
                           ↓
                继续正常运行
```

## 🛠️ 手动重新获取 Token

如果自动刷新失败，或者 refresh_token 也过期了，需要手动重新授权。

### 方式 1: 使用授权工具（推荐）

```bash
python tools/oauth2_authorize.py
```

**步骤**:
1. 工具会生成授权 URL
2. 在浏览器中打开 URL
3. 登录 Twitter 账号
4. 授权应用
5. Token 自动保存到配置文件

### 方式 2: 完整设置流程

如果您的 Client ID 或 Client Secret 也需要更新：

```bash
python tools/complete_setup.py
```

这会重新配置所有凭据。

### 方式 3: 手动配置

如果您已经有新的 access_token 和 refresh_token：

1. 编辑 `config/config.yaml`
2. 更新以下字段：
   ```yaml
   twitter:
     access_token: "your_new_access_token"
     refresh_token: "your_new_refresh_token"
     token_expires_at: ""  # 留空，系统会自动计算
   ```
3. 保存文件
4. 运行测试验证：
   ```bash
   python tools/quick_test.py
   ```

## 🔧 故障排除

### 问题 1: refresh_token 也过期了

**症状**:
```
ERROR - 刷新访问令牌失败: invalid_grant
```

**解决方案**:
重新运行授权流程：
```bash
python tools/oauth2_authorize.py
```

### 问题 2: 授权工具无法启动

**症状**:
```
❌ 未配置有效的 Client ID
```

**解决方案**:
1. 检查 `config/config.yaml` 中的 `client_id` 是否正确
2. 运行配置向导：
   ```bash
   python tools/setup_config.py
   ```

### 问题 3: 浏览器授权后没有反应

**症状**:
浏览器显示 "无法访问此网站" 或 "连接被拒绝"

**可能原因**:
- 回调服务器未启动
- 端口 8080 被占用
- 回调 URL 配置不正确

**解决方案**:
1. 确保授权工具正在运行
2. 检查端口 8080 是否被占用：
   ```bash
   # Windows
   netstat -ano | findstr :8080
   
   # Linux/Mac
   lsof -i :8080
   ```
3. 确认 Twitter App 设置中的回调 URL 为：
   ```
   http://localhost:8080/callback
   ```

### 问题 4: 代理连接超时

**症状**:
```
ERROR - Read timed out
ERROR - 代理连接测试失败
```

**解决方案**:
1. 检查代理配置是否正确
2. 测试代理连接：
   ```bash
   # 临时禁用代理测试
   # 编辑 config/config.yaml
   proxy:
     enabled: false
   ```
3. 如果不使用代理可以成功，说明代理配置有问题
4. 检查代理地址、端口、用户名、密码是否正确

### 问题 5: Client Secret 丢失

**症状**:
需要重新配置，但 Client Secret 丢失了

**解决方案**:
1. 访问 [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. 选择您的应用
3. 在 "Keys and tokens" 中重新生成 Client Secret
4. 更新配置文件：
   ```bash
   python tools/setup_config.py
   ```
5. 重新授权：
   ```bash
   python tools/oauth2_authorize.py
   ```

## 📋 Token 生命周期

### Access Token
- **有效期**: 通常 2 小时
- **用途**: 访问 Twitter API
- **刷新**: 使用 refresh_token 自动刷新

### Refresh Token
- **有效期**: 通常 6 个月（如果持续使用会自动延长）
- **用途**: 获取新的 access_token
- **刷新**: 每次刷新 access_token 时可能会获得新的 refresh_token

## 🔒 安全建议

1. **定期备份配置文件**:
   ```bash
   cp config/config.yaml config/config.yaml.backup
   ```

2. **不要分享 Token**:
   - access_token 和 refresh_token 是敏感信息
   - 不要提交到版本控制系统
   - 不要在公开场合分享

3. **定期检查应用权限**:
   - 访问 Twitter 账号设置
   - 检查已授权的应用
   - 撤销不再使用的应用权限

4. **监控异常活动**:
   - 定期查看日志文件
   - 注意异常的 API 调用
   - 如发现异常，立即撤销 Token 并重新授权

## 📚 相关文档

- [快速开始指南](GET_STARTED.md)
- [OAuth 2.0 详细指南](OAUTH2_GUIDE.md)
- [实现说明文档](AUTH_IMPLEMENTATION.md)

## 🆘 需要帮助？

如果以上方法都无法解决问题：

1. 查看日志文件: `logs/twitter_bot.log`
2. 运行诊断测试: `python tools/test_oauth2.py`
3. 提交 Issue: [GitHub Issues](https://github.com/qiqi-feeder/twitter_bot/issues)

