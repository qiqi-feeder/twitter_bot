# 使用 Grok API 配置指南

## 📝 快速配置

### 步骤 1: 获取 Grok API Key

1. 访问 Grok 控制台：https://console.x.ai/
2. 登录你的 X (Twitter) 账号
3. 创建或选择一个项目
4. 生成 API Key（格式：`xai-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`）

### 步骤 2: 配置 config.yaml

编辑 `config/config.yaml` 文件，找到 `openai` 部分，修改为：

```yaml
openai:
  # 选择 LLM 提供商: "openai" 或 "grok"
  provider: "grok"
  
  # Grok API Key（从 https://console.x.ai/ 获取）
  grok_api_key: "xai-在这里填入你的 Grok API Key"
  
  # 使用的模型
  # Grok 可用模型: "grok-beta", "grok-vision-beta"
  model: "grok-beta"
  
  # Grok API Base URL（通常不需要修改）
  grok_base_url: "https://api.x.ai/v1"
```

### 步骤 3: 测试

```bash
# 拉取最新代码
git pull origin main

# 运行测试脚本
python tools/test_recap_with_prompt.py
```

---

## 🔧 完整配置示例

### 使用 Grok（推荐）

```yaml
openai:
  provider: "grok"
  grok_api_key: "xai-your-actual-key-here"
  model: "grok-beta"
  grok_base_url: "https://api.x.ai/v1"
```

### 使用 OpenAI

```yaml
openai:
  provider: "openai"
  api_key: "sk-your-openai-key-here"
  model: "gpt-4"
```

---

## 📊 Grok 模型说明

| 模型 | 说明 | 推荐用途 |
|------|------|---------|
| `grok-beta` | Grok 标准模型 | 文本生成、复盘分析 ✅ |
| `grok-vision-beta` | Grok 视觉模型 | 图像理解（暂不支持） |

**推荐使用：** `grok-beta`

---

## ✅ 配置检查清单

- [ ] 已获取 Grok API Key
- [ ] 已在 `config/config.yaml` 中设置 `provider: "grok"`
- [ ] 已填入 `grok_api_key`
- [ ] 已设置 `model: "grok-beta"`
- [ ] 已运行测试脚本验证

---

## 🚀 测试命令

```bash
# 测试完整流程（获取数据 + 生成复盘）
python tools/test_recap_with_prompt.py

# 查看生成的内容
cat data/recap_output.json
```

---

## ❓ 常见问题

### Q1: Grok API Key 在哪里填？

**A:** 在 `config/config.yaml` 文件中，找到 `openai` 部分：

```yaml
openai:
  provider: "grok"
  grok_api_key: "在这里填入你的 Key"  # ← 这里
  model: "grok-beta"
```

### Q2: 如何切换回 OpenAI？

**A:** 修改 `config/config.yaml`：

```yaml
openai:
  provider: "openai"  # 改为 openai
  api_key: "sk-your-openai-key"
  model: "gpt-4"
```

### Q3: Grok 和 OpenAI 有什么区别？

**A:** 
- **Grok**: X (Twitter) 官方 AI，可能更了解 Twitter 风格
- **OpenAI**: GPT-4 质量更稳定，但需要付费

### Q4: 可以同时配置两个吗？

**A:** 可以！两个 API Key 都填上，通过 `provider` 切换：

```yaml
openai:
  provider: "grok"  # 当前使用 grok
  
  # OpenAI 配置（备用）
  api_key: "sk-your-openai-key"
  
  # Grok 配置（当前使用）
  grok_api_key: "xai-your-grok-key"
  
  model: "grok-beta"
```

---

## 🎯 下一步

配置完成后：

1. **测试生成效果**
   ```bash
   python tools/test_recap_with_prompt.py
   ```

2. **调整系统提示词**
   - 编辑 `prompt/system_prompt.md`
   - 根据 Grok 的风格调整提示词

3. **启用定时发布**
   - 编辑 `config/config.yaml`
   - 设置 `scheduler.daily_recap.enabled: true`

---

## 📞 获取帮助

如有问题，请查看：
- [完整使用指南](RECAP_USAGE_GUIDE.md)
- [快速开始](QUICK_START.md)
- [中文使用说明](../使用说明.md)

