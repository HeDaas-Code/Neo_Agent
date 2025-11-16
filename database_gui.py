"""
数据库管理GUI组件
提供可视化界面管理数据库内容
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from typing import Dict, Any, List
from database_manager import DatabaseManager


class DatabaseManagerGUI:
    """
    数据库管理GUI界面
    提供数据库的可视化管理、编辑功能
    """

    def __init__(self, parent_frame, db_manager: DatabaseManager):
        """
        初始化数据库管理GUI

        Args:
            parent_frame: 父容器
            db_manager: 数据库管理器实例
        """
        self.parent = parent_frame
        self.db = db_manager

        # 自动刷新相关
        self.auto_refresh_enabled = True
        self.refresh_interval = 2000  # 默认2秒刷新一次
        self.refresh_job = None

        # 创建界面
        self.create_widgets()

        # 首次刷新数据
        self.refresh_all()

        # 启动自动刷新
        self.start_auto_refresh()

        # 绑定窗口关闭事件
        self.parent.bind('<Destroy>', self.on_destroy)

    def on_destroy(self, event=None):
        """窗口销毁时的清理工作"""
        self.stop_auto_refresh()

    def create_widgets(self):
        """
        创建所有GUI组件
        """
        # 顶部工具栏
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(toolbar, text="📑 数据库管理", font=("微软雅黑", 10, "bold")).pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar, text="🔄 刷新全部", command=self.refresh_all, width=10).pack(side=tk.LEFT, padx=2)

        # 自动刷新开关
        self.auto_refresh_btn = ttk.Button(toolbar, text="⏸️ 暂停刷新", command=self.toggle_auto_refresh, width=10)
        self.auto_refresh_btn.pack(side=tk.LEFT, padx=2)

        # 刷新间隔设置
        ttk.Label(toolbar, text="间隔:").pack(side=tk.LEFT, padx=(10, 2))
        self.interval_var = tk.StringVar(value="2")
        interval_combo = ttk.Combobox(toolbar, textvariable=self.interval_var, width=5,
                                     values=["1", "2", "3", "5", "10"])
        interval_combo.pack(side=tk.LEFT, padx=2)
        interval_combo.bind('<<ComboboxSelected>>', self.change_refresh_interval)
        ttk.Label(toolbar, text="秒").pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar, text="📊 统计信息", command=self.show_statistics, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 清空数据", command=self.clear_confirm, width=10).pack(side=tk.LEFT, padx=2)

        # 刷新状态指示器
        self.refresh_indicator = ttk.Label(toolbar, text="🟢", font=("微软雅黑", 12))
        self.refresh_indicator.pack(side=tk.RIGHT, padx=5)

        # 最后刷新时间
        self.last_refresh_label = ttk.Label(toolbar, text="", font=("微软雅黑", 8), foreground="gray")
        self.last_refresh_label.pack(side=tk.RIGHT, padx=5)

        # 统计信息标签
        self.stats_label = ttk.Label(toolbar, text="", font=("微软雅黑", 9))
        self.stats_label.pack(side=tk.RIGHT, padx=10)

        # 分割线
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=2)

        # 创建标签页
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 标签页1：基础知识
        self.create_base_knowledge_tab()

        # 标签页2：实体管理
        self.create_entities_tab()

        # 标签页3：短期记忆
        self.create_short_term_tab()

        # 标签页4：长期记忆
        self.create_long_term_tab()

        # 标签页5：情感分析历史
        self.create_emotion_tab()

    def create_base_knowledge_tab(self):
        """
        创建基础知识管理标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔒 基础知识")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕ 添加", command=self.add_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏️ 编辑", command=self.edit_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 删除", command=self.delete_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)

        # 搜索框
        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT, padx=(20, 5))
        self.base_search_var = tk.StringVar()
        self.base_search_entry = ttk.Entry(toolbar, textvariable=self.base_search_var, width=20)
        self.base_search_entry.pack(side=tk.LEFT, padx=2)
        self.base_search_entry.bind('<Return>', lambda e: self.refresh_base_knowledge())

        # 创建Treeview显示列表
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        # Treeview
        self.base_tree = ttk.Treeview(
            tree_frame,
            columns=("entity", "content", "category", "confidence", "created"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        # 配置列
        self.base_tree.heading("entity", text="实体名称")
        self.base_tree.heading("content", text="内容")
        self.base_tree.heading("category", text="分类")
        self.base_tree.heading("confidence", text="置信度")
        self.base_tree.heading("created", text="创建时间")

        self.base_tree.column("entity", width=120)
        self.base_tree.column("content", width=300)
        self.base_tree.column("category", width=100)
        self.base_tree.column("confidence", width=80)
        self.base_tree.column("created", width=150)

        scrollbar_y.config(command=self.base_tree.yview)
        scrollbar_x.config(command=self.base_tree.xview)

        # 布局
        self.base_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击编辑
        self.base_tree.bind("<Double-1>", lambda e: self.edit_base_knowledge())

    def create_entities_tab(self):
        """
        创建实体管理标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📦 实体管理")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕ 新建实体", command=self.add_entity, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="👁️ 查看详情", command=self.view_entity_detail, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑️ 删除", command=self.delete_entity, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_entities, width=8).pack(side=tk.LEFT, padx=2)

        # 搜索框
        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT, padx=(20, 5))
        self.entity_search_var = tk.StringVar()
        self.entity_search_entry = ttk.Entry(toolbar, textvariable=self.entity_search_var, width=20)
        self.entity_search_entry.pack(side=tk.LEFT, padx=2)
        self.entity_search_entry.bind('<Return>', lambda e: self.refresh_entities())

        # 创建Treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self.entity_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "has_def", "info_count", "created", "updated"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.entity_tree.heading("name", text="实体名称")
        self.entity_tree.heading("has_def", text="有定义")
        self.entity_tree.heading("info_count", text="相关信息数")
        self.entity_tree.heading("created", text="创建时间")
        self.entity_tree.heading("updated", text="更新时间")

        self.entity_tree.column("name", width=200)
        self.entity_tree.column("has_def", width=80)
        self.entity_tree.column("info_count", width=100)
        self.entity_tree.column("created", width=150)
        self.entity_tree.column("updated", width=150)

        scrollbar_y.config(command=self.entity_tree.yview)
        scrollbar_x.config(command=self.entity_tree.xview)

        self.entity_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击查看详情
        self.entity_tree.bind("<Double-1>", lambda e: self.view_entity_detail())

    def create_short_term_tab(self):
        """
        创建短期记忆标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="💭 短期记忆")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🗑️ 清空全部", command=self.clear_short_term, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_short_term, width=8).pack(side=tk.LEFT, padx=2)

        self.short_term_count_label = ttk.Label(toolbar, text="消息数: 0", font=("微软雅黑", 9))
        self.short_term_count_label.pack(side=tk.RIGHT, padx=10)

        # 显示区域
        text_frame = ttk.Frame(tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.short_term_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9"
        )
        self.short_term_text.pack(fill=tk.BOTH, expand=True)

        # 配置标签颜色
        self.short_term_text.tag_config("user", foreground="#0066cc", font=("微软雅黑", 9, "bold"))
        self.short_term_text.tag_config("assistant", foreground="#ff6600", font=("微软雅黑", 9, "bold"))
        self.short_term_text.tag_config("timestamp", foreground="#999999", font=("微软雅黑", 8))

    def create_long_term_tab(self):
        """
        创建长期记忆标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📚 长期记忆")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🗑️ 清空全部", command=self.clear_long_term, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_long_term, width=8).pack(side=tk.LEFT, padx=2)

        self.long_term_count_label = ttk.Label(toolbar, text="概括数: 0", font=("微软雅黑", 9))
        self.long_term_count_label.pack(side=tk.RIGHT, padx=10)

        # 显示区域
        text_frame = ttk.Frame(tab)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.long_term_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            font=("微软雅黑", 9),
            bg="#f9f9f9"
        )
        self.long_term_text.pack(fill=tk.BOTH, expand=True)

    def create_emotion_tab(self):
        """
        创建情感分析历史标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="💖 情感分析")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="👁️ 查看详情", command=self.view_emotion_detail, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_emotion, width=8).pack(side=tk.LEFT, padx=2)

        self.emotion_count_label = ttk.Label(toolbar, text="分析数: 0", font=("微软雅黑", 9))
        self.emotion_count_label.pack(side=tk.RIGHT, padx=10)

        # 创建Treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)

        self.emotion_tree = ttk.Treeview(
            tree_frame,
            columns=("relationship", "tone", "score", "created"),
            show="headings",
            yscrollcommand=scrollbar_y.set
        )

        self.emotion_tree.heading("relationship", text="关系类型")
        self.emotion_tree.heading("tone", text="情感基调")
        self.emotion_tree.heading("score", text="总评分")
        self.emotion_tree.heading("created", text="分析时间")

        self.emotion_tree.column("relationship", width=150)
        self.emotion_tree.column("tone", width=150)
        self.emotion_tree.column("score", width=80)
        self.emotion_tree.column("created", width=180)

        scrollbar_y.config(command=self.emotion_tree.yview)

        self.emotion_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击查看详情
        self.emotion_tree.bind("<Double-1>", lambda e: self.view_emotion_detail())

    # ==================== 刷新方法 ====================

    def refresh_all(self):
        """刷新所有标签页数据"""
        # 显示刷新中状态
        self.refresh_indicator.config(text="🔄")

        try:
            self.refresh_base_knowledge()
            self.refresh_entities()
            self.refresh_short_term()
            self.refresh_long_term()
            self.refresh_emotion()
            self.update_statistics()

            # 刷新完成，显示绿色指示器和时间戳
            self.refresh_indicator.config(text="🟢")
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            self.last_refresh_label.config(text=f"最后刷新: {current_time}")
        except Exception as e:
            # 刷新出错，显示红色指示器
            self.refresh_indicator.config(text="🔴")
            print(f"刷新数据时出错: {e}")

    def refresh_base_knowledge(self):
        """刷新基础知识列表"""
        # 保存当前选中项
        selected_items = self.base_tree.selection()
        selected_ids = []
        for item in selected_items:
            tags = self.base_tree.item(item)['tags']
            if tags:
                selected_ids.append(tags[0])

        # 清空现有项
        for item in self.base_tree.get_children():
            self.base_tree.delete(item)

        # 获取所有基础知识
        base_facts = self.db.get_all_base_facts()

        # 应用搜索过滤
        search_text = self.base_search_var.get().lower()
        if search_text:
            base_facts = [f for f in base_facts if search_text in f['entity_name'].lower() or search_text in f['content'].lower()]

        # 添加到树形视图
        for fact in base_facts:
            item_id = self.base_tree.insert("", "end", values=(
                fact['entity_name'],
                fact['content'][:50] + "..." if len(fact['content']) > 50 else fact['content'],
                fact['category'],
                f"{fact['confidence']:.2f}",
                fact['created_at'][:19] if fact.get('created_at') else ""
            ), tags=(fact['id'],))

            # 恢复选中状态
            if fact['id'] in selected_ids:
                self.base_tree.selection_add(item_id)

    def refresh_entities(self):
        """刷新实体列表"""
        # 保存当前选中项
        selected_items = self.entity_tree.selection()
        selected_uuids = []
        for item in selected_items:
            tags = self.entity_tree.item(item)['tags']
            if tags:
                selected_uuids.append(tags[0])

        # 清空现有项
        for item in self.entity_tree.get_children():
            self.entity_tree.delete(item)

        # 获取所有实体
        entities = self.db.get_all_entities()

        # 应用搜索过滤
        search_text = self.entity_search_var.get().lower()
        if search_text:
            entities = [e for e in entities if search_text in e['name'].lower()]

        # 添加到树形视图
        for entity in entities:
            # 获取定义和相关信息
            definition = self.db.get_entity_definition(entity['uuid'])
            related_info = self.db.get_entity_related_info(entity['uuid'])

            item_id = self.entity_tree.insert("", "end", values=(
                entity['name'],
                "是" if definition else "否",
                len(related_info),
                entity['created_at'][:19],
                entity['updated_at'][:19]
            ), tags=(entity['uuid'],))

            # 恢复选中状态
            if entity['uuid'] in selected_uuids:
                self.entity_tree.selection_add(item_id)

    def refresh_short_term(self):
        """刷新短期记忆显示"""
        # 记住当前是否滚动到底部
        was_at_bottom = False
        try:
            # 检查是否在底部附近（允许一点误差）
            yview = self.short_term_text.yview()
            was_at_bottom = yview[1] >= 0.99
        except:
            pass

        self.short_term_text.config(state=tk.NORMAL)
        self.short_term_text.delete(1.0, tk.END)

        messages = self.db.get_short_term_messages()
        self.short_term_count_label.config(text=f"消息数: {len(messages)}")

        for msg in messages:
            role_text = "用户" if msg['role'] == 'user' else "助手"
            timestamp = msg['timestamp'][:19] if msg.get('timestamp') else ""

            self.short_term_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.short_term_text.insert(tk.END, f"{role_text}:\n", msg['role'])
            self.short_term_text.insert(tk.END, f"{msg['content']}\n\n")

        self.short_term_text.config(state=tk.DISABLED)

        # 如果之前在底部，刷新后也滚动到底部（用于查看新消息）
        if was_at_bottom or len(messages) > 0:
            self.short_term_text.see(tk.END)

    def refresh_long_term(self):
        """刷新长期记忆显示"""
        self.long_term_text.config(state=tk.NORMAL)
        self.long_term_text.delete(1.0, tk.END)

        summaries = self.db.get_long_term_summaries()
        self.long_term_count_label.config(text=f"概括数: {len(summaries)}")

        for i, summary in enumerate(summaries, 1):
            self.long_term_text.insert(tk.END, f"━━━━━ 主题 {i} ━━━━━\n", "header")
            self.long_term_text.insert(tk.END, f"时间: {summary['created_at'][:19]} - {summary['ended_at'][:19]}\n")
            self.long_term_text.insert(tk.END, f"轮数: {summary.get('rounds', 0)} 轮 | 消息: {summary.get('message_count', 0)} 条\n")
            self.long_term_text.insert(tk.END, f"\n{summary['summary']}\n\n\n")

        self.long_term_text.config(state=tk.DISABLED)

    def refresh_emotion(self):
        """刷新情感分析历史"""
        # 清空现有项
        for item in self.emotion_tree.get_children():
            self.emotion_tree.delete(item)

        # 获取情感分析历史
        emotions = self.db.get_emotion_history()
        self.emotion_count_label.config(text=f"分析数: {len(emotions)}")

        for emotion in emotions:
            self.emotion_tree.insert("", "end", values=(
                emotion.get('relationship_type', '未知'),
                emotion.get('emotional_tone', '未知'),
                f"{emotion.get('overall_score', 0)}/100",
                emotion['created_at'][:19]
            ), tags=(emotion['uuid'],))

    def update_statistics(self):
        """更新统计信息显示"""
        stats = self.db.get_statistics()
        text = f"基础知识: {stats['base_knowledge_count']} | " \
               f"实体: {stats['entities_count']} | " \
               f"短期记忆: {stats['short_term_count']} | " \
               f"长期记忆: {stats['long_term_count']} | " \
               f"情感分析: {stats['emotion_count']} | " \
               f"DB大��: {stats.get('db_size_kb', 0):.1f} KB"
        self.stats_label.config(text=text)

    # ==================== 自动刷新方法 ====================

    def start_auto_refresh(self):
        """启动自动刷新"""
        if self.auto_refresh_enabled and self.refresh_job is None:
            self._schedule_refresh()

    def stop_auto_refresh(self):
        """停止自动刷新"""
        if self.refresh_job is not None:
            self.parent.after_cancel(self.refresh_job)
            self.refresh_job = None

    def _schedule_refresh(self):
        """调度下一次刷新"""
        if self.auto_refresh_enabled:
            self.refresh_all()
            self.refresh_job = self.parent.after(self.refresh_interval, self._schedule_refresh)

    def toggle_auto_refresh(self):
        """切换自动刷新状态"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled

        if self.auto_refresh_enabled:
            self.auto_refresh_btn.config(text="⏸️ 暂停刷新")
            self.start_auto_refresh()
        else:
            self.auto_refresh_btn.config(text="▶️ 启动刷新")
            self.stop_auto_refresh()

    def change_refresh_interval(self, event=None):
        """改变刷新间隔"""
        try:
            interval_seconds = float(self.interval_var.get())
            self.refresh_interval = int(interval_seconds * 1000)  # 转换为毫秒

            # 如果正在自动刷新，重新调度
            if self.auto_refresh_enabled:
                self.stop_auto_refresh()
                self.start_auto_refresh()
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的数字！")
            self.interval_var.set("2")

    # ==================== 操作方法 ====================

    def add_base_knowledge(self):
        """添加基础知识"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("添加基础知识")
        dialog.geometry("500x400")

        ttk.Label(dialog, text="实体名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entity_entry = ttk.Entry(dialog, width=40)
        entity_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="内容:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        content_text = tk.Text(dialog, width=40, height=8, wrap=tk.WORD)
        content_text.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="分类:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        category_combo = ttk.Combobox(dialog, width=38, values=["通用", "机构类型", "定义", "规则", "其他"])
        category_combo.set("通用")
        category_combo.grid(row=2, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="描述:").grid(row=3, column=0, padx=10, pady=10, sticky="nw")
        desc_text = tk.Text(dialog, width=40, height=4, wrap=tk.WORD)
        desc_text.grid(row=3, column=1, padx=10, pady=10)

        def save():
            entity_name = entity_entry.get().strip()
            content = content_text.get(1.0, tk.END).strip()
            category = category_combo.get()
            description = desc_text.get(1.0, tk.END).strip()

            if not entity_name or not content:
                messagebox.showwarning("警告", "实体名称和内容不能为空！")
                return

            if self.db.add_base_fact(entity_name, content, category, description, immutable=True):
                messagebox.showinfo("成功", f"已添加基础知识: {entity_name}")
                self.refresh_base_knowledge()
                self.update_statistics()
                dialog.destroy()
            else:
                messagebox.showerror("错误", "添加失败，可能该实体已存在！")

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def edit_base_knowledge(self):
        """编辑基础知识"""
        selection = self.base_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一条基础知识！")
            return

        messagebox.showinfo("提示", "基础知识不可编辑（immutable=True）\n如需修改，请删除后重新添加。")

    def delete_base_knowledge(self):
        """删除基础知识"""
        selection = self.base_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一条基础知识！")
            return

        if messagebox.askyesno("确认", "确定要删除选中的基础知识吗？\n（基础知识一般不应删除）"):
            for item in selection:
                values = self.base_tree.item(item)['values']
                entity_name = values[0]
                self.db.delete_base_fact(entity_name)

            self.refresh_base_knowledge()
            self.update_statistics()
            messagebox.showinfo("成功", "删除完成")

    def add_entity(self):
        """添加新实体"""
        name = simpledialog.askstring("添加实体", "请输入实体名称:")
        if name:
            uuid = self.db.create_entity(name)
            messagebox.showinfo("成功", f"已创建实体: {name}\nUUID: {uuid}")
            self.refresh_entities()
            self.update_statistics()

    def view_entity_detail(self):
        """查看实体详情"""
        selection = self.entity_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个实体！")
            return

        item = selection[0]
        entity_uuid = self.entity_tree.item(item)['tags'][0]

        # 获取实体详细信息
        entity = self.db.get_entity_by_uuid(entity_uuid)
        definition = self.db.get_entity_definition(entity_uuid)
        related_info = self.db.get_entity_related_info(entity_uuid)

        # 创建详情窗口
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"实体详情: {entity['name']}")
        dialog.geometry("700x600")

        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("微软雅黑", 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 显示信息
        text.insert(tk.END, f"实体名称: {entity['name']}\n")
        text.insert(tk.END, f"UUID: {entity['uuid']}\n")
        text.insert(tk.END, f"创建时间: {entity['created_at']}\n")
        text.insert(tk.END, f"更新时间: {entity['updated_at']}\n")
        text.insert(tk.END, "\n" + "="*60 + "\n\n")

        if definition:
            text.insert(tk.END, "【定义】\n", "header")
            text.insert(tk.END, f"{definition['content']}\n")
            text.insert(tk.END, f"类型: {definition['type']} | 置信度: {definition['confidence']:.2f}\n")
            text.insert(tk.END, f"来源: {definition.get('source', '未知')}\n\n")
        else:
            text.insert(tk.END, "【定义】无\n\n")

        text.insert(tk.END, f"【相关信息】({len(related_info)} 条)\n", "header")
        for i, info in enumerate(related_info, 1):
            text.insert(tk.END, f"\n{i}. {info['content']}\n")
            text.insert(tk.END, f"   类型: {info['type']} | 置信度: {info['confidence']:.2f} | 创建时间: {info['created_at'][:19]}\n")

        text.config(state=tk.DISABLED)

        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    def delete_entity(self):
        """删除实体（暂未实现级联删除）"""
        messagebox.showinfo("提示", "实体删除功能需要实现级联删除，暂未开放。")

    def view_emotion_detail(self):
        """查看情感分析详情"""
        selection = self.emotion_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一条情感分析记录！")
            return

        item = selection[0]
        emotion_uuid = self.emotion_tree.item(item)['tags'][0]

        # 获取完整情感分析数据
        emotions = self.db.get_emotion_history()
        emotion = next((e for e in emotions if e['uuid'] == emotion_uuid), None)

        if not emotion:
            return

        # 显示详情
        info = f"""情感分析详情

关系类型: {emotion.get('relationship_type', '未知')}
情感基调: {emotion.get('emotional_tone', '未知')}
总体评分: {emotion.get('overall_score', 0)}/100

五维度评分:
• 亲密度: {emotion.get('intimacy', 0)}/100
• 信任度: {emotion.get('trust', 0)}/100
• 愉悦度: {emotion.get('pleasure', 0)}/100
• 共鸣度: {emotion.get('resonance', 0)}/100
• 依赖度: {emotion.get('dependence', 0)}/100

分析时间: {emotion['created_at']}

分析摘要:
{emotion.get('analysis_summary', '无')}"""

        messagebox.showinfo("情感分析详情", info)

    def clear_short_term(self):
        """清空短期记忆"""
        if messagebox.askyesno("确认", "确定要清空所有短期记忆吗？"):
            if self.db.clear_short_term_memory():
                self.refresh_short_term()
                self.update_statistics()
                messagebox.showinfo("成功", "短期记忆已清空")

    def clear_long_term(self):
        """清空长期记忆"""
        if messagebox.askyesno("确认", "确定要清空所有长期记忆吗？"):
            if self.db.clear_long_term_memory():
                self.refresh_long_term()
                self.update_statistics()
                messagebox.showinfo("成功", "长期记忆已清空")

    def show_statistics(self):
        """显示详细统计信息"""
        stats = self.db.get_statistics()
        info = f"""数据库统计信息

基础知识: {stats['base_knowledge_count']} 条
实体数量: {stats['entities_count']} 个
短期记忆: {stats['short_term_count']} 条消息
长期记忆: {stats['long_term_count']} 个主题概括
情感分析: {stats['emotion_count']} 条记录

数据库文件大小: {stats.get('db_size_kb', 0):.2f} KB"""

        messagebox.showinfo("数据库统计", info)

    def clear_confirm(self):
        """确认清空所有数据"""
        if messagebox.askyesno("警告", "确定要清空所有数据吗？\n此操作不可恢复！", icon='warning'):
            if messagebox.askyesno("二次确认", "真的确定要清空所有数据吗？", icon='warning'):
                # 这里需要实现清空所有数据的功能
                messagebox.showinfo("提示", "清空所有数据功能需要在DatabaseManager中实现。")

