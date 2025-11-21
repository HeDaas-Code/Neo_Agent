@echo off
REM Live2D桌宠助手 - 小可 启动脚本 (Windows)

echo ========================================
echo    Live2D桌宠助手 - 小可 🌸
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: 未找到Python，请先安装Python 3.8或更高版本
    echo    下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ 找到Python: %PYTHON_VERSION%
echo.

REM 检查依赖
echo 检查依赖...
python -c "import tkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误: tkinter未安装
    echo    请重新安装Python并确保勾选tcl/tk选项
    pause
    exit /b 1
)

python -c "import dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  警告: python-dotenv未安装，正在安装依赖...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ❌ 错误: 依赖安装失败
        pause
        exit /b 1
    )
)

echo ✓ 依赖检查完成
echo.

REM 检查配置文件
if not exist ".env" (
    echo ⚠️  警告: 未找到.env配置文件
    if exist "example.env" (
        echo 正在从example.env创建.env...
        copy example.env .env >nul
        echo ✓ 已创建.env文件，请编辑此文件配置你的API密钥
    ) else (
        echo ❌ 错误: 未找到example.env文件
        pause
        exit /b 1
    )
    echo.
)

REM 启动应用
echo 启动Live2D助手...
echo ========================================
echo.

python live2d_assistant.py

REM 检查退出状态
if %errorlevel% neq 0 (
    echo.
    echo ❌ 应用异常退出
    echo.
    echo 故障排查：
    echo 1. 检查.env文件是否正确配置
    echo 2. 查看debug.log文件获取详细错误信息
    echo 3. 确保所有依赖已正确安装
    echo.
    pause
    exit /b 1
)
