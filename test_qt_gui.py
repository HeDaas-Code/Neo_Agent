#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Qt GUI并截图
"""

import sys
import os
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
    
    # 等待窗口完全渲染
    def take_screenshot():
        screenshot = window.grab()
        screenshot.save('/tmp/qt_gui_screenshot.png')
        print("截图已保存到: /tmp/qt_gui_screenshot.png")
        app.quit()
    
    # 延迟截图以确保界面完全加载
    QTimer.singleShot(2000, take_screenshot)
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    capture_screenshot()
