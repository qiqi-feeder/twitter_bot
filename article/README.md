# X Article Automation Bot (X文章自动发布机器人)

这是一个基于 Python 和 Playwright 的自动化脚本，用于在 X (原 Twitter) 上自动发布长文章。它使用“策略模式”来管理浏览器连接，目前主要支持连接到本地手动启动的 Chrome 浏览器（CDP模式），以规避自动化检测。

## 📋 功能特点

*   **反检测**: 通过连接已打开的 Chrome 调试端口，像真人一样操作。
*   **自动流程**:
    *   自动点击 "Write" 进入文章编辑器。
    *   自动填写文章标题 (Title)。
    *   自动填写文章正文 (Body)。
    *   自动点击 "Add photo" -> "Upload" 上传封面图片。
    *   自动在弹窗中点击 "Apply" 确认图片。

## 🛠️ 环境准备

### 1. 安装 Python
确保已安装 Python 3.10 或更高版本。

### 2. 准备 Chrome 浏览器
你需要安装 Google Chrome 浏览器。

### 3. 安装依赖库
在项目根目录下打开终端（CMD 或 PowerShell），运行：

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

## 🚀 运行指南 (本地)

这个项目不需要你把账号密码写在代码里，而是直接复用你已经登录的浏览器状态。

### 第一步：启动调试版 Chrome
你需要用特殊的命令启动 Chrome，开启远程调试端口。

**Windows 命令:**
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_debug_profile"
```
*运行后会弹出一个新的 Chrome 窗口。请在这个窗口中打开 x.com 并**登录你的账号**。保持这个窗口开启。*

### 第二步：运行机器人
在项目根目录下运行：

```bash
python main.py
```

脚本会自动连接到你刚才打开的 Chrome 窗口，并开始执行发布任务。

---

## 💻 如何在另一台设备上运行 (通过 GitHub 迁移)

如果你想把项目迁移到另一台电脑，推荐使用 GitHub。

### 1. 在当前电脑上传代码
在项目根目录执行以下 Git 命令：

```bash
# 初始化仓库
git init

# 添加所有文件 (除了 .gitignore 排除的文件)
git add .

# 提交更改
git commit -m "Initial commit x_article_bot"

# 关联到 GitHub (请先在 GitHub 网页上创建一个空仓库，然后替换下面的 URL)
git remote add origin https://github.com/你的用户名/你的仓库名.git

# 推送代码
git push -u origin master
```

### 2. 在新电脑上部署
1.  **安装环境**: 安装 Python 和 Chrome。
2.  **克隆代码**:
    ```bash
    git clone https://github.com/你的用户名/你的仓库名.git
    cd 你的仓库名
    ```
3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    python -m playwright install chromium
    ```
4.  **准备素材**:
    *   确保 `assets` 文件夹下有封面图片（如果 git 没有上传大图片，需手动放入）。
5.  **运行**:
    *   按照上面的“运行指南”，先启动 Debug Chrome 登录账号。
    *   运行 `python main.py`。

## ⚠️ 注意事项

*   **图片路径**: 默认封面图片在 `assets/cover.jpg` (或代码配置的 .png 文件)。确保该位置有文件。
*   **发布开关**: 默认代码中的 `bot.publish()` 可能是注释状态（为了测试安全），如需真实发布，请在 `main.py` 中取消注释。
*   **元素变动**: 如果 X 页面结构发生变化，可能需要更新 `src/publisher_bot.py` 中的选择器。
