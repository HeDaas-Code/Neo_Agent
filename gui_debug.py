"""
Tkinter调试GUI界面
提供可视化的对话界面和调试功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading
from chat_agent import ChatAgent


class ChatDebugGUI:
    """
    聊天调试GUI主类
    提供完整的可视化聊天和调试界面
    """

    def __init__(self, root):
        """
        初始化GUI界面

        Args:
            root: Tkinter根窗口
        """
        self.root = root
        self.root.title("智能对话代理 - 调试界面")
        self.root.geometry("1200x800")

        # 设置窗口图标（可选）
        try:
            # self.root.iconbitmap('icon.ico')  # 如果有图标文件可以取消注释
            pass
        except:
            pass

        # 初始化聊天代理
        self.agent = None
        self.is_processing = False

        # 创建UI组件
        self.create_widgets()

        # 初始化代理
        self.initialize_agent()

        # 绑定快捷键
        self.root.bind('<Return>', lambda e: self.send_message() if not e.state & 0x1 else None)
        self.root.bind('<Control-Return>', lambda e: self.input_text.insert(tk.INSERT, '\n'))

    def create_widgets(self):
        """
        创建所有UI组件
        """
        # 主容器 - 使用PanedWindow分割左右两部分
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧面板 - 聊天区域
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # 右侧面板 - 调试信息
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        # ========== 左侧聊天区域 ==========

        # 顶部标题栏
        title_frame = ttk.Frame(left_frame)
        title_frame.pack(fill=tk.X, padx=5, pady=5)

        title_label = ttk.Label(
            title_frame,
            text="💬 智能对话系统",
            font=("微软雅黑", 16, "bold")
        )
        title_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(
            title_frame,
            text="● 就绪",
            foreground="green",
            font=("微软雅黑", 10)
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        # 角色信息栏
        self.character_frame = ttk.LabelFrame(left_frame, text="📋 当前角色", padding=10)
        self.character_frame.pack(fill=tk.X, padx=5, pady=5)

        self.character_label = ttk.Label(
            self.character_frame,
            text="加载中...",
            font=("微软雅黑", 9)
        )
        self.character_label.pack()

        # 聊天显示区域
        chat_frame = ttk.Frame(left_frame)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 11),
            bg="#f5f5f5",
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)

        # 配置文本标签样式
        self.chat_display.tag_config("user", foreground="#0066cc", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("assistant", foreground="#ff6600", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("system", foreground="#666666", font=("微软雅黑", 9, "italic"))
        self.chat_display.tag_config("timestamp", foreground="#999999", font=("微软雅黑", 8))

        # 输入区域
        input_frame = ttk.LabelFrame(left_frame, text="✏️ 输入消息", padding=5)
        input_frame.pack(fill=tk.X, padx=5, pady=5)

        # 输入文本框
        self.input_text = tk.Text(
            input_frame,
            height=4,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            relief=tk.SOLID,
            borderwidth=1
        )
        self.input_text.pack(fill=tk.X, padx=5, pady=5)

        # 按钮区域
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        self.send_button = ttk.Button(
            button_frame,
            text="发送 (Enter)",
            command=self.send_message,
            style="Accent.TButton"
        )
        self.send_button.pack(side=tk.LEFT, padx=2)

        self.clear_input_button = ttk.Button(
            button_frame,
            text="清空输入",
            command=self.clear_input
        )
        self.clear_input_button.pack(side=tk.LEFT, padx=2)

        self.clear_chat_button = ttk.Button(
            button_frame,
            text="清空对话",
            command=self.clear_chat_display
        )
        self.clear_chat_button.pack(side=tk.LEFT, padx=2)

        # ========== 右侧调试区域 ==========

        # 调试选项卡
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 选项卡1: 系统信息
        info_tab = ttk.Frame(notebook)
        notebook.add(info_tab, text="系统信息")

        self.info_display = scrolledtext.ScrolledText(
            info_tab,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.info_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.info_display.config(state=tk.DISABLED)

        # 选项卡2: 对话历史
        history_tab = ttk.Frame(notebook)
        notebook.add(history_tab, text="对话历史")

        self.history_display = scrolledtext.ScrolledText(
            history_tab,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.history_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.history_display.config(state=tk.DISABLED)

        # 选项卡3: 记忆统计
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="记忆统计")

        self.stats_display = scrolledtext.ScrolledText(
            stats_tab,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.stats_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.stats_display.config(state=tk.DISABLED)

        # 选项卡4: 控制面板
        control_tab = ttk.Frame(notebook)
        notebook.add(control_tab, text="控制面板")

        control_container = ttk.Frame(control_tab, padding=10)
        control_container.pack(fill=tk.BOTH, expand=True)

        # 控制按钮
        ttk.Label(control_container, text="记忆管理", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Button(
            control_container,
            text="🔄 刷新统计信息",
            command=self.refresh_stats,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="📜 查看完整历史",
            command=self.show_full_history,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="🗑️ 清空所有记忆",
            command=self.clear_all_memory,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Separator(control_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        ttk.Label(control_container, text="系统设置", font=("微软雅黑", 10, "bold")).pack(anchor=tk.W, pady=5)

        ttk.Button(
            control_container,
            text="♻️ 重新加载代理",
            command=self.reload_agent,
            width=25
        ).pack(fill=tk.X, pady=2)

        ttk.Button(
            control_container,
            text="ℹ️ 关于",
            command=self.show_about,
            width=25
        ).pack(fill=tk.X, pady=2)

    def initialize_agent(self):
        """
        初始化聊天代理
        """
        try:
            self.update_status("初始化中...", "orange")
            self.agent = ChatAgent()

            # 更新角色信息显示
            self.update_character_info()

            # 更新系统信息
            self.update_system_info()

            # 更新统计信息
            self.refresh_stats()

            # 显示欢迎消息
            self.add_system_message("系统初始化完成！开始对话吧～")

            self.update_status("就绪", "green")

        except Exception as e:
            self.update_status("初始化失败", "red")
            messagebox.showerror("初始化错误", f"初始化聊天代理时出错：\n{str(e)}")

    def update_character_info(self):
        """
        更新角色信息显示
        """
        if self.agent:
            char_info = self.agent.get_character_info()
            info_text = f"姓名: {char_info['name']} | 性别: {char_info['gender']} | 身份: {char_info['role']} | "
            info_text += f"年龄: {char_info['age']}岁 | 身高: {char_info['height']} | 体重: {char_info['weight']}\n"
            info_text += f"性格: {char_info['personality']}"

            self.character_label.config(text=info_text)

    def update_system_info(self):
        """
        更新系统信息显示
        """
        if not self.agent:
            return

        info = []
        info.append("=" * 40)
        info.append("系统信息")
        info.append("=" * 40)
        info.append("")

        # 角色信息
        char_info = self.agent.get_character_info()
        info.append("【角色信息】")
        for key, value in char_info.items():
            info.append(f"  {key}: {value}")

        info.append("")
        info.append("【系统配置】")
        info.append(f"  记忆文件: {self.agent.memory_manager.memory_file}")
        info.append(f"  最大记忆条数: {self.agent.memory_manager.max_messages}")
        info.append(f"  API模型: {self.agent.llm.model_name}")
        info.append(f"  温度参数: {self.agent.llm.temperature}")
        info.append(f"  最大Token: {self.agent.llm.max_tokens}")

        self.update_text_widget(self.info_display, "\n".join(info))

    def refresh_stats(self):
        """
        刷新记忆统计信息
        """
        if not self.agent:
            return

        stats = self.agent.get_memory_stats()

        stats_text = []
        stats_text.append("=" * 40)
        stats_text.append("记忆统计")
        stats_text.append("=" * 40)
        stats_text.append("")
        stats_text.append(f"总消息数: {stats['total_messages']}")
        stats_text.append(f"用户消息: {stats['user_messages']}")
        stats_text.append(f"助手消息: {stats['assistant_messages']}")
        stats_text.append(f"总对话轮次: {stats['total_conversations']}")
        stats_text.append("")
        stats_text.append(f"创建时间: {stats['created_at']}")
        stats_text.append(f"记忆文件: {stats['memory_file']}")

        self.update_text_widget(self.stats_display, "\n".join(stats_text))

    def show_full_history(self):
        """
        显示完整对话历史
        """
        if not self.agent:
            return

        history = self.agent.get_conversation_history()

        if not history:
            self.update_text_widget(self.history_display, "暂无对话历史")
            return

        history_text = []
        history_text.append("=" * 40)
        history_text.append(f"完整对话历史 (共 {len(history)} 条)")
        history_text.append("=" * 40)
        history_text.append("")

        for i, msg in enumerate(history, 1):
            role = "用户" if msg['role'] == 'user' else self.agent.character.name
            timestamp = msg.get('timestamp', 'Unknown')
            history_text.append(f"[{i}] {timestamp}")
            history_text.append(f"{role}: {msg['content']}")
            history_text.append("-" * 40)

        self.update_text_widget(self.history_display, "\n".join(history_text))

    def update_text_widget(self, widget, text):
        """
        更新文本组件内容

        Args:
            widget: 文本组件
            text: 要显示的文本
        """
        widget.config(state=tk.NORMAL)
        widget.delete(1.0, tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def update_status(self, status: str, color: str = "black"):
        """
        更新状态标签

        Args:
            status: 状态文本
            color: 文字颜色
        """
        self.status_label.config(text=f"● {status}", foreground=color)
        self.root.update()

    def add_message_to_display(self, role: str, content: str):
        """
        在聊天显示区添加消息

        Args:
            role: 角色类型
            content: 消息内容
        """
        self.chat_display.config(state=tk.NORMAL)

        # 添加时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")

        # 添加角色名和消息
        if role == "user":
            self.chat_display.insert(tk.END, "你: ", "user")
        elif role == "assistant":
            name = self.agent.character.name if self.agent else "助手"
            self.chat_display.insert(tk.END, f"{name}: ", "assistant")

        self.chat_display.insert(tk.END, f"{content}\n\n")

        # 自动滚动到底部
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def add_system_message(self, message: str):
        """
        添加系统消息

        Args:
            message: 系统消息内容
        """
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[系统] {message}\n\n", "system")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def send_message(self):
        """
        发送消息
        """
        if self.is_processing:
            messagebox.showwarning("请稍候", "正在处理上一条消息，请稍候...")
            return

        if not self.agent:
            messagebox.showerror("错误", "聊天代理未初始化")
            return

        # 获取用户输入
        user_input = self.input_text.get(1.0, tk.END).strip()

        if not user_input:
            messagebox.showwarning("提示", "请输入消息内容")
            return

        # 显示用户消息
        self.add_message_to_display("user", user_input)

        # 清空输入框
        self.input_text.delete(1.0, tk.END)

        # 在新线程中处理，避免界面冻结
        self.is_processing = True
        self.update_status("思考中...", "orange")
        self.send_button.config(state=tk.DISABLED)

        def process_chat():
            try:
                # 调用代理获取回复
                response = self.agent.chat(user_input)

                # 在主线程中更新UI
                self.root.after(0, lambda: self.handle_response(response))

            except Exception as e:
                error_msg = f"处理消息时出错: {str(e)}"
                self.root.after(0, lambda: self.handle_error(error_msg))

        thread = threading.Thread(target=process_chat, daemon=True)
        thread.start()

    def handle_response(self, response: str):
        """
        处理代理回复

        Args:
            response: 代理的回复内容
        """
        # 显示助手回复
        self.add_message_to_display("assistant", response)

        # 更新统计信息
        self.refresh_stats()

        # 恢复状态
        self.is_processing = False
        self.update_status("就绪", "green")
        self.send_button.config(state=tk.NORMAL)

        # 焦点回到输入框
        self.input_text.focus()

    def handle_error(self, error_msg: str):
        """
        处理错误

        Args:
            error_msg: 错误消息
        """
        self.add_system_message(f"错误: {error_msg}")
        messagebox.showerror("错误", error_msg)

        self.is_processing = False
        self.update_status("出错", "red")
        self.send_button.config(state=tk.NORMAL)

    def clear_input(self):
        """
        清空输入框
        """
        self.input_text.delete(1.0, tk.END)

    def clear_chat_display(self):
        """
        清空聊天显示区（不删除记忆）
        """
        result = messagebox.askyesno("确认", "确定要清空聊天显示区吗？\n（不会删除历史记忆）")
        if result:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.add_system_message("聊天显示区已清空")

    def clear_all_memory(self):
        """
        清空所有记忆
        """
        result = messagebox.askyesno(
            "警告",
            "确定要清空所有记忆吗？\n此操作不可恢复！",
            icon='warning'
        )

        if result:
            if self.agent:
                self.agent.clear_memory()
                self.refresh_stats()
                self.chat_display.config(state=tk.NORMAL)
                self.chat_display.delete(1.0, tk.END)
                self.chat_display.config(state=tk.DISABLED)
                self.add_system_message("所有记忆已清空")
                self.update_text_widget(self.history_display, "暂无对话历史")

    def reload_agent(self):
        """
        重新加载代理
        """
        result = messagebox.askyesno("确认", "确定要重新加载代理吗？\n将重新读取配置文件")
        if result:
            self.initialize_agent()
            messagebox.showinfo("成功", "代理已重新加载")

    def show_about(self):
        """
        显示关于对话框
        """
        about_text = """
智能对话代理 v1.0
基于LangChain和Python开发

功能特性:
• 角色扮演对话
• 长效记忆系统
• 对话历史持久化
• 可视化调试界面

开发: 2025
技术栈: Python + Tkinter + LangChain
        """
        messagebox.showinfo("关于", about_text)


def main():
    """
    主函数
    """
    # 创建主窗口
    root = tk.Tk()

    # 设置主题样式
    style = ttk.Style()
    try:
        style.theme_use('clam')  # 使用clam主题
    except:
        pass

    # 创建GUI实例
    app = ChatDebugGUI(root)

    # 运行主循环
    root.mainloop()


if __name__ == '__main__':
    main()

