"""
数据库管理GUI组件
提供可视化界面管理数据库内容
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from typing import Dict, Any, List
from src.core.database_manager import DatabaseManager
from src.tools.tooltip_utils import create_treeview_tooltip


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
        
        # 数据缓存（用于tooltip性能优化）
        self._base_facts_cache = None
        self._entities_cache = {}
        self._emotions_cache = None

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
        ttk.Button(toolbar, text="🗑清空数据", command=self.clear_confirm, width=10).pack(side=tk.LEFT, padx=2)

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

        # 标签页4：长期记忆（已由MemU系统接管，移除此tab）
        # self.create_long_term_tab()

        # 标签页5：情感分析历史
        self.create_emotion_tab()

        # 标签页6：环境管理
        self.create_environments_tab()

        # 标签页7：域管理
        self.create_domains_tab()
        
        # 标签页8：日程管理
        self.create_schedules_tab()
        
        # 标签页8：日程管理
        self.create_schedules_tab()

    def create_base_knowledge_tab(self):
        """
        创建基础知识管理标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔒 基础知识")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕添加", command=self.add_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        #ttk.Button(toolbar, text="✏编辑", command=self.edit_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑删除", command=self.delete_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_base_knowledge, width=8).pack(side=tk.LEFT, padx=2)

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

        # 配置列 - 优化列宽
        self.base_tree.heading("entity", text="实体名称")
        self.base_tree.heading("content", text="内容")
        self.base_tree.heading("category", text="分类")
        self.base_tree.heading("confidence", text="置信度")
        self.base_tree.heading("created", text="创建时间")

        self.base_tree.column("entity", width=150, minwidth=100, stretch=False)
        self.base_tree.column("content", width=400, minwidth=200, stretch=True)
        self.base_tree.column("category", width=100, minwidth=80, stretch=False)
        self.base_tree.column("confidence", width=80, minwidth=70, stretch=False)
        self.base_tree.column("created", width=160, minwidth=140, stretch=False)

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
        
        # 添加鼠标悬停提示
        def get_base_tooltip(item_id, values, tags):
            """获取基础知识的工具提示文本"""
            if not tags:
                return None
            
            fact_id = tags[0]
            # 使用缓存的数据，避免每次悬停都查询数据库
            if self._base_facts_cache is None:
                self._base_facts_cache = self.db.get_all_base_facts()
            
            fact = next((f for f in self._base_facts_cache if f['id'] == fact_id), None)
            
            if fact:
                tooltip_text = f"实体名称: {fact['entity_name']}\n"
                tooltip_text += f"分类: {fact['category']}\n"
                tooltip_text += f"置信度: {fact['confidence']:.2f}\n"
                tooltip_text += f"创建时间: {fact['created_at'][:19] if fact.get('created_at') else 'N/A'}\n"
                tooltip_text += f"\n完整内容:\n{fact['content']}"
                return tooltip_text
            return None
        
        create_treeview_tooltip(self.base_tree, get_base_tooltip)

    def create_entities_tab(self):
        """
        创建实体管理标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📦 实体管理")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕新建实体", command=self.add_entity, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="👁查看详情", command=self.view_entity_detail, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑删除", command=self.delete_entity, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_entities, width=8).pack(side=tk.LEFT, padx=2)

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

        self.entity_tree.column("name", width=250, minwidth=150, stretch=True)
        self.entity_tree.column("has_def", width=80, minwidth=60, stretch=False)
        self.entity_tree.column("info_count", width=110, minwidth=90, stretch=False)
        self.entity_tree.column("created", width=160, minwidth=140, stretch=False)
        self.entity_tree.column("updated", width=160, minwidth=140, stretch=False)

        scrollbar_y.config(command=self.entity_tree.yview)
        scrollbar_x.config(command=self.entity_tree.xview)

        self.entity_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击查看详情
        self.entity_tree.bind("<Double-1>", lambda e: self.view_entity_detail())
        
        # 添加鼠标悬停提示
        def get_entity_tooltip(item_id, values, tags):
            """获取实体的工具提示文本"""
            if not tags:
                return None
            
            entity_uuid = tags[0]
            # 使用缓存避免重复查询
            if entity_uuid not in self._entities_cache:
                entity = self.db.get_entity_by_uuid(entity_uuid)
                definition = self.db.get_entity_definition(entity_uuid)
                self._entities_cache[entity_uuid] = (entity, definition)
            else:
                entity, definition = self._entities_cache[entity_uuid]
            
            if entity:
                tooltip_text = f"实体名称: {entity['name']}\n"
                tooltip_text += f"UUID: {entity['uuid']}\n"
                tooltip_text += f"创建时间: {entity['created_at'][:19]}\n"
                tooltip_text += f"更新时间: {entity['updated_at'][:19]}\n"
                
                if definition:
                    tooltip_text += f"\n定义:\n{definition['content'][:200]}{'...' if len(definition['content']) > 200 else ''}"
                
                return tooltip_text
            return None
        
        create_treeview_tooltip(self.entity_tree, get_entity_tooltip)

    def create_short_term_tab(self):
        """
        创建短期记忆标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="💭 短期记忆")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🗑清空全部", command=self.clear_short_term, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_short_term, width=8).pack(side=tk.LEFT, padx=2)

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

        ttk.Button(toolbar, text="🗑清空全部", command=self.clear_long_term, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_long_term, width=8).pack(side=tk.LEFT, padx=2)

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

        ttk.Button(toolbar, text="👁查看详情", command=self.view_emotion_detail, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_emotion, width=8).pack(side=tk.LEFT, padx=2)

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

        self.emotion_tree.column("relationship", width=180, minwidth=120, stretch=True)
        self.emotion_tree.column("tone", width=180, minwidth=120, stretch=True)
        self.emotion_tree.column("score", width=100, minwidth=80, stretch=False)
        self.emotion_tree.column("created", width=180, minwidth=150, stretch=False)

        scrollbar_y.config(command=self.emotion_tree.yview)

        self.emotion_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击查看详情
        self.emotion_tree.bind("<Double-1>", lambda e: self.view_emotion_detail())
        
        # 添加鼠标悬停提示
        def get_emotion_tooltip(item_id, values, tags):
            """获取情感分析的工具提示文本"""
            if not tags:
                return None
            
            emotion_uuid = tags[0]
            # 使用缓存的情感历史数据
            if self._emotions_cache is None:
                self._emotions_cache = self.db.get_emotion_history()
            
            emotion = next((e for e in self._emotions_cache if e['uuid'] == emotion_uuid), None)
            
            if emotion:
                tooltip_text = f"关系类型: {emotion.get('relationship_type', '未知')}\n"
                tooltip_text += f"情感基调: {emotion.get('emotional_tone', '未知')}\n"
                tooltip_text += f"总评分: {emotion.get('overall_score', 0)}/100\n"
                tooltip_text += f"分析时间: {emotion['created_at'][:19]}\n"
                tooltip_text += f"\n五维度评分:\n"
                tooltip_text += f"• 亲密度: {emotion.get('intimacy', 0)}/100\n"
                tooltip_text += f"• 信任度: {emotion.get('trust', 0)}/100\n"
                tooltip_text += f"• 愉悦度: {emotion.get('pleasure', 0)}/100\n"
                tooltip_text += f"• 共鸣度: {emotion.get('resonance', 0)}/100\n"
                tooltip_text += f"• 依赖度: {emotion.get('dependence', 0)}/100"
                return tooltip_text
            return None
        
        create_treeview_tooltip(self.emotion_tree, get_emotion_tooltip)

    def create_environments_tab(self):
        """
        创建环境管理标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🗺️ 环境管理")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕添加环境", command=self.add_environment, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏编辑", command=self.edit_environment, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑删除", command=self.delete_environment, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✅激活", command=self.activate_environment, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_environments, width=8).pack(side=tk.LEFT, padx=2)

        self.env_count_label = ttk.Label(toolbar, text="环境数: 0", font=("微软雅黑", 9))
        self.env_count_label.pack(side=tk.RIGHT, padx=10)

        # 创建Treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self.env_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "description", "active", "created"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.env_tree.heading("name", text="环境名称")
        self.env_tree.heading("description", text="描述")
        self.env_tree.heading("active", text="状态")
        self.env_tree.heading("created", text="创建时间")

        self.env_tree.column("name", width=150, minwidth=100, stretch=False)
        self.env_tree.column("description", width=350, minwidth=200, stretch=True)
        self.env_tree.column("active", width=80, minwidth=60, stretch=False)
        self.env_tree.column("created", width=160, minwidth=140, stretch=False)

        scrollbar_y.config(command=self.env_tree.yview)
        scrollbar_x.config(command=self.env_tree.xview)

        self.env_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击编辑
        self.env_tree.bind("<Double-1>", lambda e: self.edit_environment())

        # 添加鼠标悬停提示
        def get_env_tooltip(item_id, values, tags):
            """获取环境的工具提示文本"""
            if not tags:
                return None
            
            env_uuid = tags[0]
            env = self.db.get_environment(env_uuid)
            
            if env:
                tooltip_text = f"环境: {env['name']}\n"
                tooltip_text += f"描述: {env['overall_description'][:100]}...\n" if len(env.get('overall_description', '')) > 100 else f"描述: {env.get('overall_description', '')}\n"
                if env.get('atmosphere'):
                    tooltip_text += f"氛围: {env['atmosphere']}\n"
                if env.get('lighting'):
                    tooltip_text += f"光照: {env['lighting']}\n"
                tooltip_text += f"状态: {'激活' if env.get('is_active') else '未激活'}\n"
                tooltip_text += f"创建时间: {env['created_at'][:19]}"
                return tooltip_text
            return None
        
        create_treeview_tooltip(self.env_tree, get_env_tooltip)

    def create_domains_tab(self):
        """
        创建域管理标签页
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🏘️ 域管理")

        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="➕创建域", command=self.add_domain, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✏编辑", command=self.edit_domain, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑删除", command=self.delete_domain, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📍管理环境", command=self.manage_domain_environments, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄刷新", command=self.refresh_domains, width=8).pack(side=tk.LEFT, padx=2)

        self.domain_count_label = ttk.Label(toolbar, text="域数: 0", font=("微软雅黑", 9))
        self.domain_count_label.pack(side=tk.RIGHT, padx=10)

        # 创建Treeview
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        self.domain_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "description", "default_env", "env_count", "created"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.domain_tree.heading("name", text="域名称")
        self.domain_tree.heading("description", text="描述")
        self.domain_tree.heading("default_env", text="默认环境")
        self.domain_tree.heading("env_count", text="环境数")
        self.domain_tree.heading("created", text="创建时间")

        self.domain_tree.column("name", width=120, minwidth=100, stretch=False)
        self.domain_tree.column("description", width=300, minwidth=200, stretch=True)
        self.domain_tree.column("default_env", width=120, minwidth=100, stretch=False)
        self.domain_tree.column("env_count", width=80, minwidth=60, stretch=False)
        self.domain_tree.column("created", width=160, minwidth=140, stretch=False)

        scrollbar_y.config(command=self.domain_tree.yview)
        scrollbar_x.config(command=self.domain_tree.xview)

        self.domain_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # 双击编辑
        self.domain_tree.bind("<Double-1>", lambda e: self.edit_domain())

        # 添加鼠标悬停提示
        def get_domain_tooltip(item_id, values, tags):
            """获取域的工具提示文本"""
            if not tags:
                return None
            
            domain_uuid = tags[0]
            domain = self.db.get_domain(domain_uuid)
            
            if domain:
                tooltip_text = f"域: {domain['name']}\n"
                tooltip_text += f"描述: {domain.get('description', '')}\n"
                
                # 获取域中的环境
                envs = self.db.get_domain_environments(domain_uuid)
                if envs:
                    tooltip_text += f"包含环境: {', '.join([e['name'] for e in envs])}\n"
                
                # 显示默认环境
                if domain.get('default_environment_uuid'):
                    default_env = self.db.get_environment(domain['default_environment_uuid'])
                    if default_env:
                        tooltip_text += f"默认环境: {default_env['name']}\n"
                
                tooltip_text += f"创建时间: {domain['created_at'][:19]}"
                return tooltip_text
            return None
        
        create_treeview_tooltip(self.domain_tree, get_domain_tooltip)

    # ==================== 刷新方法 ====================

    def refresh_all(self):
        """刷新所有标签页数据"""
        # 显示刷新中状态
        self.refresh_indicator.config(text="🔄")

        try:
            self.refresh_base_knowledge()
            self.refresh_entities()
            self.refresh_short_term()
            # self.refresh_long_term()  # 已废弃，由MemU系统接管
            self.refresh_emotion()
            self.refresh_environments()
            self.refresh_domains()
            
            # 刷新日程（如果方法存在）
            if hasattr(self, 'refresh_schedules'):
                self.refresh_schedules()
            
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
        # 清空缓存
        self._base_facts_cache = None
        
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

        # 获取所有基础知识并更新缓存
        base_facts = self.db.get_all_base_facts()
        self._base_facts_cache = base_facts

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
        # 清空缓存
        self._entities_cache = {}
        
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
            
            # 预填充缓存以提高tooltip性能
            self._entities_cache[entity['uuid']] = (entity, definition)

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

#     def refresh_long_term(self):
#         """刷新长期记忆显示"""
#         self.long_term_text.config(state=tk.NORMAL)
#         self.long_term_text.delete(1.0, tk.END)
# 
#         summaries = self.db.get_long_term_summaries()
#         self.long_term_count_label.config(text=f"概括数: {len(summaries)}")
# 
#         for i, summary in enumerate(summaries, 1):
#             self.long_term_text.insert(tk.END, f"━━━━━ 主题 {i} ━━━━━\n", "header")
#             self.long_term_text.insert(tk.END, f"时间: {summary['created_at'][:19]} - {summary['ended_at'][:19]}\n")
#             self.long_term_text.insert(tk.END, f"轮数: {summary.get('rounds', 0)} 轮 | 消息: {summary.get('message_count', 0)} 条\n")
#             self.long_term_text.insert(tk.END, f"\n{summary['summary']}\n\n\n")
# 
#         self.long_term_text.config(state=tk.DISABLED)
# 
    def refresh_emotion(self):
        """刷新情感分析历史"""
        # 清空缓存
        self._emotions_cache = None
        
        # 清空现有项
        for item in self.emotion_tree.get_children():
            self.emotion_tree.delete(item)

        # 获取情感分析历史并更新缓存
        emotions = self.db.get_emotion_history()
        self._emotions_cache = emotions
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

#     def clear_long_term(self):
#         """清空长期记忆"""
#         if messagebox.askyesno("确认", "确定要清空所有长期记忆吗？"):
#             if self.db.clear_long_term_memory():
#                 self.refresh_long_term()
#                 self.update_statistics()
#                 messagebox.showinfo("成功", "长期记忆已清空")
# 
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
    
    # ==================== 环境管理方法 ====================

    def refresh_environments(self):
        """刷新环境列表"""
        # 清空现有项
        for item in self.env_tree.get_children():
            self.env_tree.delete(item)

        # 获取所有环境
        environments = self.db.get_all_environments()
        
        # 更新计数
        self.env_count_label.config(text=f"环境数: {len(environments)}")

        # 添加到树视图
        for env in environments:
            status = "✅激活" if env.get('is_active') else "⭕未激活"
            self.env_tree.insert("", tk.END, values=(
                env['name'],
                env.get('overall_description', '')[:50] + "..." if len(env.get('overall_description', '')) > 50 else env.get('overall_description', ''),
                status,
                env['created_at'][:19]
            ), tags=(env['uuid'],))

    def add_environment(self):
        """添加新环境"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("添加环境")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="环境名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(dialog, width=50)
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="整体描述:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        desc_text = tk.Text(dialog, width=50, height=5, wrap=tk.WORD)
        desc_text.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="氛围:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        atmosphere_entry = ttk.Entry(dialog, width=50)
        atmosphere_entry.grid(row=2, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="光照:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        lighting_entry = ttk.Entry(dialog, width=50)
        lighting_entry.grid(row=3, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="声音:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        sounds_entry = ttk.Entry(dialog, width=50)
        sounds_entry.grid(row=4, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="气味:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        smells_entry = ttk.Entry(dialog, width=50)
        smells_entry.grid(row=5, column=1, padx=10, pady=10)

        def save():
            name = name_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()
            atmosphere = atmosphere_entry.get().strip()
            lighting = lighting_entry.get().strip()
            sounds = sounds_entry.get().strip()
            smells = smells_entry.get().strip()

            if not name or not description:
                messagebox.showwarning("警告", "环境名称和描述不能为空！")
                return

            try:
                env_uuid = self.db.create_environment(
                    name=name,
                    overall_description=description,
                    atmosphere=atmosphere,
                    lighting=lighting,
                    sounds=sounds,
                    smells=smells
                )
                messagebox.showinfo("成功", f"已创建环境: {name}")
                self.refresh_environments()
                self.update_statistics()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"创建失败: {str(e)}")

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def edit_environment(self):
        """编辑选中的环境"""
        selected = self.env_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个环境！")
            return

        env_uuid = self.env_tree.item(selected[0])['tags'][0]
        env = self.db.get_environment(env_uuid)
        
        if not env:
            messagebox.showerror("错误", "环境不存在！")
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title(f"编辑环境: {env['name']}")
        dialog.geometry("600x500")

        ttk.Label(dialog, text="环境名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(dialog, width=50)
        name_entry.insert(0, env['name'])
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="整体描述:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        desc_text = tk.Text(dialog, width=50, height=5, wrap=tk.WORD)
        desc_text.insert(1.0, env.get('overall_description', ''))
        desc_text.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="氛围:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        atmosphere_entry = ttk.Entry(dialog, width=50)
        atmosphere_entry.insert(0, env.get('atmosphere', ''))
        atmosphere_entry.grid(row=2, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="光照:").grid(row=3, column=0, padx=10, pady=10, sticky="w")
        lighting_entry = ttk.Entry(dialog, width=50)
        lighting_entry.insert(0, env.get('lighting', ''))
        lighting_entry.grid(row=3, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="声音:").grid(row=4, column=0, padx=10, pady=10, sticky="w")
        sounds_entry = ttk.Entry(dialog, width=50)
        sounds_entry.insert(0, env.get('sounds', ''))
        sounds_entry.grid(row=4, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="气味:").grid(row=5, column=0, padx=10, pady=10, sticky="w")
        smells_entry = ttk.Entry(dialog, width=50)
        smells_entry.insert(0, env.get('smells', ''))
        smells_entry.grid(row=5, column=1, padx=10, pady=10)

        def save():
            name = name_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()
            atmosphere = atmosphere_entry.get().strip()
            lighting = lighting_entry.get().strip()
            sounds = sounds_entry.get().strip()
            smells = smells_entry.get().strip()

            if not name or not description:
                messagebox.showwarning("警告", "环境名称和描述不能为空！")
                return

            try:
                self.db.update_environment(
                    env_uuid,
                    name=name,
                    overall_description=description,
                    atmosphere=atmosphere,
                    lighting=lighting,
                    sounds=sounds,
                    smells=smells
                )
                messagebox.showinfo("成功", f"已更新环境: {name}")
                self.refresh_environments()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"更新失败: {str(e)}")

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def delete_environment(self):
        """删除选中的环境"""
        selected = self.env_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个环境！")
            return

        env_uuid = self.env_tree.item(selected[0])['tags'][0]
        env = self.db.get_environment(env_uuid)
        
        if not env:
            return

        if messagebox.askyesno("确认", f"确定要删除环境 '{env['name']}' 吗？"):
            if self.db.delete_environment(env_uuid):
                messagebox.showinfo("成功", "环境已删除")
                self.refresh_environments()
                self.update_statistics()
            else:
                messagebox.showerror("错误", "删除失败！")

    def activate_environment(self):
        """激活选中的环境"""
        selected = self.env_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个环境！")
            return

        env_uuid = self.env_tree.item(selected[0])['tags'][0]
        env = self.db.get_environment(env_uuid)
        
        if not env:
            return

        if self.db.set_active_environment(env_uuid):
            messagebox.showinfo("成功", f"已激活环境: {env['name']}")
            self.refresh_environments()
        else:
            messagebox.showerror("错误", "激活失败！")

    # ==================== 域管理方法 ====================

    def refresh_domains(self):
        """刷新域列表"""
        # 清空现有项
        for item in self.domain_tree.get_children():
            self.domain_tree.delete(item)

        # 获取所有域
        domains = self.db.get_all_domains()
        
        # 更新计数
        self.domain_count_label.config(text=f"域数: {len(domains)}")

        # 添加到树视图
        for domain in domains:
            # 获取默认环境名称
            default_env_name = ""
            if domain.get('default_environment_uuid'):
                default_env = self.db.get_environment(domain['default_environment_uuid'])
                if default_env:
                    default_env_name = default_env['name']
            
            # 获取域中的环境数量
            envs = self.db.get_domain_environments(domain['uuid'])
            env_count = len(envs)
            
            self.domain_tree.insert("", tk.END, values=(
                domain['name'],
                domain.get('description', '')[:50] + "..." if len(domain.get('description', '')) > 50 else domain.get('description', ''),
                default_env_name,
                env_count,
                domain['created_at'][:19]
            ), tags=(domain['uuid'],))

    def add_domain(self):
        """添加新域"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("创建域")
        dialog.geometry("500x300")

        ttk.Label(dialog, text="域名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="描述:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        desc_text = tk.Text(dialog, width=40, height=6, wrap=tk.WORD)
        desc_text.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="默认环境:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        # 获取所有环境
        all_envs = self.db.get_all_environments()
        env_names = ["(不设置)"] + [env['name'] for env in all_envs]
        env_combo = ttk.Combobox(dialog, width=38, values=env_names, state="readonly")
        env_combo.set("(不设置)")
        env_combo.grid(row=2, column=1, padx=10, pady=10)

        def save():
            name = name_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()
            default_env_name = env_combo.get()

            if not name:
                messagebox.showwarning("警告", "域名称不能为空！")
                return

            # 获取默认环境UUID
            default_env_uuid = None
            if default_env_name != "(不设置)":
                for env in all_envs:
                    if env['name'] == default_env_name:
                        default_env_uuid = env['uuid']
                        break

            try:
                domain_uuid = self.db.create_domain(
                    name=name,
                    description=description,
                    default_environment_uuid=default_env_uuid
                )
                messagebox.showinfo("成功", f"已创建域: {name}")
                self.refresh_domains()
                self.update_statistics()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"创建失败: {str(e)}")

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def edit_domain(self):
        """编辑选中的域"""
        selected = self.domain_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个域！")
            return

        domain_uuid = self.domain_tree.item(selected[0])['tags'][0]
        domain = self.db.get_domain(domain_uuid)
        
        if not domain:
            messagebox.showerror("错误", "域不存在！")
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title(f"编辑域: {domain['name']}")
        dialog.geometry("500x300")

        ttk.Label(dialog, text="域名称:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.insert(0, domain['name'])
        name_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="描述:").grid(row=1, column=0, padx=10, pady=10, sticky="nw")
        desc_text = tk.Text(dialog, width=40, height=6, wrap=tk.WORD)
        desc_text.insert(1.0, domain.get('description', ''))
        desc_text.grid(row=1, column=1, padx=10, pady=10)

        ttk.Label(dialog, text="默认环境:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        # 获取所有环境
        all_envs = self.db.get_all_environments()
        env_names = ["(不设置)"] + [env['name'] for env in all_envs]
        env_combo = ttk.Combobox(dialog, width=38, values=env_names, state="readonly")
        
        # 设置当前默认环境
        if domain.get('default_environment_uuid'):
            default_env = self.db.get_environment(domain['default_environment_uuid'])
            if default_env:
                env_combo.set(default_env['name'])
            else:
                env_combo.set("(不设置)")
        else:
            env_combo.set("(不设置)")
        
        env_combo.grid(row=2, column=1, padx=10, pady=10)

        def save():
            name = name_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()
            default_env_name = env_combo.get()

            if not name:
                messagebox.showwarning("警告", "域名称不能为空！")
                return

            # 获取默认环境UUID
            default_env_uuid = None
            if default_env_name != "(不设置)":
                for env in all_envs:
                    if env['name'] == default_env_name:
                        default_env_uuid = env['uuid']
                        break

            try:
                self.db.update_domain(
                    domain_uuid,
                    name=name,
                    description=description,
                    default_environment_uuid=default_env_uuid
                )
                messagebox.showinfo("成功", f"已更新域: {name}")
                self.refresh_domains()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("错误", f"更新失败: {str(e)}")

        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="保存", command=save, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=15).pack(side=tk.LEFT, padx=5)

    def delete_domain(self):
        """删除选中的域"""
        selected = self.domain_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个域！")
            return

        domain_uuid = self.domain_tree.item(selected[0])['tags'][0]
        domain = self.db.get_domain(domain_uuid)
        
        if not domain:
            return

        if messagebox.askyesno("确认", f"确定要删除域 '{domain['name']}' 吗？\n这将移除域与环境的关联，但不会删除环境本身。"):
            if self.db.delete_domain(domain_uuid):
                messagebox.showinfo("成功", "域已删除")
                self.refresh_domains()
                self.update_statistics()
            else:
                messagebox.showerror("错误", "删除失败！")

    def manage_domain_environments(self):
        """管理域中的环境"""
        selected = self.domain_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择一个域！")
            return

    def create_schedules_tab(self):
        """
        创建日程数据管理标签页（简化版，仅用于数据查看和编辑）
        """
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📅 日程数据")
        
        # 说明文本
        info_frame = ttk.Frame(tab)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text="💡 提示：完整的日程管理功能请使用主界面的「📅 日程管理」标签页\n这里仅提供基础的数据查看和编辑功能",
            font=("微软雅黑", 9),
            foreground="#666",
            justify=tk.LEFT
        )
        info_label.pack(side=tk.LEFT, padx=5)
        
        # 工具栏
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_schedules, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📝 编辑数据", command=self.edit_schedule_data, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🗑 删除", command=self.delete_schedule_data, width=8).pack(side=tk.LEFT, padx=2)
        
        # 创建Treeview显示列表
        tree_frame = ttk.Frame(tab)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        self.schedules_tree = ttk.Treeview(
            tree_frame,
            columns=("id", "title", "type", "start_time", "end_time", "priority", "status"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        
        # 配置列
        self.schedules_tree.heading("id", text="ID")
        self.schedules_tree.heading("title", text="标题")
        self.schedules_tree.heading("type", text="类型")
        self.schedules_tree.heading("start_time", text="开始时间")
        self.schedules_tree.heading("end_time", text="结束时间")
        self.schedules_tree.heading("priority", text="优先级")
        self.schedules_tree.heading("status", text="状态")
        
        self.schedules_tree.column("id", width=80, minwidth=60, stretch=False)
        self.schedules_tree.column("title", width=150, minwidth=100, stretch=True)
        self.schedules_tree.column("type", width=80, minwidth=70, stretch=False)
        self.schedules_tree.column("start_time", width=150, minwidth=120, stretch=False)
        self.schedules_tree.column("end_time", width=150, minwidth=120, stretch=False)
        self.schedules_tree.column("priority", width=70, minwidth=60, stretch=False)
        self.schedules_tree.column("status", width=80, minwidth=70, stretch=False)
        
        scrollbar_y.config(command=self.schedules_tree.yview)
        scrollbar_x.config(command=self.schedules_tree.xview)
        
        # 布局
        self.schedules_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # 双击编辑
        self.schedules_tree.bind("<Double-1>", lambda e: self.edit_schedule_data())
        
        # 统计信息
        stats_frame = ttk.Frame(tab)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.schedule_stats_label = ttk.Label(stats_frame, text="", font=("微软雅黑", 9))
        self.schedule_stats_label.pack(side=tk.LEFT, padx=5)
        
        # 首次刷新
        self.refresh_schedules()
    
    def refresh_schedules(self):
        """刷新日程数据列表"""
        # 清空现有内容
        for item in self.schedules_tree.get_children():
            self.schedules_tree.delete(item)
        
        try:
            # 直接从数据库读取
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 首先检查表是否存在
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='schedules'
                """)
                
                if not cursor.fetchone():
                    # 表不存在，静默跳过（首次启动时会出现这种情况）
                    self.schedule_stats_label.config(text="日程表尚未初始化（首次使用日程功能时会自动创建）")
                    return
                
                cursor.execute("""
                    SELECT schedule_id, title, schedule_type, start_time, end_time, 
                           priority, is_active, collaboration_status
                    FROM schedules
                    ORDER BY start_time DESC
                    LIMIT 500
                """)
                
                schedules = cursor.fetchall()
                
                # 类型映射
                type_map = {'recurring': '周期', 'appointment': '预约', 'temporary': '临时'}
                priority_map = {1: '低', 2: '中', 3: '高', 4: '关键'}
                
                for schedule in schedules:
                    schedule_id = schedule[0][:8]  # 显示前8位
                    title = schedule[1]
                    stype = type_map.get(schedule[2], schedule[2])
                    start_time = schedule[3][:16] if schedule[3] else ""
                    end_time = schedule[4][:16] if schedule[4] else ""
                    priority = priority_map.get(schedule[5], str(schedule[5]))
                    status = "激活" if schedule[6] else "已删除"
                    
                    # 添加到树
                    self.schedules_tree.insert(
                        "",
                        tk.END,
                        values=(schedule_id, title, stype, start_time, end_time, priority, status),
                        tags=(schedule[0],)  # 完整ID作为tag
                    )
                
                # 更新统计
                self.schedule_stats_label.config(text=f"共 {len(schedules)} 条日程记录")
            
        except Exception as e:
            # 如果是"no such table"错误，静默处理
            error_msg = str(e).lower()
            if "no such table" in error_msg or "schedules" in error_msg:
                self.schedule_stats_label.config(text="日程表尚未初始化")
            else:
                messagebox.showerror("错误", f"刷新日程数据失败:\n{str(e)}")
    
    def edit_schedule_data(self):
        """编辑日程数据"""
        selection = self.schedules_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要编辑的日程")
            return
        
        item = selection[0]
        schedule_id = self.schedules_tree.item(item)['tags'][0]
        
        try:
            # 从数据库读取完整数据
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,))
                schedule = cursor.fetchone()
                
                if not schedule:
                    messagebox.showerror("错误", "日程不存在")
                    return
            
            # 创建编辑对话框
            dialog = tk.Toplevel(self.parent)
            dialog.title("编辑日程数据")
            dialog.geometry("500x400")
            dialog.transient(self.parent)
            dialog.grab_set()
            
            form_frame = ttk.Frame(dialog, padding=10)
            form_frame.pack(fill=tk.BOTH, expand=True)
            
            # 显示可编辑字段
            fields = []
            
            # 标题
            ttk.Label(form_frame, text="标题:").grid(row=0, column=0, sticky=tk.W, pady=2)
            title_entry = ttk.Entry(form_frame, width=40)
            title_entry.insert(0, schedule[1] or "")
            title_entry.grid(row=0, column=1, pady=2)
            fields.append(('title', title_entry))
            
            # 描述
            ttk.Label(form_frame, text="描述:").grid(row=1, column=0, sticky=tk.W, pady=2)
            desc_text = tk.Text(form_frame, width=40, height=3)
            desc_text.insert("1.0", schedule[2] or "")
            desc_text.grid(row=1, column=1, pady=2)
            fields.append(('description', desc_text))
            
            # 优先级
            ttk.Label(form_frame, text="优先级 (1-4):").grid(row=2, column=0, sticky=tk.W, pady=2)
            priority_entry = ttk.Entry(form_frame, width=40)
            priority_entry.insert(0, str(schedule[6]))
            priority_entry.grid(row=2, column=1, pady=2)
            fields.append(('priority', priority_entry))
            
            # 激活状态
            ttk.Label(form_frame, text="激活状态:").grid(row=3, column=0, sticky=tk.W, pady=2)
            active_var = tk.BooleanVar(value=bool(schedule[10]))
            ttk.Checkbutton(form_frame, variable=active_var).grid(row=3, column=1, sticky=tk.W, pady=2)
            
            # 按钮
            button_frame = ttk.Frame(dialog)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def save_changes():
                try:
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        
                        title = title_entry.get()
                        description = desc_text.get("1.0", tk.END).strip()
                        priority = int(priority_entry.get())
                        is_active = 1 if active_var.get() else 0
                        
                        cursor.execute("""
                            UPDATE schedules
                            SET title = ?, description = ?, priority = ?, is_active = ?
                            WHERE schedule_id = ?
                        """, (title, description, priority, is_active, schedule_id))
                        
                        conn.commit()
                        messagebox.showinfo("成功", "日程数据已更新")
                        dialog.destroy()
                        self.refresh_schedules()
                    
                except Exception as e:
                    messagebox.showerror("错误", f"更新失败:\n{str(e)}")
            
            ttk.Button(button_frame, text="保存", command=save_changes, width=10).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"加载日程数据失败:\n{str(e)}")
    
    def delete_schedule_data(self):
        """删除日程数据（软删除）"""
        selection = self.schedules_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的日程")
            return
        
        item = selection[0]
        values = self.schedules_tree.item(item)['values']
        schedule_id = self.schedules_tree.item(item)['tags'][0]
        
        if not messagebox.askyesno("确认", f"确定要删除日程「{values[1]}」吗？\n\n这是软删除，数据仍保留在数据库中。"):
            return
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE schedules SET is_active = 0 WHERE schedule_id = ?", (schedule_id,))
                conn.commit()
            
            messagebox.showinfo("成功", "日程已标记为删除")
            self.refresh_schedules()
            
        except Exception as e:
            messagebox.showerror("错误", f"删除失败:\n{str(e)}")
