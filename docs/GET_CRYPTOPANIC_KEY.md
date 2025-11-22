# 🔑 如何获取 CryptoPanic API Key（免费）

## 📌 为什么需要 CryptoPanic？

CryptoPanic 是最专业的加密货币新闻聚合平台，提供：
- ✅ 实时加密新闻（BTC、ETH、山寨币）
- ✅ 新闻热度评分和社区投票
- ✅ 按币种、类别筛选
- ✅ **免费版每天 1000 次请求**（足够使用）

---

## 🚀 获取步骤（5 分钟）

### 1️⃣ 访问官网

打开浏览器，访问：**https://cryptopanic.com/**

### 2️⃣ 注册账号

1. 点击右上角 **"Sign Up"**（注册）
2. 填写信息：
   - Email（邮箱）
   - Password（密码）
   - 或者使用 Google/Twitter 账号快速注册

3. 验证邮箱（检查收件箱，点击验证链接）

### 3️⃣ 获取 API Key

1. 登录后，访问：**https://cryptopanic.com/developers/api/**
2. 点击 **"Get your free API key"**
3. 填写简单信息：
   - Application Name（应用名称）：填 `Twitter Bot` 或任意名称
   - Description（描述）：填 `Daily crypto market recap` 或任意描述
   - Website（可选）：可以留空

4. 点击 **"Create"**
5. 复制生成的 **API Key**（格式：`xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

### 4️⃣ 配置到项目

编辑 `config/config.local.yaml`：

```yaml
data_sources:
  news:
    provider: "cryptopanic"  # 切换到 CryptoPanic
    enabled: true
    cryptopanic_api_key: "粘贴你的API-Key"  # ← 这里粘贴
```

### 5️⃣ 测试

```bash
python tools/test_recap_with_prompt.py
```

查看日志，应该看到：
```
✅ 新闻获取成功（CryptoPanic），共 5 条
```

---

## 📊 免费版限制

| 项目 | 免费版 | 付费版 |
|------|--------|--------|
| 每天请求次数 | 1,000 次 | 无限制 |
| 新闻数量 | 全部 | 全部 |
| 历史数据 | 7 天 | 无限制 |
| 价格 | **免费** | $9.99/月起 |

**对于每日复盘，免费版完全够用！**

---

## ❓ 常见问题

### Q1: 我没有收到验证邮件怎么办？

- 检查垃圾邮件文件夹
- 重新发送验证邮件
- 使用 Google/Twitter 账号注册（无需邮箱验证）

### Q2: API Key 在哪里查看？

登录后访问：https://cryptopanic.com/developers/api/

### Q3: 免费版够用吗？

完全够用！每天复盘只调用 1 次，远低于 1000 次限制。

### Q4: 可以不配置新闻吗？

可以！在 `config/config.local.yaml` 中设置：

```yaml
data_sources:
  news:
    enabled: false  # 禁用新闻
```

但是系统提示词中的"市场重磅新闻"板块会由 Grok AI 根据市场数据推测，可能不准确。

---

## 🎯 总结

1. 访问：https://cryptopanic.com/
2. 注册账号
3. 获取 API Key：https://cryptopanic.com/developers/api/
4. 配置到 `config/config.local.yaml`
5. 测试：`python tools/test_recap_with_prompt.py`

**5 分钟搞定，完全免费！** 🚀

