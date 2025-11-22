# 快速配置指南 🚀

## 第一步：安装依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装宏观数据支持（推荐）
pip install yfinance
```

---

## 第二步：配置 API Keys

### 方案 A：最小配置（推荐新手）

只配置 Grok API，其他数据源使用免费 API：

**编辑 `config/config.local.yaml`：**

```yaml
# LLM API 配置
openai:
  provider: "grok"
  grok_api_key: "xai-你的Grok-API-Key"  # ← 在这里填入
  model: "grok-4-fast-reasoning"

# 数据源配置
data_sources:
  # 爆仓数据（暂时禁用）
  coinglass:
    enabled: false
  
  # L2 数据（使用免费的 DefiLlama）
  l2:
    provider: "defillama"
    enabled: true
  
  # 宏观数据（使用免费的 yfinance）
  macro:
    provider: "yfinance"
    enabled: true
```

### 方案 B：完整配置（推荐进阶用户）

配置所有数据源，获取最完整的市场数据：

**编辑 `config/config.local.yaml`：**

```yaml
# LLM API 配置
openai:
  provider: "grok"
  grok_api_key: "xai-你的Grok-API-Key"
  model: "grok-4-fast-reasoning"

# 数据源配置
data_sources:
  # 爆仓数据（需要注册 Coinglass）
  coinglass:
    api_key: "你的Coinglass-API-Key"  # ← 在这里填入
    enabled: true
  
  # L2 数据
  l2:
    provider: "defillama"
    enabled: true
  
  # 宏观数据
  macro:
    provider: "yfinance"
    enabled: true
```

---

## 第三步：获取 API Keys

### 1️⃣ Grok API Key（必需）

1. 访问：https://console.x.ai/
2. 登录你的 X (Twitter) 账号
3. 点击 "Create API Key"
4. 复制 Key（格式：`xai-xxxxxxxx...`）
5. 粘贴到 `config/config.local.yaml` 中

### 2️⃣ Coinglass API Key（可选）

1. 访问：https://www.coinglass.com/
2. 注册账号并登录
3. 访问：https://www.coinglass.com/api
4. 点击 "Create API Key"
5. 复制 Key
6. 粘贴到 `config/config.local.yaml` 中
7. 设置 `enabled: true`

**价格：**
- 免费版：每天 100 次请求
- 付费版：$29/月起

---

## 第四步：测试配置

运行测试脚本：

```bash
python tools/test_recap_with_prompt.py
```

**预期输出：**

```
✅ 系统提示词加载成功
============================================================
步骤 1/3: 获取市场数据
============================================================
✅ Binance 数据获取成功: BTC $91,691, ETH $3,010
✅ 全球市场数据获取成功: 总市值 $3.21T
✅ 恐惧贪婪指数: 11 (Extreme Fear)
✅ L2 TVL 数据获取成功（DefiLlama），共 5 个 L2
✅ 宏观数据获取成功（yfinance），共 6 个指标

============================================================
步骤 2/3: 使用 LLM 生成复盘内容
============================================================
✅ LLM 生成成功

============================================================
步骤 3/3: 生成的复盘内容
============================================================
【2025-11-20 Web3大盘复盘】BTC微涨0.23%守住91K关口...
```

---

## 常见问题 FAQ

### ❓ yfinance 安装失败？

```bash
# 方案 1：使用国内镜像
pip install yfinance -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方案 2：升级 pip
pip install --upgrade pip
pip install yfinance
```

### ❓ 宏观数据获取失败？

可能原因：
1. 网络问题（Yahoo Finance 可能需要代理）
2. yfinance 版本过旧

解决方案：
```bash
pip install --upgrade yfinance
```

或者暂时禁用宏观数据：
```yaml
data_sources:
  macro:
    enabled: false
```

### ❓ L2 数据为空？

DefiLlama API 偶尔会超时，重新运行测试脚本即可。

### ❓ Coinglass API 返回错误？

检查：
1. API Key 是否正确
2. 是否超过免费版请求限制（100次/天）
3. 网络是否正常

---

## 下一步

配置成功后，你可以：

1. **修改系统提示词**：编辑 `prompt/system_prompt.md`
2. **查看历史复盘**：`data/recaps/` 目录
3. **配置定时任务**：编辑 `config/config.yaml` 中的 `scheduler` 部分
4. **手动发布到 Twitter**：使用 API 端点 `POST /recap/manual`

---

## 需要帮助？

查看详细文档：
- [API Keys 配置指南](API_KEYS_SETUP.md)
- [完整使用指南](RECAP_USAGE_GUIDE.md)
- [快速开始](QUICK_START.md)

