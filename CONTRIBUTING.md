# 贡献指南

感谢您对 Twitter 自动发推系统项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告问题

如果您发现了 bug 或有功能建议，请：

1. 检查 [Issues](https://github.com/qiqi-feeder/twitter_bot/issues) 确保问题尚未被报告
2. 创建新的 Issue，详细描述问题或建议
3. 提供尽可能多的相关信息（错误信息、环境信息等）

### 提交代码

1. **Fork 项目**
   ```bash
   # 点击 GitHub 页面上的 Fork 按钮
   ```

2. **克隆您的 Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/twitter_bot.git
   cd twitter_bot
   ```

3. **创建功能分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **进行更改**
   - 遵循现有的代码风格
   - 添加必要的注释
   - 更新相关文档

5. **测试您的更改**
   ```bash
   python test_config.py
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "Add: 描述您的更改"
   ```

7. **推送到您的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建 Pull Request**
   - 在 GitHub 上创建 Pull Request
   - 详细描述您的更改
   - 链接相关的 Issues

## 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用 4 个空格缩进
- 行长度不超过 120 字符
- 使用有意义的变量和函数名

### 注释规范

- 为所有公共函数和类添加文档字符串
- 使用中文注释（项目主要面向中文用户）
- 复杂逻辑添加行内注释

### 提交信息规范

使用以下格式：

```
类型: 简短描述

详细描述（可选）
```

类型包括：
- `Add`: 新增功能
- `Fix`: 修复 bug
- `Update`: 更新现有功能
- `Refactor`: 重构代码
- `Docs`: 文档更新
- `Style`: 代码格式调整
- `Test`: 测试相关

## 开发环境设置

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # 编辑配置文件
   ```

3. **运行测试**
   ```bash
   python test_config.py
   ```

## 项目结构

请确保您的贡献符合项目的模块化结构：

- `auth/`: 认证相关模块
- `twitter/`: Twitter API 交互
- `llm/`: LLM 客户端
- `scheduler/`: 定时任务
- `utils/`: 工具函数
- `config/`: 配置文件

## 需要帮助的领域

我们特别欢迎以下方面的贡献：

- 🐛 Bug 修复
- 📚 文档改进
- 🧪 测试用例
- 🌐 国际化支持
- 🔧 性能优化
- 💡 新功能建议

## 行为准则

- 保持友好和专业的态度
- 尊重不同的观点和经验水平
- 专注于对项目最有利的方案
- 帮助营造包容的社区环境

## 许可证

通过贡献代码，您同意您的贡献将在 MIT 许可证下发布。

## 联系方式

如有任何问题，请通过以下方式联系：

- 创建 [Issue](https://github.com/qiqi-feeder/twitter_bot/issues)
- 发起 [Discussion](https://github.com/qiqi-feeder/twitter_bot/discussions)

感谢您的贡献！🎉
