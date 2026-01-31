"""
NPS (Neo Plugin System) 工具管理GUI模块
提供可视化界面管理NPS工具的配置和状态
"""

import os
import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog, filedialog
from typing import Dict, Any, List
from datetime import datetime
from src.nps.nps_registry import NPSRegistry, NPSTool

# 配置常量
DEFAULT_REFRESH_INTERVAL = 3000  # 默认自动刷新间隔（毫秒）


class NPSManagerGUI:
    """
    NPS 工具管理GUI界面
    提供NPS工具的可视化管理功能
    """

    def __init__(self, parent_frame, nps_registry: NPSRegistry = None):
        """
        初始化NPS管理GUI

        Args:
            parent_frame: 父容器
            nps_registry: NPS工具注册表实例
        """
        self.parent = parent_frame
        self.registry = nps_registry or NPSRegistry()
        
        # 如果注册表为空，扫描并注册工具
        if not self.registry.get_all_tools():
            self.registry.scan_and_register()
        
        # 自动刷新相关
        self.auto_refresh_enabled = True
        self.refresh_interval = DEFAULT_REFRESH_INTERVAL
        self.refresh_job = None
        
        # 创建界面
        self.create_widgets()
        
        # 首次刷新数据
        self.refresh_tools()
        
        # 启动自动刷新
        self.start_auto_refresh()
        
        # 绑定窗口关闭事件
        self.parent.bind('<Destroy>', self.on_destroy)

    def on_destroy(self, event=None):
        """窗口销毁时的清理工作"""
        self.stop_auto_refresh()

    def create_widgets(self):
        """创建所有GUI组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(toolbar, text="🔧 NPS工具管理", font=("微软雅黑", 12, "bold")).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(toolbar, text="🔄 刷新", command=self.refresh_tools, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="➕ 创建工具", command=self.create_new_tool, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📥 导入工具", command=self.import_tool, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📊 统计信息", command=self.show_statistics, width=12).pack(side=tk.LEFT, padx=2)
        
        # 自动刷新开关
        self.auto_refresh_btn = ttk.Button(toolbar, text="⏸ 暂停刷新", command=self.toggle_auto_refresh, width=12)
        self.auto_refresh_btn.pack(side=tk.LEFT, padx=2)
        
        # 最后刷新时间
        self.last_refresh_label = ttk.Label(toolbar, text="", font=("微软雅黑", 8), foreground="gray")
        self.last_refresh_label.pack(side=tk.RIGHT, padx=5)
        
        # 分割线
        ttk.Separator(self.parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=2)
        
        # 工具列表区域
        list_frame = ttk.Frame(self.parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        scrollbar_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        
        # Treeview
        self.tree = ttk.Treeview(
            list_frame,
            columns=("tool_id", "name", "description", "version", "author", "enabled", "keywords"),
            show="headings",
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )
        
        # 配置列
        self.tree.heading("tool_id", text="工具ID")
        self.tree.heading("name", text="名称")
        self.tree.heading("description", text="功能描述")
        self.tree.heading("version", text="版本")
        self.tree.heading("author", text="作者")
        self.tree.heading("enabled", text="状态")
        self.tree.heading("keywords", text="关键词")
        
        self.tree.column("tool_id", width=100, minwidth=80, stretch=False)
        self.tree.column("name", width=120, minwidth=100, stretch=False)
        self.tree.column("description", width=250, minwidth=200, stretch=True)
        self.tree.column("version", width=70, minwidth=60, stretch=False)
        self.tree.column("author", width=100, minwidth=80, stretch=False)
        self.tree.column("enabled", width=70, minwidth=60, stretch=False)
        self.tree.column("keywords", width=200, minwidth=150, stretch=True)
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # 双击查看详情
        self.tree.bind("<Double-1>", lambda e: self.view_tool_details())
        
        # 右键菜单
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="📋 查看详情", command=self.view_tool_details)
        self.context_menu.add_command(label="✏️ 编辑配置", command=self.edit_tool_config)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="✓ 启用", command=self.enable_tool)
        self.context_menu.add_command(label="✗ 禁用", command=self.disable_tool)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🧪 测试工具", command=self.test_tool)
        self.context_menu.add_command(label="📤 导出工具", command=self.export_tool)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ 删除工具", command=self.delete_tool)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # 底部工具详情区域
        detail_frame = ttk.LabelFrame(self.parent, text="📝 工具详情", padding=5)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.detail_text = scrolledtext.ScrolledText(
            detail_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            height=8,
            bg="#f9f9f9",
            relief=tk.FLAT
        )
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.config(state=tk.DISABLED)
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self.on_tool_select)
        
        # 底部统计区域
        stats_frame = ttk.Frame(self.parent)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="", font=("微软雅黑", 9))
        self.stats_label.pack(side=tk.LEFT, padx=5)

    def refresh_tools(self):
        """刷新工具列表"""
        # 清空现有内容
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        try:
            # 获取所有工具
            tools = self.registry.get_all_tools()
            
            for tool in tools:
                # 状态显示
                status = "✓ 启用" if tool.enabled else "✗ 禁用"
                
                # 关键词显示
                keywords = ", ".join(tool.keywords[:5])  # 最多显示5个关键词
                if len(tool.keywords) > 5:
                    keywords += f" +{len(tool.keywords)-5}..."
                
                # 插入数据
                self.tree.insert("", tk.END, values=(
                    tool.tool_id,
                    tool.name,
                    tool.description[:50] + "..." if len(tool.description) > 50 else tool.description,
                    tool.version,
                    tool.author,
                    status,
                    keywords
                ))
            
            # 更新统计
            stats = self.registry.get_statistics()
            self.stats_label.config(
                text=f"总计: {stats['total_tools']} 个工具 | "
                     f"已启用: {stats['enabled_tools']} | "
                     f"已禁用: {stats['disabled_tools']}"
            )
            
            # 更新最后刷新时间
            self.last_refresh_label.config(
                text=f"最后刷新: {datetime.now().strftime('%H:%M:%S')}"
            )
            
        except Exception as e:
            messagebox.showerror("错误", f"刷新工具列表失败: {str(e)}")

    def on_tool_select(self, event=None):
        """工具选择事件"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        tool = self.registry.get_tool(tool_id)
        if tool:
            self.show_tool_detail(tool)

    def show_tool_detail(self, tool: NPSTool):
        """显示工具详情"""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        
        detail = f"""工具ID: {tool.tool_id}
名称: {tool.name}
版本: {tool.version}
作者: {tool.author}
状态: {'启用' if tool.enabled else '禁用'}

功能描述:
{tool.description}

触发关键词:
{', '.join(tool.keywords) if tool.keywords else '无'}
"""
        
        self.detail_text.insert("1.0", detail)
        self.detail_text.config(state=tk.DISABLED)

    def show_context_menu(self, event):
        """显示右键菜单"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def view_tool_details(self):
        """查看工具详情"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个工具")
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        tool = self.registry.get_tool(tool_id)
        if tool:
            # 创建详情对话框
            dialog = tk.Toplevel(self.parent)
            dialog.title(f"工具详情 - {tool.name}")
            dialog.geometry("500x400")
            dialog.transient(self.parent)
            
            # 详情内容
            text = scrolledtext.ScrolledText(
                dialog,
                wrap=tk.WORD,
                font=("Consolas", 10),
                bg="#f9f9f9"
            )
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            detail = f"""═══════════════════════════════════════
             NPS工具详细信息
═══════════════════════════════════════

【基本信息】
工具ID: {tool.tool_id}
名称: {tool.name}
版本: {tool.version}
作者: {tool.author}
状态: {'✓ 启用' if tool.enabled else '✗ 禁用'}

【功能描述】
{tool.description}

【触发关键词】
{', '.join(tool.keywords) if tool.keywords else '无'}

【配置文件】
{os.path.join(self.registry.tools_dir, tool.tool_id + '.NPS')}

【模块文件】
{os.path.join(self.registry.tools_dir, tool.tool_id + '.py')}
"""
            
            text.insert("1.0", detail)
            text.config(state=tk.DISABLED)
            
            # 关闭按钮
            ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)

    def edit_tool_config(self):
        """编辑工具配置"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个工具")
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        tool = self.registry.get_tool(tool_id)
        if not tool:
            return
        
        # 创建编辑对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"编辑工具配置 - {tool.name}")
        dialog.geometry("500x500")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 表单区域
        form_frame = ttk.Frame(dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工具ID (只读)
        ttk.Label(form_frame, text="工具ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        id_entry = ttk.Entry(form_frame, width=40)
        id_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        id_entry.insert(0, tool.tool_id)
        id_entry.config(state="readonly")
        
        # 名称
        ttk.Label(form_frame, text="名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar(value=tool.name)
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=40)
        name_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        # 版本
        ttk.Label(form_frame, text="版本:").grid(row=2, column=0, sticky=tk.W, pady=5)
        version_var = tk.StringVar(value=tool.version)
        version_entry = ttk.Entry(form_frame, textvariable=version_var, width=40)
        version_entry.grid(row=2, column=1, pady=5, sticky=tk.W)
        
        # 作者
        ttk.Label(form_frame, text="作者:").grid(row=3, column=0, sticky=tk.W, pady=5)
        author_var = tk.StringVar(value=tool.author)
        author_entry = ttk.Entry(form_frame, textvariable=author_var, width=40)
        author_entry.grid(row=3, column=1, pady=5, sticky=tk.W)
        
        # 描述
        ttk.Label(form_frame, text="描述:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(form_frame, width=40, height=4)
        desc_text.grid(row=4, column=1, pady=5, sticky=tk.W)
        desc_text.insert("1.0", tool.description)
        
        # 关键词
        ttk.Label(form_frame, text="关键词:").grid(row=5, column=0, sticky=tk.NW, pady=5)
        keywords_text = tk.Text(form_frame, width=40, height=3)
        keywords_text.grid(row=5, column=1, pady=5, sticky=tk.W)
        keywords_text.insert("1.0", ", ".join(tool.keywords))
        ttk.Label(form_frame, text="(逗号分隔)", font=("微软雅黑", 8), foreground="gray").grid(row=5, column=1, sticky=tk.E, pady=5)
        
        # 启用状态
        enabled_var = tk.BooleanVar(value=tool.enabled)
        enabled_check = ttk.Checkbutton(form_frame, text="启用此工具", variable=enabled_var)
        enabled_check.grid(row=6, column=1, sticky=tk.W, pady=10)
        
        def save_config():
            """保存配置"""
            try:
                # 读取.NPS文件
                nps_path = os.path.join(self.registry.tools_dir, f"{tool.tool_id}.NPS")
                if os.path.exists(nps_path):
                    with open(nps_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                else:
                    config = {}
                
                # 更新配置
                config['name'] = name_var.get()
                config['version'] = version_var.get()
                config['author'] = author_var.get()
                config['description'] = desc_text.get("1.0", tk.END).strip()
                
                # 解析关键词
                keywords_str = keywords_text.get("1.0", tk.END).strip()
                config['keywords'] = [k.strip() for k in keywords_str.split(',') if k.strip()]
                
                config['enabled'] = enabled_var.get()
                
                # 保存文件
                with open(nps_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                # 更新内存中的工具
                tool.name = config['name']
                tool.version = config['version']
                tool.author = config['author']
                tool.description = config['description']
                tool.keywords = config['keywords']
                tool.enabled = config['enabled']
                
                messagebox.showinfo("成功", "配置已保存")
                dialog.destroy()
                self.refresh_tools()
                
            except Exception as e:
                messagebox.showerror("错误", f"保存配置失败: {str(e)}")
        
        # 按钮区域
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="保存", command=save_config, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

    def enable_tool(self):
        """启用工具"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        tool = self.registry.get_tool(tool_id)
        if tool:
            tool.enabled = True
            self._save_tool_enabled_state(tool_id, True)
            self.refresh_tools()

    def disable_tool(self):
        """禁用工具"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        tool = self.registry.get_tool(tool_id)
        if tool:
            tool.enabled = False
            self._save_tool_enabled_state(tool_id, False)
            self.refresh_tools()

    def _save_tool_enabled_state(self, tool_id: str, enabled: bool):
        """保存工具启用状态到.NPS文件"""
        try:
            nps_path = os.path.join(self.registry.tools_dir, f"{tool_id}.NPS")
            if os.path.exists(nps_path):
                with open(nps_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['enabled'] = enabled
                
                with open(nps_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("错误", f"保存状态失败: {str(e)}")

    def test_tool(self):
        """测试工具"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个工具")
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        tool = self.registry.get_tool(tool_id)
        if not tool:
            return
        
        # 创建测试对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"测试工具 - {tool.name}")
        dialog.geometry("500x400")
        dialog.transient(self.parent)
        
        # 输入区域
        input_frame = ttk.LabelFrame(dialog, text="测试输入", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="模拟用户输入:").pack(anchor=tk.W)
        test_input = ttk.Entry(input_frame, width=60)
        test_input.pack(fill=tk.X, pady=5)
        
        # 根据工具的关键词生成默认测试输入
        default_test = ""
        if tool.keywords:
            # 使用第一个关键词构建测试输入
            default_test = f"请告诉我关于{tool.keywords[0]}的信息"
        else:
            default_test = f"测试{tool.name}"
        test_input.insert(0, default_test)
        
        # 结果区域
        result_frame = ttk.LabelFrame(dialog, text="执行结果", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        result_text = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),
            bg="#f9f9f9"
        )
        result_text.pack(fill=tk.BOTH, expand=True)
        
        def run_test():
            """执行测试"""
            user_input = test_input.get()
            
            result_text.config(state=tk.NORMAL)
            result_text.delete("1.0", tk.END)
            
            try:
                result = tool.execute({'user_input': user_input})
                
                if result['success']:
                    result_text.insert(tk.END, "✓ 执行成功\n\n")
                    result_text.insert(tk.END, f"工具: {result['tool_name']}\n")
                    result_text.insert(tk.END, f"工具ID: {result['tool_id']}\n\n")
                    result_text.insert(tk.END, "返回结果:\n")
                    result_text.insert(tk.END, json.dumps(result['result'], ensure_ascii=False, indent=2))
                else:
                    result_text.insert(tk.END, "✗ 执行失败\n\n")
                    result_text.insert(tk.END, f"错误: {result.get('error', '未知错误')}")
                    
            except Exception as e:
                result_text.insert(tk.END, f"✗ 执行异常\n\n错误: {str(e)}")
            
            result_text.config(state=tk.DISABLED)
        
        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="🧪 执行测试", command=run_test, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="关闭", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

    def export_tool(self):
        """导出工具"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个工具")
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        
        # 选择导出目录
        export_dir = filedialog.askdirectory(title="选择导出目录")
        if not export_dir:
            return
        
        try:
            # 复制.NPS文件和.py文件
            import shutil
            
            nps_path = os.path.join(self.registry.tools_dir, f"{tool_id}.NPS")
            py_path = os.path.join(self.registry.tools_dir, f"{tool_id}.py")
            
            if os.path.exists(nps_path):
                shutil.copy(nps_path, os.path.join(export_dir, f"{tool_id}.NPS"))
            
            if os.path.exists(py_path):
                shutil.copy(py_path, os.path.join(export_dir, f"{tool_id}.py"))
            
            messagebox.showinfo("成功", f"工具已导出到: {export_dir}")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")

    def delete_tool(self):
        """删除工具"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请先选择一个工具")
            return
        
        item = self.tree.item(selection[0])
        tool_id = item['values'][0]
        tool_name = item['values'][1]
        
        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除工具「{tool_name}」吗？\n\n这将删除工具的配置文件和代码文件。"):
            return
        
        try:
            # 删除文件
            nps_path = os.path.join(self.registry.tools_dir, f"{tool_id}.NPS")
            py_path = os.path.join(self.registry.tools_dir, f"{tool_id}.py")
            
            if os.path.exists(nps_path):
                os.remove(nps_path)
            
            if os.path.exists(py_path):
                os.remove(py_path)
            
            # 从注册表中删除
            self.registry.unregister_tool(tool_id)
            
            messagebox.showinfo("成功", "工具已删除")
            self.refresh_tools()
            
        except Exception as e:
            messagebox.showerror("错误", f"删除失败: {str(e)}")

    def create_new_tool(self):
        """创建新工具"""
        # 创建向导对话框
        dialog = tk.Toplevel(self.parent)
        dialog.title("创建新工具")
        dialog.geometry("600x600")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # 表单区域
        form_frame = ttk.Frame(dialog, padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # 工具ID
        ttk.Label(form_frame, text="工具ID (唯一标识):").grid(row=0, column=0, sticky=tk.W, pady=5)
        id_var = tk.StringVar()
        id_entry = ttk.Entry(form_frame, textvariable=id_var, width=40)
        id_entry.grid(row=0, column=1, pady=5, sticky=tk.W)
        
        # 名称
        ttk.Label(form_frame, text="名称:").grid(row=1, column=0, sticky=tk.W, pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=40)
        name_entry.grid(row=1, column=1, pady=5, sticky=tk.W)
        
        # 版本
        ttk.Label(form_frame, text="版本:").grid(row=2, column=0, sticky=tk.W, pady=5)
        version_var = tk.StringVar(value="1.0.0")
        version_entry = ttk.Entry(form_frame, textvariable=version_var, width=40)
        version_entry.grid(row=2, column=1, pady=5, sticky=tk.W)
        
        # 作者
        ttk.Label(form_frame, text="作者:").grid(row=3, column=0, sticky=tk.W, pady=5)
        author_var = tk.StringVar(value="Neo Agent")
        author_entry = ttk.Entry(form_frame, textvariable=author_var, width=40)
        author_entry.grid(row=3, column=1, pady=5, sticky=tk.W)
        
        # 描述
        ttk.Label(form_frame, text="功能描述:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        desc_text = tk.Text(form_frame, width=40, height=4)
        desc_text.grid(row=4, column=1, pady=5, sticky=tk.W)
        
        # 关键词
        ttk.Label(form_frame, text="触发关键词:").grid(row=5, column=0, sticky=tk.NW, pady=5)
        keywords_text = tk.Text(form_frame, width=40, height=3)
        keywords_text.grid(row=5, column=1, pady=5, sticky=tk.W)
        ttk.Label(form_frame, text="(逗号分隔)", font=("微软雅黑", 8), foreground="gray").grid(row=5, column=1, sticky=tk.E, pady=5)
        
        # 函数名
        ttk.Label(form_frame, text="执行函数名:").grid(row=6, column=0, sticky=tk.W, pady=5)
        func_var = tk.StringVar(value="execute")
        func_entry = ttk.Entry(form_frame, textvariable=func_var, width=40)
        func_entry.grid(row=6, column=1, pady=5, sticky=tk.W)
        
        # 代码模板
        ttk.Label(form_frame, text="代码模板:").grid(row=7, column=0, sticky=tk.NW, pady=5)
        code_text = scrolledtext.ScrolledText(form_frame, width=50, height=10, font=("Consolas", 9))
        code_text.grid(row=7, column=1, pady=5, sticky=tk.W)
        
        # 默认代码模板
        default_code = '''"""
{name} - NPS工具模块
{description}
"""

from typing import Dict, Any


def {function}(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    工具执行函数

    Args:
        context: 执行上下文，包含user_input等信息

    Returns:
        包含context字段的结果字典
    """
    user_input = context.get('user_input', '') if context else ''
    
    # TODO: 在这里实现工具逻辑
    result = "工具执行结果"
    
    return {{
        'context': result
    }}
'''
        code_text.insert("1.0", default_code)
        
        def create_tool():
            """创建工具"""
            tool_id = id_var.get().strip()
            name = name_var.get().strip()
            version = version_var.get().strip()
            author = author_var.get().strip()
            description = desc_text.get("1.0", tk.END).strip()
            keywords_str = keywords_text.get("1.0", tk.END).strip()
            function = func_var.get().strip()
            code = code_text.get("1.0", tk.END)
            
            # 验证必填字段
            if not tool_id:
                messagebox.showwarning("提示", "请输入工具ID")
                return
            if not name:
                messagebox.showwarning("提示", "请输入工具名称")
                return
            if not description:
                messagebox.showwarning("提示", "请输入功能描述")
                return
            if not function:
                messagebox.showwarning("提示", "请输入执行函数名")
                return
            
            # 检查ID是否已存在
            if self.registry.get_tool(tool_id):
                messagebox.showwarning("提示", f"工具ID「{tool_id}」已存在")
                return
            
            try:
                # 解析关键词
                keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                
                # 创建.NPS配置文件
                config = {
                    'tool_id': tool_id,
                    'name': name,
                    'description': description,
                    'module': tool_id,
                    'function': function,
                    'version': version,
                    'author': author,
                    'keywords': keywords,
                    'enabled': True
                }
                
                nps_path = os.path.join(self.registry.tools_dir, f"{tool_id}.NPS")
                with open(nps_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                # 创建Python模块文件
                # 替换模板中的占位符
                final_code = code.format(
                    name=name,
                    description=description,
                    function=function
                )
                
                py_path = os.path.join(self.registry.tools_dir, f"{tool_id}.py")
                with open(py_path, 'w', encoding='utf-8') as f:
                    f.write(final_code)
                
                # 重新扫描注册工具
                self.registry.scan_and_register()
                
                messagebox.showinfo("成功", f"工具「{name}」创建成功！\n\n请编辑 {py_path} 实现工具逻辑。")
                dialog.destroy()
                self.refresh_tools()
                
            except Exception as e:
                messagebox.showerror("错误", f"创建工具失败: {str(e)}")
        
        # 按钮区域
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text="创建", command=create_tool, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy, width=10).pack(side=tk.LEFT, padx=5)

    def import_tool(self):
        """导入工具"""
        # 选择.NPS文件
        nps_path = filedialog.askopenfilename(
            title="选择工具配置文件",
            filetypes=[("NPS配置文件", "*.NPS"), ("所有文件", "*.*")]
        )
        if not nps_path:
            return
        
        try:
            # 读取配置
            with open(nps_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            tool_id = config.get('tool_id')
            if not tool_id:
                messagebox.showerror("错误", "无效的NPS配置文件：缺少tool_id")
                return
            
            # 检查是否存在对应的Python文件
            source_dir = os.path.dirname(nps_path)
            py_path = os.path.join(source_dir, f"{config.get('module', tool_id)}.py")
            
            if not os.path.exists(py_path):
                messagebox.showwarning("警告", f"未找到对应的Python模块文件: {py_path}\n\n将只导入配置文件。")
            
            # 复制文件到工具目录
            import shutil
            
            dest_nps = os.path.join(self.registry.tools_dir, f"{tool_id}.NPS")
            shutil.copy(nps_path, dest_nps)
            
            if os.path.exists(py_path):
                dest_py = os.path.join(self.registry.tools_dir, f"{tool_id}.py")
                shutil.copy(py_path, dest_py)
            
            # 重新扫描注册
            self.registry.scan_and_register()
            
            messagebox.showinfo("成功", f"工具「{config.get('name', tool_id)}」导入成功！")
            self.refresh_tools()
            
        except json.JSONDecodeError:
            messagebox.showerror("错误", "无效的JSON格式")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")

    def show_statistics(self):
        """显示统计信息"""
        stats = self.registry.get_statistics()
        
        msg = f"""NPS工具系统统计信息
═══════════════════════════════

总工具数: {stats['total_tools']}
已启用: {stats['enabled_tools']}
已禁用: {stats['disabled_tools']}

工具目录: {self.registry.tools_dir}

已注册工具列表:
"""
        for tool_id in stats['tool_ids']:
            tool = self.registry.get_tool(tool_id)
            if tool:
                status = "✓" if tool.enabled else "✗"
                msg += f"  {status} {tool.name} (v{tool.version})\n"
        
        messagebox.showinfo("NPS统计信息", msg)

    def toggle_auto_refresh(self):
        """切换自动刷新"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled
        
        if self.auto_refresh_enabled:
            self.auto_refresh_btn.config(text="⏸ 暂停刷新")
            self.start_auto_refresh()
        else:
            self.auto_refresh_btn.config(text="▶ 继续刷新")
            self.stop_auto_refresh()

    def start_auto_refresh(self):
        """启动自动刷新"""
        if self.auto_refresh_enabled:
            self.refresh_tools()
            self.refresh_job = self.parent.after(self.refresh_interval, self.start_auto_refresh)

    def stop_auto_refresh(self):
        """停止自动刷新"""
        if self.refresh_job:
            self.parent.after_cancel(self.refresh_job)
            self.refresh_job = None
