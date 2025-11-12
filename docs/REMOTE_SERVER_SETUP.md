# 远程服务器设置指南

本指南专门针对通过 SSH 连接到 Linux 服务器的场景。

## 🌐 场景说明

当您的 Twitter Bot 部署在远程 Linux 服务器上时：
- ✅ 您通过 SSH 连接到服务器
- ✅ 服务器没有图形界面
- ✅ 无法在服务器上直接打开浏览器
- ✅ 需要在本地浏览器完成 OAuth 授权

## 🚀 快速开始

### 方法 1: 使用远程授权工具（推荐）

```bash
# 在远程服务器上运行
python tools/oauth2_authorize_remote.py
```

**流程**:
1. 工具会生成授权 URL
2. 复制 URL 到您的本地浏览器
3. 在浏览器中完成授权
4. 从浏览器地址栏复制授权码
5. 粘贴授权码到服务器终端
6. Token 自动保存

### 方法 2: 本地获取 Token 后上传

如果您有本地开发环境：

```bash
# 1. 在本地电脑运行
python tools/oauth2_authorize.py

# 2. 获取 Token 后，从 config/config.yaml 复制以下内容：
#    - access_token
#    - refresh_token
#    - token_expires_at

# 3. 上传到服务器的 config/config.yaml
```

## 📋 详细步骤（方法 1）

### 步骤 1: 配置 Client ID 和 Client Secret

在服务器上编辑配置文件：

```bash
vim config/config.yaml
# 或
nano config/config.yaml
```

填入您的凭据：

```yaml
twitter:
  client_id: "your_client_id_here"
  client_secret: "your_client_secret_here"
```

### 步骤 2: 运行远程授权工具

```bash
python tools/oauth2_authorize_remote.py
```

### 步骤 3: 在本地浏览器授权

工具会显示类似这样的 URL：

```
🔗 https://twitter.com/i/oauth2/authorize?response_type=code&client_id=...
```

**操作步骤**:

1. **复制整个 URL**（完整复制，包括所有参数）

2. **在本地浏览器打开**
   - Windows: 粘贴到 Chrome/Edge/Firefox
   - Mac: 粘贴到 Safari/Chrome
   - 任何能访问互联网的浏览器都可以

3. **登录 Twitter**
   - 如果未登录，输入您的 Twitter 账号密码
   - 如果已登录，会直接进入授权页面

4. **授权应用**
   - 查看应用请求的权限
   - 点击 "Authorize app" 按钮

5. **获取授权码**
   - 浏览器会跳转到 `http://localhost:8080/callback?code=...`
   - 页面会显示"无法访问此网站"或"连接被拒绝" - **这是正常的！**
   - 重点是地址栏的 URL

### 步骤 4: 复制授权码

从浏览器地址栏复制授权码：

**示例 URL**:
```
http://localhost:8080/callback?code=VGNWbEFVMTJPVGRRTUV0Wk1sRXdaejA5&state=abc123
```

**授权码** (code= 后面的部分):
```
VGNWbEFVMTJPVGRRTUV0Wk1sRXdaejA5
```

**注意**:
- 只复制 `code=` 和 `&state` 之间的内容
- 不要包含 `code=`
- 不要包含 `&state=...` 后面的部分

### 步骤 5: 粘贴授权码到服务器

回到 SSH 终端，粘贴授权码：

```
请粘贴授权码 (code): VGNWbEFVMTJPVGRRTUV0Wk1sRXdaejA5
```

### 步骤 6: 完成

工具会自动：
- ✅ 使用授权码交换 access_token
- ✅ 保存 Token 到配置文件
- ✅ 显示 Token 信息

## 🔧 方法 2 详细步骤

### 在本地电脑操作

```bash
# 1. 克隆项目到本地
git clone https://github.com/qiqi-feeder/twitter_bot.git
cd twitter_bot

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置 Client ID 和 Secret
# 编辑 config/config.yaml

# 4. 运行授权工具（本地版）
python tools/oauth2_authorize.py
```

### 上传 Token 到服务器

授权完成后，从本地的 `config/config.yaml` 复制以下内容：

```yaml
twitter:
  access_token: "dnpCRnpXeWE4b2lzQk10MDlWSmhBRU..."
  refresh_token: "a2ZTZV9PcVk0WXlwNzBwNFZBUkVaS2..."
  token_expires_at: "2024-02-20T15:30:00"
```

使用 SCP 或直接编辑服务器上的配置文件：

```bash
# 方式 1: 使用 SCP
scp config/config.yaml user@server:/path/to/twitter_bot/config/

# 方式 2: 直接在服务器上编辑
ssh user@server
cd /path/to/twitter_bot
vim config/config.yaml
# 粘贴 Token 信息
```

## ⚠️ 重要注意事项

### 1. 授权码有效期很短

- 授权码通常只有 **5-10 分钟** 有效期
- 授权码只能使用 **一次**
- 如果超时或失败，需要重新获取新的授权码

### 2. 回调 URL 配置

虽然服务器上没有运行回调服务器，但 Twitter App 的回调 URL 仍然必须配置为：

```
http://localhost:8080/callback
```

这是因为 OAuth 2.0 流程需要这个 URL 来生成授权码。

### 3. 浏览器跳转"失败"是正常的

当浏览器跳转到 `http://localhost:8080/callback` 时：
- ✅ 显示"无法访问此网站"是**正常的**
- ✅ 显示"连接被拒绝"是**正常的**
- ✅ 重点是 URL 中包含了授权码

### 4. 代理配置

如果服务器需要代理访问 Twitter API：

```yaml
proxy:
  socks5_url: "socks5://user:pass@proxy.example.com:1080"
  enabled: true
```

授权工具会自动使用代理。

## 🔄 Token 自动刷新

一旦获取了初始 Token，系统会自动刷新：

```
应用运行 → Token 即将过期 → 自动刷新 → 保存新 Token
```

您不需要重复授权流程，除非：
- refresh_token 也过期了（通常 6 个月）
- 手动撤销了应用授权
- 更换了 Twitter 账号

## 🛠️ 故障排除

### 问题 1: 授权码交换失败

```
❌ 交换访问令牌失败
```

**可能原因**:
1. 授权码已过期
2. 授权码复制不完整
3. 网络连接问题
4. 代理配置错误

**解决方案**:
- 重新运行工具获取新的授权码
- 确保完整复制授权码（不包含 `code=` 和 `&state`）
- 检查网络连接
- 检查代理配置

### 问题 2: 无法生成授权 URL

```
❌ 未配置有效的 Client ID
```

**解决方案**:
检查 `config/config.yaml` 中的 `client_id` 是否正确填写。

### 问题 3: 代理超时

```
ERROR - Read timed out
```

**解决方案**:
1. 检查代理配置
2. 增加超时时间（已默认设置为 60 秒）
3. 测试代理连接：
   ```bash
   curl -x socks5://proxy.example.com:1080 https://api.twitter.com
   ```

## 📚 相关文档

- [快速开始指南](GET_STARTED.md)
- [OAuth 2.0 详细指南](OAUTH2_GUIDE.md)
- [Token 刷新指南](TOKEN_REFRESH_GUIDE.md)

## 💡 最佳实践

1. **使用 screen 或 tmux**
   ```bash
   screen -S twitter_bot
   python app.py
   # Ctrl+A, D 分离会话
   ```

2. **设置系统服务**
   ```bash
   # 创建 systemd 服务
   sudo vim /etc/systemd/system/twitter_bot.service
   ```

3. **定期备份配置**
   ```bash
   cp config/config.yaml config/config.yaml.backup
   ```

4. **监控日志**
   ```bash
   tail -f logs/twitter_bot.log
   ```

