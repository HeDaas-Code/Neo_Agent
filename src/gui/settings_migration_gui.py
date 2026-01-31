"""
设定迁移 GUI 模块
提供图形界面用于导出和导入智能体设定
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.tools.settings_migration import SettingsMigration
from src.core.database_manager import DatabaseManager


class SettingsMigrationGUI:
    """
    设定迁移图形界面
    """
    
    def __init__(self, parent=None, db_manager: DatabaseManager = None):
        """
        初始化设定迁移GUI
        
        Args:
            parent: 父窗口
            db_manager: 数据库管理器实例
        """
        self.parent = parent
        self.db_manager = db_manager or DatabaseManager()
        self.migration = SettingsMigration(db_manager=self.db_manager)
        
        # 如果有父窗口，嵌入到父窗口中；否则创建独立窗口
        if parent:
            self.window = parent
            self._setup_ui()
        else:
            self.window = tk.Tk()
            self.window.title("智能体设定迁移")
            self.window.geometry("800x700")
            
            # 设置窗口图标（如果存在）
            try:
                self.window.iconbitmap('icon.ico')
            except:
                pass
            
            self._setup_ui()
        
    def _setup_ui(self):
        """设置用户界面"""
        # 创建选项卡
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 导出选项卡
        self.export_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.export_frame, text="导出设定")
        self._setup_export_ui()
        
        # 导入选项卡
        self.import_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.import_frame, text="导入设定")
        self._setup_import_ui()
        
    def _setup_export_ui(self):
        """设置导出界面"""
        # 创建主滚动容器
        main_canvas = tk.Canvas(self.export_frame, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self.export_frame, orient="vertical", command=main_canvas.yview)
        scrollable_main_frame = ttk.Frame(main_canvas)
        
        scrollable_main_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_main_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))
        
        # 说明文本
        info_frame = ttk.LabelFrame(scrollable_main_frame, text="说明", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        info_text = """导出功能可以将当前智能体的配置和数据保存到文件中，便于备份或迁移到其他环境。
导出的文件包含 .env 配置和选定的数据库数据。"""
        ttk.Label(info_frame, text=info_text, wraplength=700, justify=tk.LEFT).pack()
        
        # 导出选项
        options_frame = ttk.LabelFrame(scrollable_main_frame, text="导出选项", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # .env 配置选项
        self.export_env_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="包含 .env 配置文件",
            variable=self.export_env_var
        ).pack(anchor=tk.W, pady=2)
        
        # 数据类别选择
        ttk.Label(options_frame, text="\n选择要导出的数据类别:", 
                 font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        # 全选/取消全选按钮
        select_buttons_frame = ttk.Frame(options_frame)
        select_buttons_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            select_buttons_frame,
            text="全选",
            command=self._select_all_export_categories
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            select_buttons_frame,
            text="取消全选",
            command=self._deselect_all_export_categories
        ).pack(side=tk.LEFT, padx=5)
        
        # 创建滚动框架用于类别选择
        canvas = tk.Canvas(options_frame, height=250)
        scrollbar = ttk.Scrollbar(options_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 数据类别复选框
        self.export_category_vars = {}
        categories = self.migration.get_available_categories()
        
        # 默认选中的类别
        default_selected = [
            'base_knowledge', 'entities', 'long_term_memory',
            'emotion_history', 'environment_descriptions', 'agent_expressions'
        ]
        
        for category_key, category_name in categories.items():
            var = tk.BooleanVar(value=(category_key in default_selected))
            self.export_category_vars[category_key] = var
            
            ttk.Checkbutton(
                scrollable_frame,
                text=f"{category_name} ({category_key})",
                variable=var
            ).pack(anchor=tk.W, pady=2, padx=10)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 导出按钮
        button_frame = ttk.Frame(scrollable_main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            button_frame,
            text="导出设定",
            command=self._do_export,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT, padx=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(scrollable_main_frame, text="导出结果", padding=10)
        result_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.export_result_text = scrolledtext.ScrolledText(
            result_frame,
            height=8,
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.export_result_text.pack(fill=tk.BOTH, expand=True)
        
    def _setup_import_ui(self):
        """设置导入界面"""
        # 创建主滚动容器
        main_canvas = tk.Canvas(self.import_frame, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self.import_frame, orient="vertical", command=main_canvas.yview)
        scrollable_main_frame = ttk.Frame(main_canvas)
        
        scrollable_main_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_main_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        main_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10, padx=(0, 10))
        
        # 说明文本
        info_frame = ttk.LabelFrame(scrollable_main_frame, text="说明", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        info_text = """导入功能可以从导出的配置文件中恢复智能体设定。
您可以选择是否导入 .env 配置和选择要导入的数据类别。
建议先预览导入内容，确认无误后再执行导入。"""
        ttk.Label(info_frame, text=info_text, wraplength=700, justify=tk.LEFT).pack()
        
        # 文件选择
        file_frame = ttk.LabelFrame(scrollable_main_frame, text="选择导入文件", padding=10)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        file_select_frame = ttk.Frame(file_frame)
        file_select_frame.pack(fill=tk.X)
        
        self.import_file_var = tk.StringVar()
        ttk.Entry(
            file_select_frame,
            textvariable=self.import_file_var,
            width=60
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(
            file_select_frame,
            text="浏览...",
            command=self._select_import_file
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            file_frame,
            text="预览导入内容",
            command=self._preview_import
        ).pack(pady=(10, 0))
        
        # 导入选项
        options_frame = ttk.LabelFrame(scrollable_main_frame, text="导入选项", padding=10)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # .env 配置选项
        self.import_env_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="导入 .env 配置文件",
            variable=self.import_env_var
        ).pack(anchor=tk.W, pady=2)
        
        # 覆盖选项
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="覆盖现有数据（谨慎使用）",
            variable=self.overwrite_var
        ).pack(anchor=tk.W, pady=2)
        
        # 数据类别选择
        ttk.Label(options_frame, text="\n选择要导入的数据类别:", 
                 font=('微软雅黑', 10, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        # 创建滚动框架
        canvas = tk.Canvas(options_frame, height=200)
        scrollbar = ttk.Scrollbar(options_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 数据类别复选框
        self.import_category_vars = {}
        categories = self.migration.get_available_categories()
        
        for category_key, category_name in categories.items():
            var = tk.BooleanVar(value=True)
            self.import_category_vars[category_key] = var
            
            ttk.Checkbutton(
                scrollable_frame,
                text=f"{category_name} ({category_key})",
                variable=var
            ).pack(anchor=tk.W, pady=2, padx=10)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 导入按钮
        button_frame = ttk.Frame(scrollable_main_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            button_frame,
            text="执行导入",
            command=self._do_import,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT, padx=5)
        
        # 结果显示
        result_frame = ttk.LabelFrame(scrollable_main_frame, text="导入结果", padding=10)
        result_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.import_result_text = scrolledtext.ScrolledText(
            result_frame,
            height=8,
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.import_result_text.pack(fill=tk.BOTH, expand=True)
        
    def _select_all_export_categories(self):
        """全选导出类别"""
        for var in self.export_category_vars.values():
            var.set(True)
    
    def _deselect_all_export_categories(self):
        """取消全选导出类别"""
        for var in self.export_category_vars.values():
            var.set(False)
    
    def _do_export(self):
        """执行导出"""
        # 获取选中的类别
        selected_categories = [
            key for key, var in self.export_category_vars.items() if var.get()
        ]
        
        if not selected_categories and not self.export_env_var.get():
            messagebox.showwarning("警告", "请至少选择一项要导出的内容")
            return
        
        # 选择保存路径
        default_filename = f"neo_agent_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_path = filedialog.asksaveasfilename(
            title="保存导出文件",
            defaultextension=".json",
            initialfile=default_filename,
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        # 移除扩展名（因为 export_settings 会自动添加）
        if file_path.endswith('.json'):
            file_path = file_path[:-5]
        
        # 显示进度
        self.export_result_text.delete(1.0, tk.END)
        self.export_result_text.insert(tk.END, "正在导出...\n")
        self.window.update()
        
        # 执行导出
        result = self.migration.export_settings(
            export_path=file_path,
            include_env=self.export_env_var.get(),
            selected_categories=selected_categories if selected_categories else None
        )
        
        # 显示结果
        self.export_result_text.delete(1.0, tk.END)
        
        if result['success']:
            self.export_result_text.insert(tk.END, f"✓ 导出成功!\n\n", 'success')
            self.export_result_text.insert(tk.END, f"导出文件: {result['exported_file']}\n\n")
            self.export_result_text.insert(tk.END, "导出统计:\n")
            
            for key, count in result['stats'].items():
                category_name = self.migration.DATA_CATEGORIES.get(key, key)
                self.export_result_text.insert(tk.END, f"  - {category_name}: {count} 条\n")
            
            self.export_result_text.tag_config('success', foreground='green')
            
            messagebox.showinfo("成功", f"设定已成功导出到:\n{result['exported_file']}")
        else:
            self.export_result_text.insert(tk.END, f"✗ {result['message']}\n", 'error')
            self.export_result_text.tag_config('error', foreground='red')
            
            messagebox.showerror("错误", result['message'])
    
    def _select_import_file(self):
        """选择导入文件"""
        file_path = filedialog.askopenfilename(
            title="选择导入文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.import_file_var.set(file_path)
    
    def _preview_import(self):
        """预览导入内容"""
        file_path = self.import_file_var.get()
        
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("警告", "请先选择有效的导入文件")
            return
        
        # 预览导入内容
        preview = self.migration.preview_import(file_path)
        
        self.import_result_text.delete(1.0, tk.END)
        
        if preview['success']:
            self.import_result_text.insert(tk.END, "=== 导入文件预览 ===\n\n", 'title')
            
            # 显示导出信息
            export_info = preview['export_info']
            if export_info:
                self.import_result_text.insert(tk.END, "导出信息:\n")
                self.import_result_text.insert(tk.END, f"  版本: {export_info.get('version', '未知')}\n")
                self.import_result_text.insert(tk.END, f"  导出时间: {export_info.get('exported_at', '未知')}\n")
                self.import_result_text.insert(tk.END, f"  智能体名称: {export_info.get('agent_name', '未知')}\n\n")
            
            # 显示环境变量统计
            if preview['env_settings_count'] > 0:
                self.import_result_text.insert(tk.END, f"环境变量: {preview['env_settings_count']} 项\n\n")
            
            # 显示数据类别统计
            if preview['categories']:
                self.import_result_text.insert(tk.END, "数据类别:\n")
                for category_key, info in preview['categories'].items():
                    self.import_result_text.insert(
                        tk.END,
                        f"  - {info['name']}: {info['count']} 条\n"
                    )
            
            self.import_result_text.tag_config('title', font=('微软雅黑', 10, 'bold'))
            
            messagebox.showinfo("预览", "导入文件预览已显示在下方结果区域")
        else:
            self.import_result_text.insert(tk.END, f"✗ {preview['message']}\n", 'error')
            self.import_result_text.tag_config('error', foreground='red')
            
            messagebox.showerror("错误", preview['message'])
    
    def _do_import(self):
        """执行导入"""
        file_path = self.import_file_var.get()
        
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("警告", "请先选择有效的导入文件")
            return
        
        # 获取选中的类别
        selected_categories = [
            key for key, var in self.import_category_vars.items() if var.get()
        ]
        
        if not selected_categories and not self.import_env_var.get():
            messagebox.showwarning("警告", "请至少选择一项要导入的内容")
            return
        
        # 确认导入
        overwrite = self.overwrite_var.get()
        message = "确定要导入设定吗？"
        if overwrite:
            message += "\n\n警告: 您选择了覆盖现有数据，这将删除现有的数据！"
        
        if not messagebox.askyesno("确认导入", message):
            return
        
        # 显示进度
        self.import_result_text.delete(1.0, tk.END)
        self.import_result_text.insert(tk.END, "正在导入...\n")
        self.window.update()
        
        # 执行导入
        result = self.migration.import_settings(
            import_path=file_path,
            import_env=self.import_env_var.get(),
            import_database=True,
            overwrite=overwrite,
            selected_categories=selected_categories if selected_categories else None
        )
        
        # 显示结果
        self.import_result_text.delete(1.0, tk.END)
        
        if result['success']:
            self.import_result_text.insert(tk.END, f"✓ 导入成功!\n\n", 'success')
            
            if 'backup_env' in result:
                self.import_result_text.insert(
                    tk.END,
                    f"原 .env 已备份到: {result['backup_env']}\n\n"
                )
            
            self.import_result_text.insert(tk.END, "导入统计:\n")
            
            for key, count in result['stats'].items():
                category_name = self.migration.DATA_CATEGORIES.get(key, key)
                self.import_result_text.insert(tk.END, f"  - {category_name}: {count} 条\n")
            
            self.import_result_text.tag_config('success', foreground='green')
            
            messagebox.showinfo("成功", "设定已成功导入！\n\n如果导入了 .env 配置，请重启应用以使新配置生效。")
        else:
            self.import_result_text.insert(tk.END, f"✗ {result['message']}\n", 'error')
            self.import_result_text.tag_config('error', foreground='red')
            
            messagebox.showerror("错误", result['message'])
    
    def run(self):
        """运行GUI（独立窗口模式）"""
        if not self.parent:
            self.window.mainloop()


def main():
    """主函数，用于独立运行"""
    gui = SettingsMigrationGUI()
    gui.run()


if __name__ == '__main__':
    main()
