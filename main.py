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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk
from src.gui.gui_enhanced import EnhancedChatDebugGUI


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
