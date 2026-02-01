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
    
    # 等待窗口完全渲染
    def take_screenshot():
        screenshot = window.grab()
        screenshot.save(screenshot_path)
        print(f"截图已保存到: {screenshot_path}")
        app.quit()
    
    # 延迟截图以确保界面完全加载
    QTimer.singleShot(2000, take_screenshot)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    capture_screenshot()
