"""
Cognee 智能记忆系统 GUI
提供 Cognee 记忆管理和世界观构建的可视化界面

功能：
1. Cognee 记忆管理 - 添加、搜索、查看记忆
2. 世界观构建 - 创建、编辑、管理 Markdown 世界观文件
3. 知识图谱可视化 - 展示记忆关联
"""

import asyncio
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
from datetime import datetime
from typing import Dict, Any, List

from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class CogneeMemoryGUI:
    """
    Cognee 智能记忆管理 GUI
    提供记忆的添加、搜索、查看功能
    """
    
    def __init__(self, parent_frame, cognee_manager=None):
        """
        初始化 Cognee 记忆管理 GUI
        
        Args:
            parent_frame: 父容器
            cognee_manager: Cognee 记忆管理器实例
        """
        self.parent = parent_frame
        self.cognee_manager = cognee_manager
        
        # 搜索结果缓存
        self._search_results_cache = []
        
        # 创建界面
        self.create_widgets()
        
        debug_logger.log_info('CogneeMemoryGUI', 'Cognee 记忆管理 GUI 已初始化')
    
    def create_widgets(self):
        """创建所有 GUI 组件"""
        # 顶部标题栏
        header = ttk.Frame(self.parent)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            header, 
            text="🧠 Cognee 智能记忆系统", 
            font=("微软雅黑", 12, "bold")
        ).pack(side=tk.LEFT, padx=5)
        
        # 状态指示器
        self.status_label = ttk.Label(
            header, 
            text="", 
            font=("微软雅黑", 9)
        )
        self.status_label.pack(side=tk.RIGHT, padx=5)
        self._update_status()
        
        # 分割线
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=2)
        
        # 创建标签页
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标签页1: 添加记忆
        self._create_add_memory_tab()
        
        # 标签页2: 搜索记忆
        self._create_search_tab()
        
        # 标签页3: 记忆统计
        self._create_stats_tab()
    
    def _update_status(self):
        """更新状态指示器"""
        if self.cognee_manager and self.cognee_manager._initialized:
            self.status_label.config(text="🟢 Cognee 已连接", foreground="green")
        else:
            self.status_label.config(text="🔴 Cognee 未连接", foreground="red")
    
    def _create_add_memory_tab(self):
        """创建添加记忆标签页"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="➕ 添加记忆")
        
        # 记忆类型选择
        type_frame = ttk.Frame(tab)
        type_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(type_frame, text="记忆类型:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
        
        self.memory_type_var = tk.StringVar(value="conversation")
        memory_types = [
            ("对话记忆", "conversation"),
            ("知识记忆", "knowledge"),
            ("世界观", "worldview")
        ]
        
        for text, value in memory_types:
            ttk.Radiobutton(
                type_frame, 
                text=text, 
                value=value, 
                variable=self.memory_type_var
            ).pack(side=tk.LEFT, padx=10)
        
        # 内容输入
        content_frame = ttk.LabelFrame(tab, text="记忆内容", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.memory_content_text = scrolledtext.ScrolledText(
            content_frame, 
            height=15, 
            font=("微软雅黑", 10),
            wrap=tk.WORD
        )
        self.memory_content_text.pack(fill=tk.BOTH, expand=True)
        
        # 元数据输入
        meta_frame = ttk.LabelFrame(tab, text="元数据（可选）", padding=10)
        meta_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(meta_frame, text="实体/主题:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entity_entry = ttk.Entry(meta_frame, width=30)
        self.entity_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(meta_frame, text="来源:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.source_entry = ttk.Entry(meta_frame, width=30)
        self.source_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="📝 添加记忆", 
            command=self._add_memory,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="📝 添加并构建图谱", 
            command=self._add_and_cognify,
            width=18
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="🔄 构建知识图谱", 
            command=self._cognify,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="🧹 清空", 
            command=self._clear_input,
            width=10
        ).pack(side=tk.RIGHT, padx=5)
    
    def _create_search_tab(self):
        """创建搜索记忆标签页"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔍 搜索记忆")
        
        # 搜索框
        search_frame = ttk.Frame(tab)
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(search_frame, text="搜索:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
        
        self.search_entry = ttk.Entry(search_frame, width=50, font=("微软雅黑", 10))
        self.search_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', lambda e: self._search_memory())
        
        ttk.Button(
            search_frame, 
            text="🔍 搜索", 
            command=self._search_memory,
            width=10
        ).pack(side=tk.LEFT, padx=5)
        
        # 搜索类型过滤
        filter_frame = ttk.Frame(tab)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(filter_frame, text="过滤类型:").pack(side=tk.LEFT, padx=5)
        
        self.search_type_var = tk.StringVar(value="all")
        search_types = [
            ("全部", "all"),
            ("对话", "conversation"),
            ("知识", "knowledge"),
            ("世界观", "worldview")
        ]
        
        for text, value in search_types:
            ttk.Radiobutton(
                filter_frame, 
                text=text, 
                value=value, 
                variable=self.search_type_var
            ).pack(side=tk.LEFT, padx=10)
        
        # 搜索结果
        result_frame = ttk.LabelFrame(tab, text="搜索结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建 Treeview
        columns = ("index", "content", "relevance")
        self.search_tree = ttk.Treeview(
            result_frame, 
            columns=columns, 
            show="headings",
            height=15
        )
        
        self.search_tree.heading("index", text="#")
        self.search_tree.heading("content", text="内容")
        self.search_tree.heading("relevance", text="相关度")
        
        self.search_tree.column("index", width=50, minwidth=40, stretch=False)
        self.search_tree.column("content", width=500, minwidth=300, stretch=True)
        self.search_tree.column("relevance", width=80, minwidth=60, stretch=False)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.search_tree.yview)
        self.search_tree.configure(yscrollcommand=scrollbar.set)
        
        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 双击查看详情
        self.search_tree.bind("<Double-1>", self._show_result_detail)
    
    def _create_stats_tab(self):
        """创建记忆统计标签页"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📊 统计信息")
        
        # 统计信息显示
        stats_frame = ttk.LabelFrame(tab, text="Cognee 记忆系统状态", padding=20)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(
            stats_frame,
            height=20,
            font=("Consolas", 10),
            wrap=tk.WORD
        )
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="🔄 刷新统计", 
            command=self._refresh_stats,
            width=15
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="🗑️ 清空所有记忆", 
            command=self._clear_all_memory,
            width=15
        ).pack(side=tk.RIGHT, padx=5)
        
        # 初始加载统计
        self._refresh_stats()
    
    def _run_async(self, coro):
        """运行异步协程"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    def _add_memory(self):
        """添加记忆"""
        if not self.cognee_manager or not self.cognee_manager._initialized:
            messagebox.showwarning("警告", "Cognee 未初始化，无法添加记忆")
            return
        
        content = self.memory_content_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("警告", "请输入记忆内容")
            return
        
        memory_type = self.memory_type_var.get()
        entity = self.entity_entry.get().strip()
        source = self.source_entry.get().strip()
        
        metadata = {}
        if entity:
            metadata["entity"] = entity
        if source:
            metadata["source"] = source
        
        try:
            success = self._run_async(
                self.cognee_manager.add_memory(content, memory_type, metadata)
            )
            
            if success:
                messagebox.showinfo("成功", "记忆已添加到 Cognee")
                self._clear_input()
            else:
                messagebox.showerror("错误", "添加记忆失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"添加记忆时出错: {str(e)}")
    
    def _add_and_cognify(self):
        """添加记忆并构建知识图谱"""
        if not self.cognee_manager or not self.cognee_manager._initialized:
            messagebox.showwarning("警告", "Cognee 未初始化")
            return
        
        content = self.memory_content_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("警告", "请输入记忆内容")
            return
        
        memory_type = self.memory_type_var.get()
        
        try:
            success = self._run_async(
                self.cognee_manager.process_and_store(content, memory_type)
            )
            
            if success:
                messagebox.showinfo("成功", "记忆已添加并构建知识图谱")
                self._clear_input()
            else:
                messagebox.showerror("错误", "处理失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"处理时出错: {str(e)}")
    
    def _cognify(self):
        """构建知识图谱"""
        if not self.cognee_manager or not self.cognee_manager._initialized:
            messagebox.showwarning("警告", "Cognee 未初始化")
            return
        
        try:
            success = self._run_async(self.cognee_manager.cognify())
            
            if success:
                messagebox.showinfo("成功", "知识图谱已构建")
            else:
                messagebox.showerror("错误", "构建知识图谱失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"构建知识图谱时出错: {str(e)}")
    
    def _search_memory(self):
        """搜索记忆"""
        if not self.cognee_manager or not self.cognee_manager._initialized:
            messagebox.showwarning("警告", "Cognee 未初始化")
            return
        
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("警告", "请输入搜索内容")
            return
        
        search_type = self.search_type_var.get()
        memory_type = None if search_type == "all" else search_type
        
        try:
            results = self._run_async(
                self.cognee_manager.search(query, memory_type=memory_type)
            )
            
            # 清空现有结果
            for item in self.search_tree.get_children():
                self.search_tree.delete(item)
            
            # 缓存结果
            self._search_results_cache = results
            
            # 添加结果
            for result in results:
                content = result.get("content", "")
                # 截断显示
                display_content = content[:100] + "..." if len(content) > 100 else content
                
                self.search_tree.insert("", "end", values=(
                    result.get("index", ""),
                    display_content,
                    f"{result.get('relevance', 0):.2f}"
                ))
            
            if not results:
                messagebox.showinfo("提示", "未找到相关记忆")
                
        except Exception as e:
            messagebox.showerror("错误", f"搜索时出错: {str(e)}")
    
    def _show_result_detail(self, event):
        """显示搜索结果详情"""
        selection = self.search_tree.selection()
        if not selection:
            return
        
        item = self.search_tree.item(selection[0])
        index = int(item["values"][0]) - 1
        
        if 0 <= index < len(self._search_results_cache):
            result = self._search_results_cache[index]
            content = result.get("content", "")
            
            # 显示详情对话框
            detail_window = tk.Toplevel(self.parent)
            detail_window.title("记忆详情")
            detail_window.geometry("600x400")
            
            text = scrolledtext.ScrolledText(
                detail_window,
                font=("微软雅黑", 10),
                wrap=tk.WORD
            )
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert("1.0", content)
            text.config(state=tk.DISABLED)
    
    def _refresh_stats(self):
        """刷新统计信息"""
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        
        if self.cognee_manager:
            stats = self.cognee_manager.get_statistics()
            
            stats_text = """╔══════════════════════════════════════════════════════╗
║            Cognee 智能记忆系统状态                    ║
╠══════════════════════════════════════════════════════╣
║                                                      ║
║  系统状态                                            ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
"""
            stats_text += f"║  • 启用状态: {'✓ 已启用' if stats.get('enabled') else '✗ 未启用':40}║\n"
            stats_text += f"║  • 初始化: {'✓ 已初始化' if stats.get('initialized') else '✗ 未初始化':42}║\n"
            stats_text += f"║  • API配置: {'✓ 已配置' if stats.get('api_key_configured') else '✗ 未配置':42}║\n"
            stats_text += f"║  • 后端: {stats.get('backend', 'N/A'):45}║\n"
            stats_text += """║                                                      ║
║  功能说明                                            ║
║  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
║  • 对话记忆: 存储和检索对话历史                      ║
║  • 知识记忆: 自动构建实体关系图谱                    ║
║  • 世界观: 虚拟世界设定和规则                        ║
║  • 语义搜索: 基于含义的智能检索                      ║
║                                                      ║
╚══════════════════════════════════════════════════════╝

Cognee 是一个开源的知识引擎，将原始数据转化为
智能体的持久动态记忆。它结合向量搜索和图数据库，
使文档既可以按语义搜索，又能通过关系相互关联。

官方文档: https://docs.cognee.ai/
"""
            self.stats_text.insert("1.0", stats_text)
        else:
            self.stats_text.insert("1.0", "Cognee 管理器未初始化")
        
        self.stats_text.config(state=tk.DISABLED)
    
    def _clear_input(self):
        """清空输入"""
        self.memory_content_text.delete("1.0", tk.END)
        self.entity_entry.delete(0, tk.END)
        self.source_entry.delete(0, tk.END)
    
    def _clear_all_memory(self):
        """清空所有记忆"""
        if not self.cognee_manager or not self.cognee_manager._initialized:
            messagebox.showwarning("警告", "Cognee 未初始化")
            return
        
        if messagebox.askyesno("确认", "确定要清空所有 Cognee 记忆吗？\n此操作不可恢复！"):
            try:
                success = self._run_async(self.cognee_manager.clear_all_memory())
                
                if success:
                    messagebox.showinfo("成功", "所有记忆已清空")
                    self._refresh_stats()
                else:
                    messagebox.showerror("错误", "清空记忆失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"清空记忆时出错: {str(e)}")


class WorldviewBuilderGUI:
    """
    世界观构建系统 GUI
    提供 Markdown 世界观的创建、编辑、管理功能
    """
    
    def __init__(self, parent_frame, worldview_builder=None):
        """
        初始化世界观构建 GUI
        
        Args:
            parent_frame: 父容器
            worldview_builder: 世界观构建器实例
        """
        self.parent = parent_frame
        self.worldview_builder = worldview_builder
        
        # 当前编辑的文件
        self.current_file = None
        self.is_modified = False
        
        # 创建界面
        self.create_widgets()
        
        # 加载世界观列表
        self._refresh_worldview_list()
        
        debug_logger.log_info('WorldviewBuilderGUI', '世界观构建 GUI 已初始化')
    
    def create_widgets(self):
        """创建所有 GUI 组件"""
        # 主分割面板
        self.paned = ttk.PanedWindow(self.parent, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 左侧：文件列表
        self._create_file_list_panel()
        
        # 右侧：编辑器
        self._create_editor_panel()
    
    def _create_file_list_panel(self):
        """创建文件列表面板"""
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        # 标题
        header = ttk.Frame(left_frame)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            header, 
            text="🌍 世界观文件", 
            font=("微软雅黑", 10, "bold")
        ).pack(side=tk.LEFT)
        
        # 工具栏
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            toolbar, 
            text="➕ 新建", 
            command=self._new_worldview,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar, 
            text="🗑️ 删除", 
            command=self._delete_worldview,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar, 
            text="🔄", 
            command=self._refresh_worldview_list,
            width=3
        ).pack(side=tk.LEFT, padx=2)
        
        # 文件列表
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.file_listbox = tk.Listbox(
            list_frame,
            font=("微软雅黑", 10),
            selectmode=tk.SINGLE
        )
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.file_listbox.bind('<<ListboxSelect>>', self._on_file_select)
        self.file_listbox.bind('<Double-1>', self._on_file_double_click)
        
        # 文件统计
        self.file_stats_label = ttk.Label(left_frame, text="", font=("微软雅黑", 9))
        self.file_stats_label.pack(fill=tk.X, padx=5, pady=5)
    
    def _create_editor_panel(self):
        """创建编辑器面板"""
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        # 标题栏
        header = ttk.Frame(right_frame)
        header.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_title_label = ttk.Label(
            header, 
            text="未选择文件", 
            font=("微软雅黑", 10, "bold")
        )
        self.file_title_label.pack(side=tk.LEFT)
        
        self.modified_label = ttk.Label(
            header, 
            text="", 
            font=("微软雅黑", 9),
            foreground="orange"
        )
        self.modified_label.pack(side=tk.LEFT, padx=10)
        
        # 工具栏
        toolbar = ttk.Frame(right_frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            toolbar, 
            text="💾 保存", 
            command=self._save_worldview,
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar, 
            text="🔄 重新加载", 
            command=self._reload_worldview,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(
            toolbar, 
            text="🤖 AI生成", 
            command=self._generate_with_ai,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar, 
            text="☁️ 同步到Cognee", 
            command=self._sync_to_cognee,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            toolbar, 
            text="📚 同步到知识库", 
            command=self._sync_to_knowledge_base,
            width=12
        ).pack(side=tk.LEFT, padx=2)
        
        # 编辑器
        editor_frame = ttk.LabelFrame(right_frame, text="Markdown 编辑器", padding=5)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.editor_text = scrolledtext.ScrolledText(
            editor_frame,
            font=("Consolas", 11),
            wrap=tk.WORD,
            undo=True
        )
        self.editor_text.pack(fill=tk.BOTH, expand=True)
        
        # 绑定修改事件
        self.editor_text.bind('<<Modified>>', self._on_text_modified)
        self.editor_text.bind('<KeyRelease>', self._on_key_release)
    
    def _refresh_worldview_list(self):
        """刷新世界观文件列表"""
        self.file_listbox.delete(0, tk.END)
        
        if self.worldview_builder:
            files = self.worldview_builder.list_worldview_files()
            
            for f in files:
                self.file_listbox.insert(tk.END, f["name"])
            
            self.file_stats_label.config(
                text=f"共 {len(files)} 个世界观文件"
            )
        else:
            self.file_stats_label.config(text="世界观构建器未初始化")
    
    def _on_file_select(self, event):
        """文件选择事件"""
        pass  # 单击只选中，不加载
    
    def _on_file_double_click(self, event):
        """文件双击事件"""
        selection = self.file_listbox.curselection()
        if not selection:
            return
        
        # 检查是否有未保存的修改
        if self.is_modified:
            if messagebox.askyesno("确认", "当前文件有未保存的修改，是否保存？"):
                self._save_worldview()
        
        filename = self.file_listbox.get(selection[0])
        self._load_worldview(filename)
    
    def _load_worldview(self, name: str):
        """加载世界观文件"""
        if not self.worldview_builder:
            messagebox.showwarning("警告", "世界观构建器未初始化")
            return
        
        try:
            content = self.worldview_builder.load_worldview(name)
            
            self.current_file = name
            self.is_modified = False
            
            self.editor_text.delete("1.0", tk.END)
            self.editor_text.insert("1.0", content)
            self.editor_text.edit_modified(False)
            
            self.file_title_label.config(text=f"📄 {name}.md")
            self.modified_label.config(text="")
            
        except FileNotFoundError:
            messagebox.showerror("错误", f"文件不存在: {name}.md")
        except Exception as e:
            messagebox.showerror("错误", f"加载文件时出错: {str(e)}")
    
    def _save_worldview(self):
        """保存世界观文件"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择或创建一个文件")
            return
        
        if not self.worldview_builder:
            messagebox.showwarning("警告", "世界观构建器未初始化")
            return
        
        content = self.editor_text.get("1.0", tk.END)
        
        try:
            success = self.worldview_builder.save_worldview(self.current_file, content)
            
            if success:
                self.is_modified = False
                self.editor_text.edit_modified(False)
                self.modified_label.config(text="")
                messagebox.showinfo("成功", f"世界观已保存: {self.current_file}.md")
            else:
                messagebox.showerror("错误", "保存失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存时出错: {str(e)}")
    
    def _reload_worldview(self):
        """重新加载当前文件"""
        if not self.current_file:
            return
        
        if self.is_modified:
            if not messagebox.askyesno("确认", "放弃未保存的修改？"):
                return
        
        self._load_worldview(self.current_file)
    
    def _new_worldview(self):
        """新建世界观"""
        name = simpledialog.askstring("新建世界观", "请输入世界观名称:")
        
        if not name:
            return
        
        # 清理文件名
        name = name.strip().replace(" ", "_")
        
        if not self.worldview_builder:
            messagebox.showwarning("警告", "世界观构建器未初始化")
            return
        
        # 检查是否已存在
        files = self.worldview_builder.list_worldview_files()
        if any(f["name"] == name for f in files):
            messagebox.showwarning("警告", f"世界观 '{name}' 已存在")
            return
        
        # 创建空模板
        template = f"""# {name}

## 世界基本信息

**世界名称**：{name}

**时代背景**：

**地理位置**：

## 世界特征

### 1. 基本设定

<!-- 在这里描述世界的基本设定 -->

### 2. 规则与限制

<!-- 在这里描述世界的规则和限制 -->

### 3. 重要地点

<!-- 在这里描述世界中的重要地点 -->

### 4. 重要人物

<!-- 在这里描述世界中的重要人物 -->

## 注意事项

- 保持世界观的一致性
- 自然地融入对话中

---

*创建时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        try:
            self.worldview_builder.save_worldview(name, template)
            self._refresh_worldview_list()
            self._load_worldview(name)
            messagebox.showinfo("成功", f"世界观 '{name}' 已创建")
            
        except Exception as e:
            messagebox.showerror("错误", f"创建失败: {str(e)}")
    
    def _delete_worldview(self):
        """删除世界观"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的世界观")
            return
        
        filename = self.file_listbox.get(selection[0])
        
        # 不允许删除默认世界观
        if filename == "default_world":
            messagebox.showwarning("警告", "不能删除默认世界观")
            return
        
        if not messagebox.askyesno("确认", f"确定要删除世界观 '{filename}' 吗？\n此操作不可恢复！"):
            return
        
        if not self.worldview_builder:
            return
        
        try:
            success = self.worldview_builder.delete_worldview(filename)
            
            if success:
                # 如果删除的是当前编辑的文件，清空编辑器
                if self.current_file == filename:
                    self.current_file = None
                    self.editor_text.delete("1.0", tk.END)
                    self.file_title_label.config(text="未选择文件")
                
                self._refresh_worldview_list()
                messagebox.showinfo("成功", f"世界观 '{filename}' 已删除")
            else:
                messagebox.showerror("错误", "删除失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"删除时出错: {str(e)}")
    
    def _generate_with_ai(self):
        """使用 AI 生成世界观"""
        description = simpledialog.askstring(
            "AI 生成世界观", 
            "请描述你想要的世界观:\n(例如: 一个充满魔法的中世纪世界)",
            parent=self.parent
        )
        
        if not description:
            return
        
        if not self.worldview_builder:
            messagebox.showwarning("警告", "世界观构建器未初始化")
            return
        
        try:
            # 显示进度
            self.file_title_label.config(text="⏳ 正在生成...")
            self.parent.update()
            
            content = self.worldview_builder.create_worldview_from_natural_language(
                description,
                use_llm=True
            )
            
            # 插入到编辑器
            self.editor_text.delete("1.0", tk.END)
            self.editor_text.insert("1.0", content)
            
            self.is_modified = True
            self.file_title_label.config(text="🆕 新生成的世界观（未保存）")
            self.modified_label.config(text="● 未保存")
            
            messagebox.showinfo("成功", "世界观已生成，请编辑后保存")
            
        except Exception as e:
            messagebox.showerror("错误", f"生成失败: {str(e)}")
            self.file_title_label.config(text="生成失败")
    
    def _sync_to_cognee(self):
        """同步到 Cognee"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个世界观文件")
            return
        
        if not self.worldview_builder:
            messagebox.showwarning("警告", "世界观构建器未初始化")
            return
        
        if not self.worldview_builder.cognee_manager:
            messagebox.showwarning("警告", "Cognee 管理器未配置")
            return
        
        loop = None
        try:
            # 运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(
                self.worldview_builder.sync_to_cognee(self.current_file)
            )
            
            if success:
                messagebox.showinfo("成功", f"世界观已同步到 Cognee")
            else:
                messagebox.showerror("错误", "同步失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"同步时出错: {str(e)}")
        finally:
            # 确保事件循环在使用后被关闭，避免资源泄漏
            if loop is not None and not loop.is_closed():
                loop.close()
    
    def _sync_to_knowledge_base(self):
        """同步到知识库"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先选择一个世界观文件")
            return
        
        if not self.worldview_builder:
            messagebox.showwarning("警告", "世界观构建器未初始化")
            return
        
        try:
            count = self.worldview_builder.sync_to_knowledge_base(self.current_file)
            
            if count > 0:
                messagebox.showinfo("成功", f"已同步 {count} 个世界观模块到知识库")
            else:
                messagebox.showwarning("警告", "没有模块被同步")
                
        except Exception as e:
            messagebox.showerror("错误", f"同步时出错: {str(e)}")
    
    def _on_text_modified(self, event):
        """文本修改事件"""
        if self.editor_text.edit_modified():
            self.is_modified = True
            self.modified_label.config(text="● 未保存")
    
    def _on_key_release(self, event):
        """按键释放事件"""
        if self.editor_text.edit_modified() and not self.is_modified:
            self.is_modified = True
            self.modified_label.config(text="● 未保存")


class CogneeWorldviewManagerGUI:
    """
    Cognee 记忆与世界观管理综合 GUI
    整合 Cognee 记忆管理和世界观构建功能
    """
    
    def __init__(self, parent_frame, cognee_manager=None, worldview_builder=None):
        """
        初始化综合管理 GUI
        
        Args:
            parent_frame: 父容器
            cognee_manager: Cognee 记忆管理器
            worldview_builder: 世界观构建器
        """
        self.parent = parent_frame
        self.cognee_manager = cognee_manager
        self.worldview_builder = worldview_builder
        
        # 创建主标签页
        self.notebook = ttk.Notebook(self.parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Cognee 记忆管理标签页
        cognee_frame = ttk.Frame(self.notebook)
        self.notebook.add(cognee_frame, text="🧠 Cognee 记忆")
        self.cognee_gui = CogneeMemoryGUI(cognee_frame, cognee_manager)
        
        # 世界观构建标签页
        worldview_frame = ttk.Frame(self.notebook)
        self.notebook.add(worldview_frame, text="🌍 世界观构建")
        self.worldview_gui = WorldviewBuilderGUI(worldview_frame, worldview_builder)
        
        debug_logger.log_info('CogneeWorldviewManagerGUI', 'Cognee 与世界观管理 GUI 已初始化')
