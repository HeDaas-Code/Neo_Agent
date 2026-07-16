#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Main Entry Point
主程序入口

Stage A.5: 启动入口

- 默认 --web：调用 run_web.main() 启动 Web GUI（FastAPI + 可选前端 dev server）
- --tk：启动原 Tkinter GUI（EnhancedChatDebugGUI），不依赖 Web 依赖
- --help：显示 argparse 用法
- 仅使用标准库 argparse（不引入 click/typer 等额外依赖）
"""

import sys
import os
import argparse
from typing import Any

# Add the project root to the Python path
# This ensures imports work whether running from project root or elsewhere
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# ============================================================
# 启动模式分发
# ============================================================

def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description=(
            "Neo Agent 启动器\n"
            "默认模式为 --web（FastAPI 后端），--tk 用于启动原 Tkinter GUI。"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--web', dest='web', action='store_true',
                      help='启动 Web GUI（默认模式，FastAPI 后端）')
    mode.add_argument('--tk', dest='tk', action='store_true',
                      help='启动 Tkinter GUI（开发态/降级方案，不依赖 Web 依赖）')

    parser.add_argument('--port', type=int, default=8000,
                        help='[--web] FastAPI 监听端口（默认 8000）')
    parser.add_argument('--host', default='0.0.0.0',
                        help='[--web] FastAPI 监听地址（默认 0.0.0.0）')
    parser.add_argument('--no-dev', action='store_true',
                        help='[--web] 跳过前端 dev server（生产模式）')
    parser.add_argument('--no-static', action='store_true',
                        help='[--web] 不挂载前端构建产物（纯 API 模式）')
    parser.add_argument('--reload', action='store_true',
                        help='[--web] 启用 uvicorn 代码热重载（仅开发态）')

    args = parser.parse_args()

    # 默认模式为 --web（仅当用户未显式指定任一时）
    if not args.tk and not args.web:
        args.web = True
    return args


def _resolve_mode(args: argparse.Namespace) -> str:
    """根据参数决定启动模式。返回 'tk' 或 'web'。"""
    return 'tk' if args.tk else 'web'


# ============================================================
# Tkinter 模式（保留原 EnhancedChatDebugGUI 启动逻辑）
# ============================================================

def _chat_agent_creatable() -> bool:
    """快速判断 ChatAgent 能否在不实际连接 LLM 的情况下构造。"""
    try:
        from src.core.chat_agent import ChatAgent
        return True
    except Exception:
        return False


def _run_tkinter(args: argparse.Namespace) -> int:
    """原 Tkinter GUI 启动逻辑（封装后保持行为完全一致）。"""
    # Check if we can import required modules before proceeding
    try:
        import tkinter as tk
        from tkinter import ttk
    except ImportError as e:
        print("错误 / Error: Tkinter is not available.")
        print("请确保已安装Python的Tkinter模块。")
        print("Please ensure Python's Tkinter module is installed.")
        print(f"详细错误 / Details: {e}")
        return 1

    # Import the main GUI class
    try:
        from src.gui.gui_enhanced import EnhancedChatDebugGUI
    except ImportError as e:
        print("错误 / Error: Failed to import application modules.")
        print("请确保在项目根目录运行此脚本。")
        print("Please ensure you run this script from the project root directory.")
        print(f"当前目录 / Current directory: {os.getcwd()}")
        print(f"脚本位置 / Script location: {project_root}")
        print(f"详细错误 / Details: {e}")
        import traceback
        traceback.print_exc()
        return 1

    background_scheduler = None
    try:
        # P4: 在 GUI 启动前尝试拉起后台调度（子线程隔离）
        try:
            from src.core.background_scheduler import start_default_scheduler
            from src.core.chat_agent import ChatAgent
            from src.core.database_manager import DatabaseManager
            shared_db = DatabaseManager()
            chat_agent = ChatAgent() if _chat_agent_creatable() else None
            background_scheduler = start_default_scheduler(
                tick_seconds=60,
                life_state=getattr(chat_agent, 'life_state_manager', None),
                dream_diary=getattr(chat_agent, 'dream_diary_manager', None),
                creative_writer=getattr(chat_agent, 'creative_writer', None),
                proactive_engine=getattr(chat_agent, 'proactive_engine', None),
                open_loop_tracker=getattr(chat_agent, 'open_loop_tracker', None),
            )
        except Exception as e:
            print(f"后台调度启动失败（不影响 GUI 启动）: {e}")
            background_scheduler = None

        root = tk.Tk()

        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass

        app = EnhancedChatDebugGUI(root)
        try:
            root.mainloop()
        finally:
            if background_scheduler:
                background_scheduler.stop()
    except Exception as e:
        print(f"启动失败 / Failed to start: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


# ============================================================
# Web 模式（Stage A.5：委托给 run_web.main）
# ============================================================

def _run_web(args: argparse.Namespace) -> int:
    """Web GUI 启动逻辑：直接调用 run_web.main() 并把相关参数透传过去。

    业务逻辑、依赖检查、静态挂载、前端 dev server 管理、优雅关闭
    均由 run_web.main() 负责，本函数仅做参数桥接。
    """
    # 验收 P0 3.3: ENABLE_WEB_GUI 显式校验。
    # 用途：允许运维 / 测试通过环境变量关闭 Web GUI 启动入口，
    #       强制使用 --tk 模式；常用于灰度回滚或 CI 烟囱测试。
    if os.environ.get("ENABLE_WEB_GUI", "true").lower() == "false":
        print("[ERROR] Web GUI 已被 ENABLE_WEB_GUI=false 禁用,请使用 --tk 启动 Tkinter 模式")
        sys.exit(1)

    import run_web

    # run_web 内部使用 argparse 解析自身命令行参数；
    # 此处用 sys.argv 模拟等价命令行，确保 --port/--host/--no-dev 等
    # 通过 main.py 传入的参数在 run_web 中也生效。
    argv_backup = sys.argv[:]
    try:
        forwarded = [os.path.basename(argv_backup[0])]
        if args.host != '0.0.0.0':
            forwarded += ['--host', args.host]
        if args.port != 8000:
            forwarded += ['--port', str(args.port)]
        if args.no_dev:
            forwarded.append('--no-dev')
        if args.no_static:
            forwarded.append('--no-static')
        if args.reload:
            forwarded.append('--reload')
        sys.argv = forwarded
        return run_web.main()
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0
    except Exception as e:
        print(f"[main] Web 模式启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        sys.argv = argv_backup


# ============================================================
# 入口
# ============================================================

def main() -> int:
    """主入口：根据参数分发到 Tkinter / Web 模式。"""
    args = _parse_args()
    mode = _resolve_mode(args)
    print(f'[main] 启动模式: {mode}')

    if mode == 'tk':
        return _run_tkinter(args)
    return _run_web(args)


if __name__ == "__main__":
    sys.exit(main())
