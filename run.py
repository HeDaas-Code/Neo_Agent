#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Unified Launcher
Neo Agent 统一启动入口

自 v4.1 起，本文件成为项目主要入口点，提供子命令式 CLI：
    python run.py web        # 启动 Web/API（默认）
    python run.py web --no-dev --no-static --port 8080
    python run.py stop       # 停止正在运行的 Neo Agent 进程
    python run.py status     # 查看运行状态
    python run.py logs       # 查看 debug.log 尾部

main.py 保留为薄兼容层，内部调用本模块。
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 复用 run_web 的工具函数与常量
from run_web import (
    C_DIM,
    C_GREEN,
    C_RED,
    C_SUPER,
    PID_FILE,
    PROJECT_ROOT,
    is_process_alive,
    log,
    read_pid_file,
    remove_pid_file,
    run_web_server,
)


def _build_web_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """构建 web 子命令解析器。"""
    parser = subparsers.add_parser(
        "web",
        help="启动 Web/API 服务（默认）",
    )
    parser.add_argument("--port", type=int, default=8000,
                        help="FastAPI 监听端口（默认 8000）")
    parser.add_argument("--host", default="0.0.0.0",
                        help="FastAPI 监听地址（默认 0.0.0.0）")
    parser.add_argument("--no-dev", action="store_true",
                        help="跳过前端 dev server（生产模式）")
    parser.add_argument("--no-static", action="store_true",
                        help="不挂载前端构建产物（纯 API 模式）")
    parser.add_argument("--reload", action="store_true",
                        help="启用 uvicorn 代码热重载（仅开发态）")
    parser.set_defaults(func=cmd_web)
    return parser


def _build_stop_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """构建 stop 子命令解析器。"""
    parser = subparsers.add_parser(
        "stop",
        help="停止正在运行的 Neo Agent 进程",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="跳过 SIGTERM，直接 SIGKILL",
    )
    parser.add_argument(
        "--wait", type=int, default=5,
        help="SIGTERM 后等待秒数（默认 5）",
    )
    parser.set_defaults(func=cmd_stop)
    return parser


def _build_status_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """构建 status 子命令解析器。"""
    parser = subparsers.add_parser(
        "status",
        help="查看 Neo Agent 运行状态",
    )
    parser.set_defaults(func=cmd_status)
    return parser


def _build_logs_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    """构建 logs 子命令解析器。"""
    parser = subparsers.add_parser(
        "logs",
        help="查看 debug.log 尾部",
    )
    parser.add_argument(
        "-n", "--lines", type=int, default=50,
        help="显示最后 N 行（默认 50）",
    )
    parser.add_argument(
        "-f", "--follow", action="store_true",
        help="持续跟踪日志输出",
    )
    parser.set_defaults(func=cmd_logs)
    return parser


def cmd_web(args: argparse.Namespace) -> int:
    """启动 Web/API 服务。"""
    return run_web_server(args)


def _find_child_pids(parent_pid: int) -> List[int]:
    """查找指定 PID 下的子进程（通过 pgrep -P）。"""
    try:
        result = subprocess.run(
            ["pgrep", "-P", str(parent_pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        pids: List[int] = []
        for line in result.stdout.strip().splitlines():
            try:
                pids.append(int(line.strip()))
            except ValueError:
                continue
        return pids
    except Exception:
        return []


def _kill_process(pid: int, sig: int) -> bool:
    """向指定 PID 发送信号。"""
    try:
        os.kill(pid, sig)
        return True
    except (OSError, ProcessLookupError):
        return False


def _terminate_tree(parent_pid: int, force: bool = False, wait: int = 5) -> None:
    """递归终止进程树。"""
    children = _find_child_pids(parent_pid)
    for child_pid in children:
        _terminate_tree(child_pid, force=force, wait=wait)

    if force:
        _kill_process(parent_pid, signal.SIGKILL)
    else:
        _kill_process(parent_pid, signal.SIGTERM)


def _terminate_vite_children(parent_pid: int) -> None:
    """尝试终止 vite/node 子进程。"""
    try:
        result = subprocess.run(
            ["pgrep", "-a", "-P", str(parent_pid)],
            capture_output=True,
            text=True,
            check=False,
        )
        for line in result.stdout.strip().splitlines():
            parts = line.split(None, 1)
            if not parts:
                continue
            try:
                child_pid = int(parts[0])
            except ValueError:
                continue
            cmd = parts[1] if len(parts) > 1 else ""
            if "node" in cmd.lower() or "vite" in cmd.lower():
                _kill_process(child_pid, signal.SIGTERM)
    except Exception:
        pass


def cmd_stop(args: argparse.Namespace) -> int:
    """停止正在运行的 Neo Agent 进程。"""
    data = read_pid_file()
    stopped = False

    if data:
        pid = data.get("pid")
        if pid and is_process_alive(pid):
            log("run", C_SUPER, f"正在停止 Neo Agent (PID {pid})...")
            _terminate_vite_children(pid)
            if args.force:
                _kill_process(pid, signal.SIGKILL)
            else:
                _kill_process(pid, signal.SIGTERM)
                # 等待进程退出
                for _ in range(args.wait):
                    if not is_process_alive(pid):
                        break
                    time.sleep(1)
                if is_process_alive(pid):
                    log("run", C_RED,
                        f"进程未在 {args.wait}s 内退出，强制 kill")
                    _kill_process(pid, signal.SIGKILL)
                    time.sleep(0.5)
            stopped = not is_process_alive(pid)
            if stopped:
                log("run", C_GREEN, "Neo Agent 已停止")
            else:
                log("run", C_RED, f"无法停止 PID {pid}")
        else:
            log("run", C_DIM, f"PID 文件记录的进程 {pid} 已不存在")
            remove_pid_file()
    else:
        log("run", C_DIM, "未找到 PID 文件，尝试按名称查找进程...")

    # 兜底：按名称查找并终止其他可能的遗留进程
    if not stopped:
        patterns = [
            ["pgrep", "-f", "python run.py web"],
            ["pgrep", "-f", "python run_web.py"],
            ["pgrep", "-f", "python main.py"],
        ]
        found: List[int] = []
        for cmd in patterns:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                for line in result.stdout.strip().splitlines():
                    try:
                        found.append(int(line.strip()))
                    except ValueError:
                        continue
            except Exception:
                continue

        # 排除当前进程
        found = [p for p in set(found) if p != os.getpid()]
        if found:
            log("run", C_SUPER,
                f"发现遗留进程: {found}，尝试终止...")
            for pid in found:
                _kill_process(pid, signal.SIGKILL)
            stopped = True
        else:
            log("run", C_DIM, "未发现运行中的 Neo Agent 进程")

    remove_pid_file()
    return 0 if stopped else 1


def cmd_status(args: argparse.Namespace) -> int:
    """查看运行状态。"""
    data = read_pid_file()
    if not data:
        log("run", C_DIM, "未运行（无 PID 文件）")
        return 0

    pid = data.get("pid")
    port = data.get("port")
    started_at = data.get("started_at", "unknown")

    alive = bool(pid) and is_process_alive(pid)
    if alive:
        log("run", C_GREEN,
            f"运行中 | PID: {pid} | 端口: {port} | 启动时间: {started_at}")
    else:
        log("run", C_RED,
            f"未运行 | PID 文件存在但进程 {pid} 已消失 | 启动时间: {started_at}")
        remove_pid_file()
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    """查看 debug.log 尾部。"""
    log_file = PROJECT_ROOT / "debug.log"
    if not log_file.is_file():
        log("run", C_DIM, f"日志文件不存在: {log_file}")
        return 0

    try:
        if args.follow:
            # 使用 tail -f 持续跟踪
            result = subprocess.run(
                ["tail", "-f", "-n", str(args.lines), str(log_file)],
                check=False,
            )
            return result.returncode
        else:
            result = subprocess.run(
                ["tail", "-n", str(args.lines), str(log_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout:
                sys.stdout.write(result.stdout)
            return result.returncode
    except FileNotFoundError:
        log("run", C_RED, "未找到 tail 命令")
        return 1
    except Exception as e:
        log("run", C_RED, f"读取日志失败: {e}")
        return 1


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python run.py",
        description="Neo Agent 统一启动入口",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用子命令")

    _build_web_parser(subparsers)
    _build_stop_parser(subparsers)
    _build_status_parser(subparsers)
    _build_logs_parser(subparsers)

    # 默认子命令为 web
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["web"] + list(argv)

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """主入口：解析子命令并分发。"""
    args = _parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        # 无子命令时默认 web
        args = _parse_args(["web"] + (argv or []))
        func = getattr(args, "func", cmd_web)
    return func(args)


if __name__ == "__main__":
    sys.exit(main())