#!/bin/bash
# Live2D桌宠助手 - 小可 启动脚本

echo "========================================"
echo "   Live2D桌宠助手 - 小可 🌸"
echo "========================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null
then
    echo "❌ 错误: 未找到Python，请先安装Python 3.8或更高版本"
    exit 1
fi

# 使用python3或python命令
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null
then
    PYTHON_CMD="python"
fi

echo "✓ 找到Python: $($PYTHON_CMD --version)"
echo ""

# 检查依赖
echo "检查依赖..."
$PYTHON_CMD -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 错误: tkinter未安装"
    echo "   Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "   Fedora: sudo dnf install python3-tkinter"
    exit 1
fi

$PYTHON_CMD -c "import dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  警告: python-dotenv未安装，正在安装依赖..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ 错误: 依赖安装失败"
        exit 1
    fi
fi

echo "✓ 依赖检查完成"
echo ""

# 检查配置文件
if [ ! -f ".env" ]; then
    echo "⚠️  警告: 未找到.env配置文件"
    if [ -f "example.env" ]; then
        echo "正在从example.env创建.env..."
        cp example.env .env
        echo "✓ 已创建.env文件，请编辑此文件配置你的API密钥"
    else
        echo "❌ 错误: 未找到example.env文件"
        exit 1
    fi
    echo ""
fi

# 启动应用
echo "启动Live2D助手..."
echo "========================================"
echo ""

$PYTHON_CMD live2d_assistant.py

# 检查退出状态
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 应用异常退出"
    echo ""
    echo "故障排查："
    echo "1. 检查.env文件是否正确配置"
    echo "2. 查看debug.log文件获取详细错误信息"
    echo "3. 确保所有依赖已正确安装"
    exit 1
fi
