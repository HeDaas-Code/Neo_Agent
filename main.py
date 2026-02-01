#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Main Entry Point
主程序入口

启动 Neo Agent 图形界面应用
"""

import sys
import os

# Add the project root to the Python path
# This ensures imports work whether running from project root or elsewhere
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Check if we can import required modules before proceeding
try:
    import tkinter as tk
    from tkinter import ttk
except ImportError as e:
    print("错误 / Error: Tkinter is not available.")
    print("请确保已安装Python的Tkinter模块。")
    print("Please ensure Python's Tkinter module is installed.")
    print(f"详细错误 / Details: {e}")
    sys.exit(1)

# Import the main GUI class
try:
    from src.gui.gui_enhanced import EnhancedChatDebugGUI
except ImportError as e:
    print("错误 / Error: Failed to import application modules.")
    print("请确保在项目根目录运行此脚本。")
    print("Please ensure you run this script from the project root directory.")
    print(f"当前目录 / Current directory: {os.getcwd()}")
    print(f"脚本位置 / Script location: {project_root}")
    print(f"详细错误 / Details: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def main():
    """主函数 - 启动GUI应用"""
    try:
        root = tk.Tk()
        
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
        
        app = EnhancedChatDebugGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"启动失败 / Failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
