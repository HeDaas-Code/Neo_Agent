#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Qt GUI并截图
"""

import sys
import os
import tempfile
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.chat_gui_qt import ChatGUIQt


def capture_screenshot():
    """启动GUI并截图"""
    app = QApplication(sys.argv)
    window = ChatGUIQt()
    window.show()
    
    # 使用系统临时目录以支持跨平台
    screenshot_path = os.path.join(tempfile.gettempdir(), 'qt_gui_screenshot.png')
    
    # 如果debug模式开启，也截取debug窗口
    debug_screenshot_path = None
    if window.debug_window and window.debug_window.isVisible():
        debug_screenshot_path = os.path.join(tempfile.gettempdir(), 'qt_debug_window.png')
    
    # 等待窗口完全渲染
    def take_screenshot():
        screenshot = window.grab()
        screenshot.save(screenshot_path)
        print(f"主窗口截图已保存到: {screenshot_path}")
        
        # 截取debug窗口（如果存在）
        if window.debug_window and window.debug_window.isVisible():
            debug_screenshot = window.debug_window.grab()
            debug_screenshot.save(debug_screenshot_path)
            print(f"调试窗口截图已保存到: {debug_screenshot_path}")
        
        app.quit()
    
    # 延迟截图以确保界面完全加载
    QTimer.singleShot(2000, take_screenshot)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    capture_screenshot()
