@echo off
echo ============================================================
echo   安装 Twitter Bot 依赖
echo ============================================================
echo.

REM 检测 Python 环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请确保 Python 已安装并添加到 PATH
    pause
    exit /b 1
)

echo [信息] 正在安装依赖...
echo.

REM 安装所有依赖
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   依赖安装完成！
echo ============================================================
echo.
echo 已安装的主要依赖:
echo   - Flask (Web 框架)
echo   - tweepy (Twitter API)
echo   - openai (OpenAI API)
echo   - APScheduler (定时任务)
echo   - pytz (时区支持)
echo   - requests[socks] (SOCKS5 代理)
echo.
echo 下一步:
echo   1. 配置 config/config.yaml
echo   2. 运行授权工具: python tools/oauth2_authorize_remote.py
echo   3. 启动应用: python app.py
echo.
pause

