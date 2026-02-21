#!/usr/bin/env python3
"""
Cognee 智能记忆管理器 - 独立应用
提供 Cognee 记忆管理、世界观构建和日志查看的可视化界面

功能：
1. 🧠 Cognee 记忆管理 - 添加、搜索、查看智能记忆
2. 🌍 世界观构建 - 创建、编辑 Markdown 世界观文件
3. 📋 Cognee 日志 - 查看和分析 Cognee 系统日志

使用方法:
    python cognee_manager.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def setup_huggingface_tokenizer():
    """
    配置 HuggingFace 分词器
    在应用初始化时设置 HuggingFace 环境，替代 tiktoken
    """
    # 1. 处理中国大陆 HuggingFace SSL 问题
    if os.getenv('HF_HUB_DISABLE_SSL_VERIFY', '0') == '1':
        os.environ['CURL_CA_BUNDLE'] = ''
        os.environ['REQUESTS_CA_BUNDLE'] = ''
        print("✓ 已禁用 HuggingFace SSL 验证")
    
    # 2. 设置 HuggingFace 镜像站点（中国大陆加速）
    hf_endpoint = os.getenv('HF_ENDPOINT', '')
    if hf_endpoint:
        os.environ['HF_ENDPOINT'] = hf_endpoint
        print(f"✓ 使用 HuggingFace 镜像: {hf_endpoint}")
    
    # 3. 配置 tokenizer
    embedding_model = os.getenv('COGNEE_EMBEDDING_MODEL', 'BAAI/bge-large-zh-v1.5')
    huggingface_tokenizer = os.getenv('HUGGINGFACE_TOKENIZER', embedding_model)
    os.environ['HUGGINGFACE_TOKENIZER'] = huggingface_tokenizer
    
    # 4. 尝试预加载 HuggingFace tokenizer
    try:
        from transformers import AutoTokenizer
        print(f"✓ HuggingFace transformers 已加载")
        print(f"✓ 使用 tokenizer: {huggingface_tokenizer}")
    except ImportError:
        print("⚠ transformers 未安装，请运行: pip install transformers")


class CogneeManagerApp:
    """
    Cognee 智能记忆管理器应用
    独立的桌面应用，提供完整的 Cognee 管理功能
    """
    
    def __init__(self):
        """初始化应用"""
        # 配置 HuggingFace tokenizer
        setup_huggingface_tokenizer()
        
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("🧠 Cognee 智能记忆管理器")
        self.root.geometry("1200x800")
        
        # 设置图标（如果存在）
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except:
            pass
        
        # 初始化管理器
        self.cognee_manager = None
        self.worldview_builder = None
        
        self._init_managers()
        
        # 创建界面
        self._create_ui()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _init_managers(self):
        """初始化 Cognee 管理器和世界观构建器"""
        try:
            from src.core.cognee_memory import CogneeMemoryManager, get_cognee_manager
            self.cognee_manager = get_cognee_manager()
            print("✓ Cognee 记忆管理器已初始化")
        except ImportError as e:
            print(f"⚠ 无法加载 Cognee 记忆管理器: {e}")
        except Exception as e:
            print(f"⚠ Cognee 记忆管理器初始化失败: {e}")
        
        try:
            from src.core.worldview_builder import WorldviewBuilder
            self.worldview_builder = WorldviewBuilder()
            print("✓ 世界观构建器已初始化")
        except ImportError as e:
            print(f"⚠ 无法加载世界观构建器: {e}")
        except Exception as e:
            print(f"⚠ 世界观构建器初始化失败: {e}")
    
    def _create_ui(self):
        """创建用户界面"""
        # 顶部菜单栏
        self._create_menu()
        
        # 顶部信息栏
        self._create_header()
        
        # 主内容区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 加载 Cognee GUI
        try:
            from src.gui.cognee_gui import CogneeWorldviewManagerGUI
            self.cognee_gui = CogneeWorldviewManagerGUI(
                main_frame, 
                self.cognee_manager, 
                self.worldview_builder
            )
        except ImportError as e:
            self._show_import_error(main_frame, e)
        except Exception as e:
            self._show_error(main_frame, e)
        
        # 底部状态栏
        self._create_status_bar()
    
    def _create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新", command=self._refresh)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="Cognee 文档", command=self._open_cognee_docs)
        help_menu.add_command(label="关于", command=self._show_about)
    
    def _create_header(self):
        """创建顶部信息栏"""
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=5)
        
        # 标题
        title_label = ttk.Label(
            header,
            text="🧠 Cognee 智能记忆管理器",
            font=("微软雅黑", 14, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=5)
        
        # 状态指示器
        self.status_indicator = ttk.Label(
            header,
            text="",
            font=("微软雅黑", 10)
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=5)
        self._update_status_indicator()
    
    def _create_status_bar(self):
        """创建底部状态栏"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = ttk.Label(
            status_frame,
            text="就绪",
            font=("微软雅黑", 9)
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 版本信息
        version_label = ttk.Label(
            status_frame,
            text="Cognee Manager v1.0",
            font=("微软雅黑", 9),
            foreground="gray"
        )
        version_label.pack(side=tk.RIGHT, padx=5)
    
    def _update_status_indicator(self):
        """更新状态指示器"""
        if self.cognee_manager and self.cognee_manager._initialized:
            self.status_indicator.config(
                text="🟢 Cognee 已连接",
                foreground="green"
            )
        else:
            self.status_indicator.config(
                text="🔴 Cognee 未连接",
                foreground="red"
            )
    
    def _show_import_error(self, parent, error):
        """显示导入错误"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="⚠️ 组件加载失败",
            font=("微软雅黑", 14, "bold")
        ).pack(pady=20)
        
        ttk.Label(
            frame,
            text=f"无法加载 Cognee GUI 组件:\n{str(error)}",
            font=("微软雅黑", 10),
            wraplength=500
        ).pack(pady=10)
        
        ttk.Label(
            frame,
            text="请确保已安装所有依赖:\npip install cognee transformers",
            font=("微软雅黑", 10)
        ).pack(pady=10)
    
    def _show_error(self, parent, error):
        """显示一般错误"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="❌ 初始化失败",
            font=("微软雅黑", 14, "bold")
        ).pack(pady=20)
        
        ttk.Label(
            frame,
            text=str(error),
            font=("微软雅黑", 10),
            wraplength=500
        ).pack(pady=10)
    
    def _refresh(self):
        """刷新应用"""
        self._init_managers()
        self._update_status_indicator()
        self.status_label.config(text="已刷新")
    
    def _open_cognee_docs(self):
        """打开 Cognee 文档"""
        import webbrowser
        webbrowser.open("https://docs.cognee.ai/")
    
    def _show_about(self):
        """显示关于对话框"""
        messagebox.showinfo(
            "关于",
            "Cognee 智能记忆管理器\n\n"
            "版本: 1.0\n\n"
            "基于 Cognee 开源知识引擎\n"
            "https://github.com/topoteretes/cognee\n\n"
            "功能:\n"
            "• 🧠 智能记忆管理\n"
            "• 🌍 世界观构建\n"
            "• 📋 日志查看\n"
        )
    
    def _on_close(self):
        """关闭应用"""
        self.root.destroy()
    
    def run(self):
        """运行应用"""
        print("\n" + "=" * 50)
        print("🧠 Cognee 智能记忆管理器已启动")
        print("=" * 50 + "\n")
        self.root.mainloop()


def main():
    """主函数"""
    print("=" * 50)
    print("Cognee 智能记忆管理器")
    print("=" * 50)
    
    # 创建并运行应用
    app = CogneeManagerApp()
    app.run()


if __name__ == '__main__':
    main()
