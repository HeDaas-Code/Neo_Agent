#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Qt GUI启动脚本
用于启动Qt版本的聊天界面
"""

import sys
import os

# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add the script directory to Python path
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Change to script directory to ensure relative paths work
os.chdir(script_dir)

# Now run the Qt GUI
if __name__ == "__main__":
    try:
        from src.gui.chat_gui_qt import main
        main()
    except ImportError as e:
        print("=" * 60)
        print("导入错误 / Import Error")
        print("=" * 60)
        print(f"无法导入所需模块: {e}")
        print(f"Cannot import required modules: {e}")
        print()
        print("请检查以下事项 / Please check:")
        print("1. 是否在项目根目录运行? / Running from project root?")
        print(f"   当前目录 / Current dir: {os.getcwd()}")
        print("2. 是否安装了所有依赖? / All dependencies installed?")
        print("   运行 / Run: pip install -r requirements.txt")
        print("3. Python版本是否>=3.8? / Python version >= 3.8?")
        print(f"   当前版本 / Current: {sys.version}")
        print("4. 是否安装了PyQt5? / PyQt5 installed?")
        print("   运行 / Run: pip install PyQt5")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print("=" * 60)
        print("运行错误 / Runtime Error")
        print("=" * 60)
        print(f"应用启动失败: {e}")
        print(f"Application failed to start: {e}")
        print()
        import traceback
        traceback.print_exc()
        sys.exit(1)
