"""
Qt聊天GUI - 仿QQ风格
提供现代化的聊天界面，支持与智能体进行对话
"""

import sys
import os
from datetime import datetime
from typing import Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QSplitter, QScrollArea,
    QFrame, QMessageBox, QMenu, QAction
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPalette, QIcon

from src.core.chat_agent import ChatAgent
from src.tools.debug_logger import get_debug_logger


class MessageBubble(QFrame):
    """
    聊天消息气泡组件
    """
    def __init__(self, message: str, is_user: bool, timestamp: str = None, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.setup_ui(message)
        
    def setup_ui(self, message: str):
        """设置消息气泡UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(3)
        
        # 创建时间标签（小字体，灰色）
        time_label = QLabel(self.timestamp)
        time_label.setFont(QFont("微软雅黑", 8))
        time_label.setStyleSheet("QLabel { color: #999999; }")
        
        # 创建消息标签
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        msg_label.setFont(QFont("微软雅黑", 10))
        msg_label.setTextFormat(Qt.PlainText)  # 防止HTML注入
        
        # 设置样式
        if self.is_user:
            # 用户消息 - 绿色气泡，右对齐
            msg_label.setStyleSheet("""
                QLabel {
                    background-color: #95EC69;
                    color: #000000;
                    padding: 10px 15px;
                    border-radius: 10px;
                    max-width: 500px;
                }
            """)
            layout.addWidget(time_label, 0, Qt.AlignRight)
            layout.addWidget(msg_label, 0, Qt.AlignRight)
        else:
            # AI消息 - 白色气泡，左对齐
            msg_label.setStyleSheet("""
                QLabel {
                    background-color: #FFFFFF;
                    color: #000000;
                    padding: 10px 15px;
                    border-radius: 10px;
                    max-width: 500px;
                    border: 1px solid #E0E0E0;
                }
            """)
            layout.addWidget(time_label, 0, Qt.AlignLeft)
            layout.addWidget(msg_label, 0, Qt.AlignLeft)


class ChatThread(QThread):
    """
    聊天线程 - 处理AI响应
    """
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, agent: ChatAgent, user_message: str):
        super().__init__()
        self.agent = agent
        self.user_message = user_message
        
    def run(self):
        """执行聊天"""
        try:
            response = self.agent.chat(self.user_message)
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatGUIQt(QMainWindow):
    """
    Qt聊天GUI主窗口 - QQ风格
    """
    def __init__(self):
        super().__init__()
        self.agent: Optional[ChatAgent] = None
        self.chat_thread: Optional[ChatThread] = None
        self.debug_logger = get_debug_logger()
        self.debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        
        self.init_ui()
        self.init_agent()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("Neo Agent - 智能对话助手")
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 600)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F5F5F5;
            }
        """)
        
        # 创建中心组件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：侧边栏
        self.create_sidebar(splitter)
        
        # 中间：聊天区域
        self.create_chat_area(splitter)
        
        # 右侧：Debug面板（可选）
        if self.debug_mode:
            self.create_debug_panel(splitter)
        
        splitter.setStretchFactor(0, 0)  # 侧边栏固定宽度
        splitter.setStretchFactor(1, 1)  # 聊天区域可伸缩
        if self.debug_mode:
            splitter.setStretchFactor(2, 0)  # Debug面板固定宽度
        
        main_layout.addWidget(splitter)
        
        # 创建菜单栏
        self.create_menu_bar()
        
    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        debug_action = QAction("调试模式", self, checkable=True)
        debug_action.setChecked(self.debug_mode)
        debug_action.triggered.connect(self.toggle_debug_mode)
        settings_menu.addAction(debug_action)
        
        clear_action = QAction("清空对话", self)
        clear_action.triggered.connect(self.clear_chat)
        settings_menu.addAction(clear_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def create_sidebar(self, parent):
        """创建侧边栏"""
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #2E2E2E;
                border-right: 1px solid #1E1E1E;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 20, 10, 10)
        layout.setSpacing(15)
        
        # 头像区域
        avatar_label = QLabel("🤖")
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setStyleSheet("""
            QLabel {
                font-size: 60px;
                background-color: #3E3E3E;
                border-radius: 50px;
                padding: 20px;
            }
        """)
        avatar_label.setFixedSize(100, 100)
        
        # 名称
        name_label = QLabel(os.getenv('CHARACTER_NAME', 'Neo Agent'))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont("微软雅黑", 14, QFont.Bold))
        name_label.setStyleSheet("QLabel { color: #FFFFFF; }")
        
        # 状态
        self.status_label = QLabel("● 在线")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("QLabel { color: #95EC69; font-size: 12px; }")
        
        # 角色信息
        role_info = QLabel(f"角色: {os.getenv('CHARACTER_ROLE', '助手')}\n"
                          f"年龄: {os.getenv('CHARACTER_AGE', '未知')}\n"
                          f"性格: {os.getenv('CHARACTER_PERSONALITY', '友好')}")
        role_info.setAlignment(Qt.AlignCenter)
        role_info.setWordWrap(True)
        role_info.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
                padding: 10px;
                background-color: #3E3E3E;
                border-radius: 5px;
            }
        """)
        
        # 添加到布局
        layout.addWidget(avatar_label, 0, Qt.AlignHCenter)
        layout.addWidget(name_label)
        layout.addWidget(self.status_label)
        layout.addWidget(role_info)
        layout.addStretch()
        
        parent.addWidget(sidebar)
        
    def create_chat_area(self, parent):
        """创建聊天区域"""
        chat_container = QWidget()
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        
        # 顶部标题栏
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        title_label = QLabel(f"与{os.getenv('CHARACTER_NAME', 'Neo Agent')}对话")
        title_label.setFont(QFont("微软雅黑", 14, QFont.Bold))
        title_label.setStyleSheet("QLabel { color: #333333; }")
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # 消息显示区域
        self.messages_scroll = QScrollArea()
        self.messages_scroll.setWidgetResizable(True)
        self.messages_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F0F0F0;
            }
        """)
        
        self.messages_widget = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(20, 20, 20, 20)
        self.messages_layout.setSpacing(15)
        self.messages_layout.addStretch()
        
        self.messages_scroll.setWidget(self.messages_widget)
        
        # 输入区域
        input_container = QFrame()
        input_container.setFixedHeight(180)
        input_container.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-top: 1px solid #E0E0E0;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(20, 10, 20, 10)
        
        # 工具栏（表情按钮等）
        toolbar_layout = QHBoxLayout()
        
        emoji_btn = QPushButton("😊")
        emoji_btn.setFixedSize(30, 30)
        emoji_btn.setToolTip("插入表情")
        emoji_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
                border-radius: 5px;
            }
        """)
        emoji_btn.clicked.connect(self.show_emoji_menu)
        
        toolbar_layout.addWidget(emoji_btn)
        toolbar_layout.addStretch()
        
        # 输入框
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入消息... (Ctrl+Enter 发送)")
        self.input_text.setFont(QFont("微软雅黑", 10))
        self.input_text.setMaximumHeight(80)
        self.input_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 8px;
                background-color: #FAFAFA;
            }
            QTextEdit:focus {
                border: 1px solid #409EFF;
            }
        """)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.send_button = QPushButton("发送")
        self.send_button.setFixedSize(100, 35)
        self.send_button.setFont(QFont("微软雅黑", 10))
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66B1FF;
            }
            QPushButton:pressed {
                background-color: #3A8EE6;
            }
            QPushButton:disabled {
                background-color: #C0C4CC;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        button_layout.addWidget(self.send_button)
        
        input_layout.addLayout(toolbar_layout)
        input_layout.addWidget(self.input_text)
        input_layout.addLayout(button_layout)
        
        # 添加到主布局
        chat_layout.addWidget(header)
        chat_layout.addWidget(self.messages_scroll)
        chat_layout.addWidget(input_container)
        
        parent.addWidget(chat_container)
        
        # 绑定快捷键
        self.input_text.installEventFilter(self)
        
    def create_debug_panel(self, parent):
        """创建Debug面板"""
        debug_panel = QFrame()
        debug_panel.setFixedWidth(300)
        debug_panel.setStyleSheet("""
            QFrame {
                background-color: #1E1E1E;
                border-left: 1px solid #2E2E2E;
            }
        """)
        
        layout = QVBoxLayout(debug_panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        title = QLabel("🐛 调试信息")
        title.setFont(QFont("微软雅黑", 12, QFont.Bold))
        title.setStyleSheet("QLabel { color: #FFFFFF; }")
        
        # Debug信息显示
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setFont(QFont("Consolas", 9))
        self.debug_text.setStyleSheet("""
            QTextEdit {
                background-color: #2E2E2E;
                color: #00FF00;
                border: 1px solid #3E3E3E;
                border-radius: 5px;
            }
        """)
        
        layout.addWidget(title)
        layout.addWidget(self.debug_text)
        
        parent.addWidget(debug_panel)
        self.debug_panel = debug_panel
        
    def init_agent(self):
        """初始化聊天代理"""
        try:
            self.agent = ChatAgent()
            character_name = os.getenv('CHARACTER_NAME', 'Neo Agent')
            welcome_msg = f"你好！我是{character_name}，很高兴与你交流！有什么我可以帮助你的吗？😊"
            self.add_message(welcome_msg, is_user=False)
            self.log_debug("ChatAgent initialized successfully")
        except Exception as e:
            error_msg = f"初始化失败: {str(e)}"
            self.add_system_message(error_msg)
            self.log_debug(f"ERROR: {error_msg}")
            QMessageBox.critical(self, "错误", error_msg)
            
    def add_message(self, message: str, is_user: bool):
        """添加消息到聊天区域"""
        # 移除stretch（用于在添加新消息后重新添加）
        _ = self.messages_layout.takeAt(self.messages_layout.count() - 1)
        
        # 添加消息气泡
        bubble = MessageBubble(message, is_user)
        self.messages_layout.addWidget(bubble)
        
        # 重新添加stretch
        self.messages_layout.addStretch()
        
        # 滚动到底部
        QTimer.singleShot(100, self.scroll_to_bottom)
        
    def add_system_message(self, message: str):
        """添加系统消息"""
        # 移除stretch（用于在添加新消息后重新添加）
        _ = self.messages_layout.takeAt(self.messages_layout.count() - 1)
        
        # 创建系统消息标签
        sys_label = QLabel(message)
        sys_label.setAlignment(Qt.AlignCenter)
        sys_label.setWordWrap(True)
        sys_label.setFont(QFont("微软雅黑", 9))
        sys_label.setStyleSheet("""
            QLabel {
                color: #999999;
                padding: 5px;
                background-color: transparent;
            }
        """)
        
        self.messages_layout.addWidget(sys_label)
        
        # 重新添加stretch
        self.messages_layout.addStretch()
        
        QTimer.singleShot(100, self.scroll_to_bottom)
        
    def scroll_to_bottom(self):
        """滚动到底部"""
        scrollbar = self.messages_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def send_message(self):
        """发送消息"""
        message = self.input_text.toPlainText().strip()
        
        if not message:
            return
            
        if not self.agent:
            QMessageBox.warning(self, "警告", "聊天代理未初始化")
            return
            
        # 禁用输入
        self.input_text.setEnabled(False)
        self.send_button.setEnabled(False)
        self.status_label.setText("● 输入中...")
        self.status_label.setStyleSheet("QLabel { color: #FFA500; font-size: 12px; }")
        
        # 清空输入框
        self.input_text.clear()
        
        # 添加用户消息
        self.add_message(message, is_user=True)
        self.log_debug(f"User: {message}")
        
        # 创建并启动聊天线程
        self.chat_thread = ChatThread(self.agent, message)
        self.chat_thread.response_ready.connect(self.on_response_ready)
        self.chat_thread.error_occurred.connect(self.on_error)
        self.chat_thread.start()
        
    def on_response_ready(self, response: str):
        """处理AI响应"""
        self.add_message(response, is_user=False)
        self.log_debug(f"AI: {response}")
        
        # 恢复输入
        self.input_text.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_text.setFocus()
        self.status_label.setText("● 在线")
        self.status_label.setStyleSheet("QLabel { color: #95EC69; font-size: 12px; }")
        
    def on_error(self, error_msg: str):
        """处理错误"""
        self.add_system_message(f"错误: {error_msg}")
        self.log_debug(f"ERROR: {error_msg}")
        
        # 恢复输入
        self.input_text.setEnabled(True)
        self.send_button.setEnabled(True)
        self.status_label.setText("● 错误")
        self.status_label.setStyleSheet("QLabel { color: #FF0000; font-size: 12px; }")
        
        QMessageBox.critical(self, "错误", error_msg)
        
    def show_emoji_menu(self):
        """显示表情选择菜单"""
        emojis = [
            "😊", "😂", "😍", "🥰", "😘", "😜", "😎", "🤔",
            "😭", "😱", "😴", "🤗", "👍", "👎", "✌️", "🙏",
            "❤️", "💯", "🎉", "🌟", "🔥", "💪", "👏", "🤝"
        ]
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 10px;
                font-size: 20px;
            }
            QMenu::item:selected {
                background-color: #F0F0F0;
                border-radius: 3px;
            }
        """)
        
        for emoji in emojis:
            action = QAction(emoji, self)
            action.triggered.connect(lambda checked, e=emoji: self.insert_emoji(e))
            menu.addAction(action)
        
        # 显示在表情按钮下方
        cursor_pos = self.mapToGlobal(self.input_text.pos())
        menu.exec_(cursor_pos)
    
    def insert_emoji(self, emoji: str):
        """插入表情到输入框"""
        cursor = self.input_text.textCursor()
        cursor.insertText(emoji)
        self.input_text.setFocus()
    
    def log_debug(self, message: str):
        """记录调试信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        if self.debug_mode and hasattr(self, 'debug_text'):
            self.debug_text.append(log_entry)
            
        self.debug_logger.log_info("ChatGUIQt", message)
        
    def toggle_debug_mode(self, checked: bool):
        """切换调试模式"""
        self.debug_mode = checked
        
        if hasattr(self, 'debug_panel'):
            self.debug_panel.setVisible(checked)
            
        self.log_debug(f"Debug mode: {'ON' if checked else 'OFF'}")
        
    def clear_chat(self):
        """清空对话"""
        reply = QMessageBox.question(
            self, "确认", 
            "确定要清空所有对话吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 清除所有消息
            while self.messages_layout.count() > 1:  # 保留stretch
                item = self.messages_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            self.add_system_message("对话已清空")
            self.log_debug("Chat cleared")
            
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 Neo Agent",
            "Neo Agent - 智能对话助手\n\n"
            "版本: 1.0.0\n"
            "基于 Qt 的现代化聊天界面\n\n"
            "© 2024 Neo Agent Team"
        )
        
    def eventFilter(self, obj, event):
        """事件过滤器 - 处理快捷键"""
        if obj == self.input_text and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and event.modifiers() == Qt.ControlModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
        
    def closeEvent(self, event):
        """关闭事件处理"""
        self.log_debug("Application closing")
        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 设置应用信息
    app.setApplicationName("Neo Agent")
    app.setOrganizationName("Neo Agent Team")
    
    # 创建并显示主窗口
    window = ChatGUIQt()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
