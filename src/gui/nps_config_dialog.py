"""
NPS插件配置对话框
提供可视化的插件配置管理界面
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, Any, Optional
from src.nps.nps_config_manager import NPSConfigManager
from src.nps.nps_registry import NPSTool


class NPSPluginConfigDialog:
    """
    NPS插件配置对话框
    允许用户可视化地编辑插件配置
    """
    
    def __init__(self, parent, tool: NPSTool, config_manager: NPSConfigManager):
        """
        初始化配置对话框
        
        Args:
            parent: 父窗口
            tool: NPS工具对象
            config_manager: 配置管理器
        """
        self.parent = parent
        self.tool = tool
        self.config_manager = config_manager
        self.config_widgets = {}
        self.result = None
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"配置 - {tool.name}")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 加载当前配置
        self.current_config = self.config_manager.get_plugin_config(tool.tool_id)
        
        # 创建界面
        self.create_widgets()
        
        # 居中显示
        self.center_dialog()
    
    def center_dialog(self):
        """使对话框居中显示"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """创建所有界面组件"""
        # 顶部信息区
        info_frame = ttk.Frame(self.dialog, padding=10)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(info_frame, text=f"🔧 {self.tool.name}",
                 font=("微软雅黑", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"工具ID: {self.tool.tool_id}",
                 font=("微软雅黑", 9), foreground="gray").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"版本: {self.tool.version}",
                 font=("微软雅黑", 9), foreground="gray").pack(anchor=tk.W)
        
        ttk.Separator(self.dialog, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # 配置区域（使用滚动容器）
        canvas_frame = ttk.Frame(self.dialog)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建Canvas和滚动条
        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        
        # 创建配置内容容器
        self.config_frame = ttk.Frame(canvas)
        
        # 配置滚动
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.create_window((0, 0), window=self.config_frame, anchor=tk.NW)
        
        # 布局
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 更新滚动区域
        self.config_frame.bind('<Configure>',
                              lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        
        # 创建配置项
        self.create_config_fields()
        
        # 按钮区域
        button_frame = ttk.Frame(self.dialog, padding=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Button(button_frame, text="💾 保存",
                  command=self.save_config, width=12).pack(side=tk.RIGHT, padx=2)
        ttk.Button(button_frame, text="❌ 取消",
                  command=self.cancel, width=12).pack(side=tk.RIGHT, padx=2)
        ttk.Button(button_frame, text="🔄 重置",
                  command=self.reset_config, width=12).pack(side=tk.RIGHT, padx=2)
        ttk.Button(button_frame, text="📤 导出",
                  command=self.export_config, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="📥 导入",
                  command=self.import_config, width=12).pack(side=tk.LEFT, padx=2)
    
    def create_config_fields(self):
        """创建配置字段"""
        # 根据工具ID创建特定的配置字段
        if self.tool.tool_id == 'websearch':
            self.create_websearch_fields()
        elif self.tool.tool_id == 'systime':
            self.create_systime_fields()
        else:
            self.create_generic_fields()
        
        # 通用字段：启用/禁用
        self.create_enabled_field()
    
    def create_websearch_fields(self):
        """创建网络搜索工具的配置字段"""
        row = 0
        
        # API Key
        ttk.Label(self.config_frame, text="SerpAPI Key:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        api_key_frame = ttk.Frame(self.config_frame)
        api_key_frame.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        
        api_key_var = tk.StringVar(value=self.current_config.get('api_key', '${SERPAPI_API_KEY}'))
        api_key_entry = ttk.Entry(api_key_frame, textvariable=api_key_var, show="*", width=40)
        api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 显示/隐藏按钮
        show_btn = ttk.Button(api_key_frame, text="👁", width=3,
                             command=lambda: self.toggle_password_visibility(api_key_entry))
        show_btn.pack(side=tk.LEFT, padx=2)
        
        self.config_widgets['api_key'] = api_key_var
        
        ttk.Label(self.config_frame, text="提示：可使用${ENV_VAR}引用环境变量",
                 font=("微软雅黑", 8), foreground="gray").grid(
            row=row+1, column=1, sticky=tk.W, padx=5, pady=0)
        row += 2
        
        # 搜索引擎
        ttk.Label(self.config_frame, text="搜索引擎:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        engine_var = tk.StringVar(value=self.current_config.get('engine', 'google'))
        engine_combo = ttk.Combobox(self.config_frame, textvariable=engine_var,
                                    values=['google', 'bing', 'yahoo'], width=37, state='readonly')
        engine_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        self.config_widgets['engine'] = engine_var
        row += 1
        
        # 结果数量
        ttk.Label(self.config_frame, text="结果数量:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        num_results_var = tk.IntVar(value=self.current_config.get('num_results', 5))
        num_results_spin = ttk.Spinbox(self.config_frame, from_=1, to=20,
                                       textvariable=num_results_var, width=37)
        num_results_spin.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        self.config_widgets['num_results'] = num_results_var
        row += 1
        
        # 语言
        ttk.Label(self.config_frame, text="语言:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        language_var = tk.StringVar(value=self.current_config.get('language', 'zh-cn'))
        language_combo = ttk.Combobox(self.config_frame, textvariable=language_var,
                                      values=['zh-cn', 'en', 'ja', 'ko'], width=37, state='readonly')
        language_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        self.config_widgets['language'] = language_var
        row += 1
        
        # 配置列权重
        self.config_frame.columnconfigure(1, weight=1)
    
    def create_systime_fields(self):
        """创建系统时间工具的配置字段"""
        row = 0
        
        # 时区
        ttk.Label(self.config_frame, text="时区:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        timezone_var = tk.StringVar(value=self.current_config.get('timezone', 'Asia/Shanghai'))
        timezone_combo = ttk.Combobox(self.config_frame, textvariable=timezone_var,
                                      values=['Asia/Shanghai', 'UTC', 'America/New_York',
                                             'Europe/London', 'Asia/Tokyo'],
                                      width=37)
        timezone_combo.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        self.config_widgets['timezone'] = timezone_var
        row += 1
        
        # 时间格式
        ttk.Label(self.config_frame, text="时间格式:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        format_var = tk.StringVar(value=self.current_config.get('format', '%Y-%m-%d %H:%M:%S'))
        format_entry = ttk.Entry(self.config_frame, textvariable=format_var, width=40)
        format_entry.grid(row=row, column=1, sticky=tk.EW, padx=5, pady=5)
        self.config_widgets['format'] = format_var
        
        ttk.Label(self.config_frame, text="例如: %Y-%m-%d %H:%M:%S",
                 font=("微软雅黑", 8), foreground="gray").grid(
            row=row+1, column=1, sticky=tk.W, padx=5, pady=0)
        row += 2
        
        # 配置列权重
        self.config_frame.columnconfigure(1, weight=1)
    
    def create_generic_fields(self):
        """创建通用配置字段（用于未知的插件）"""
        row = 0
        
        ttk.Label(self.config_frame, text="自定义配置:",
                 font=("微软雅黑", 10, "bold")).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        
        # JSON文本编辑器
        config_text = scrolledtext.ScrolledText(self.config_frame, height=10, width=50,
                                               font=("Consolas", 10))
        config_text.grid(row=row+1, column=0, columnspan=2, sticky=tk.NSEW, padx=5, pady=5)
        
        # 加载当前配置
        import json
        config_json = json.dumps(self.current_config, indent=4, ensure_ascii=False)
        config_text.insert("1.0", config_json)
        
        self.config_widgets['_json_config'] = config_text
        
        self.config_frame.rowconfigure(row+1, weight=1)
        self.config_frame.columnconfigure(1, weight=1)
    
    def create_enabled_field(self):
        """创建启用/禁用字段"""
        separator = ttk.Separator(self.config_frame, orient=tk.HORIZONTAL)
        separator.grid(row=100, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        enabled_var = tk.BooleanVar(value=self.current_config.get('enabled', True))
        enabled_check = ttk.Checkbutton(self.config_frame, text="✓ 启用此插件",
                                       variable=enabled_var)
        enabled_check.grid(row=101, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        self.config_widgets['enabled'] = enabled_var
    
    def toggle_password_visibility(self, entry_widget):
        """切换密码可见性"""
        current_show = entry_widget.cget('show')
        if current_show == '*':
            entry_widget.config(show='')
        else:
            entry_widget.config(show='*')
    
    def save_config(self):
        """保存配置"""
        try:
            # 收集配置
            new_config = {}
            
            # 如果是JSON编辑模式
            if '_json_config' in self.config_widgets:
                import json
                json_text = self.config_widgets['_json_config'].get("1.0", tk.END).strip()
                try:
                    new_config = json.loads(json_text)
                except json.JSONDecodeError as e:
                    messagebox.showerror("错误", f"JSON格式错误：{str(e)}")
                    return
            else:
                # 收集各个字段的值
                for key, widget in self.config_widgets.items():
                    if key != 'enabled':
                        value = widget.get()
                        new_config[key] = value
            
            # 添加enabled字段
            new_config['enabled'] = self.config_widgets['enabled'].get()
            
            # 保存配置
            if self.config_manager.set_plugin_config(self.tool.tool_id, new_config):
                messagebox.showinfo("成功", "配置已保存")
                self.result = new_config
                self.dialog.destroy()
            else:
                messagebox.showerror("错误", "保存配置失败")
                
        except Exception as e:
            messagebox.showerror("错误", f"保存配置时出错：{str(e)}")
    
    def reset_config(self):
        """重置配置为默认值"""
        if messagebox.askyesno("确认", "确定要重置配置为默认值吗？"):
            self.current_config = {}
            # 重新创建配置字段
            for widget in self.config_frame.winfo_children():
                widget.destroy()
            self.config_widgets = {}
            self.create_config_fields()
    
    def cancel(self):
        """取消并关闭对话框"""
        self.result = None
        self.dialog.destroy()
    
    def export_config(self):
        """导出配置到文件"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile=f"{self.tool.tool_id}_config.json"
        )
        
        if filename:
            if self.config_manager.export_config(self.tool.tool_id, filename):
                messagebox.showinfo("成功", f"配置已导出到：\n{filename}")
            else:
                messagebox.showerror("错误", "导出配置失败")
    
    def import_config(self):
        """从文件导入配置"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="导入配置",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if filename:
            if self.config_manager.import_config(self.tool.tool_id, filename):
                messagebox.showinfo("成功", "配置已导入")
                # 重新加载配置
                self.current_config = self.config_manager.get_plugin_config(self.tool.tool_id)
                # 重新创建配置字段
                for widget in self.config_frame.winfo_children():
                    widget.destroy()
                self.config_widgets = {}
                self.create_config_fields()
            else:
                messagebox.showerror("错误", "导入配置失败")
    
    def show(self) -> Optional[Dict[str, Any]]:
        """显示对话框并等待用户操作"""
        self.dialog.wait_window()
        return self.result
