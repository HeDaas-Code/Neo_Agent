#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Web GUI Launcher
Web GUI 一键启动脚本

Stage A.5: 启动入口

行为：
- 单进程模式（默认）：
  * 启动 uvicorn (默认 0.0.0.0:8000)
  * 若 src/web/frontend/dist/ 或 src/web/static/ 存在，则将其作为静态资源挂载：
      /         -> SPA 入口 (index.html, html=True)
      /assets   -> 构建产物 assets 子目录
  * 若不存在：仅以 API 模式启动，提示 "请先 cd src/web/frontend && npm run build"
- 开发模式（ENABLE_FRONTEND_DEV=1）：
  * 上述 uvicorn + 静态挂载
  * 并发启动 npm run dev (Vite dev server :5173)
  * 通过线程读取子进程 stdout，按 tag 着色
- 优雅关闭：捕获 SIGINT / SIGTERM，先停前端 dev server，再停 uvicorn
- 零业务逻辑改动：仅做启动编排，不修改 src/core/* 或 src/web/backend/services/*
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# ============================================================
# 常量
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ANSI 颜色（仅在 TTY + 未设置 NO_COLOR 时启用）
C_RESET = "\033[0m"
C_DIM = "\033[2m"
C_UVICORN = "\033[36m"      # cyan
C_VITE = "\033[35m"         # magenta
C_SUPER = "\033[33m"        # yellow
C_RED = "\033[31m"          # red
C_GREEN = "\033[32m"        # green

# Web 依赖最小集合（用于启动前自检）
REQUIRED_WEB_DEPS = ("fastapi", "uvicorn", "websockets", "pydantic")

# 前端构建产物候选目录（兼容 spec 提到的 dist/ 与 vite.config 实际输出的 static/）
FRONTEND_DIST_CANDIDATES = (
    PROJECT_ROOT / "src" / "web" / "frontend" / "dist",
    PROJECT_ROOT / "src" / "web" / "static",
)

# PID 文件路径
PID_FILE = PROJECT_ROOT / ".neo-agent.pid"


# ============================================================
# 彩色日志
# ============================================================

def _use_color() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def log(tag: str, color: str, message: str) -> None:
    """打印带颜色标签的日志行。"""
    if _use_color():
        sys.stdout.write(f"{color}[{tag}]{C_RESET} {message}\n")
    else:
        sys.stdout.write(f"[{tag}] {message}\n")
    sys.stdout.flush()


# ============================================================
# 依赖与产物自检
# ============================================================

def check_web_dependencies() -> None:
    """启动前自检 Web 依赖；缺失时打印明确错误并退出码 1。"""
    missing: list[str] = []
    for mod in REQUIRED_WEB_DEPS:
        try:
            __import__(mod)
        except Exception as e:  # noqa: BLE001
            missing.append(f"{mod} ({e.__class__.__name__})")

    if missing:
        log("supervisor", C_RED, "Web 依赖缺失，无法启动 Web 模式:")
        for m in missing:
            log("supervisor", C_RED, f"  - {m}")
        log("supervisor", C_RED,
            "请先执行: pip install -r requirements-web.txt")
        sys.exit(1)


def find_frontend_dist() -> Optional[Path]:
    """查找前端构建产物目录；返回 None 表示未构建。"""
    for candidate in FRONTEND_DIST_CANDIDATES:
        if candidate.is_dir() and (candidate / "index.html").is_file():
            return candidate
    return None


# ============================================================
# 静态资源挂载
# ============================================================

def mount_static(app, dist_dir: Path) -> bool:
    """将前端构建产物挂载到 FastAPI app；返回是否成功挂载。"""
    try:
        from fastapi.staticfiles import StaticFiles
    except Exception as e:  # noqa: BLE001
        log("supervisor", C_RED,
            f"无法导入 fastapi.staticfiles: {e}")
        return False

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)),
                  name="frontend-assets")
        log("supervisor", C_SUPER, f"已挂载 /assets -> {assets_dir}")

    # SPA fallback: html=True 自动为未匹配路径返回 index.html
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True),
              name="frontend-spa")
    log("supervisor", C_SUPER, f"已挂载 SPA 静态资源 / -> {dist_dir}")
    return True


# ============================================================
# 前端 dev server 子进程
# ============================================================

def _stream_subprocess_output(proc: subprocess.Popen, tag: str, color: str) -> None:
    """在线程中持续读取子进程 stdout 并以彩色日志转发。"""
    if proc.stdout is None:
        return
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            log(tag, color, line.rstrip())
    except Exception:  # noqa: BLE001
        pass
    finally:
        try:
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
        except Exception:  # noqa: BLE001
            pass


def spawn_frontend_dev(frontend_dir: Path) -> Optional[subprocess.Popen]:
    """启动 Vite dev server (子进程)。返回 Popen 或 None。"""
    if not frontend_dir.is_dir():
        log("supervisor", C_SUPER,
            f"前端目录不存在 {frontend_dir}，跳过 vite dev server")
        return None
    log("supervisor", C_SUPER,
        "启动前端 dev server at http://localhost:5173")
    return subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(frontend_dir),
        env={**os.environ, "BROWSER": "none"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def stop_frontend_dev(frontend_proc: Optional[subprocess.Popen]) -> None:
    """优雅终止前端 dev server 进程。"""
    if frontend_proc is None or frontend_proc.poll() is not None:
        return
    log("supervisor", C_SUPER, "正在停止前端 dev server...")
    try:
        frontend_proc.terminate()
        frontend_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        log("supervisor", C_RED, "前端 dev server 未在 5s 内退出，强制 kill")
        try:
            frontend_proc.kill()
            frontend_proc.wait(timeout=3)
        except Exception as e:  # noqa: BLE001
            log("supervisor", C_RED, f"强制 kill 失败: {e}")
    except Exception as e:  # noqa: BLE001
        log("supervisor", C_RED, f"关闭前端 dev server 失败: {e}")


# ============================================================
# PID 文件管理
# ============================================================

def read_pid_file() -> Optional[dict]:
    """读取 PID 文件，返回 {'pid': int, 'port': int, 'started_at': str} 或 None。"""
    if not PID_FILE.is_file():
        return None
    try:
        import json
        data = json.loads(PID_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "pid" in data:
            return data
    except Exception:
        pass
    return None


def write_pid_file(pid: int, port: int) -> None:
    """写入 PID 文件。"""
    import json
    from datetime import datetime, timezone
    data = {
        "pid": pid,
        "port": port,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        PID_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        log("supervisor", C_RED, f"写入 PID 文件失败: {e}")


def remove_pid_file() -> None:
    """删除 PID 文件。"""
    try:
        if PID_FILE.is_file():
            PID_FILE.unlink()
    except Exception:
        pass


def is_process_alive(pid: int) -> bool:
    """检查进程是否存活。"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ============================================================
# 入口
# ============================================================

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Neo Agent Web GUI 启动器（FastAPI + 可选前端 dev server）"
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
    return parser.parse_args()


def run_web_server(args: argparse.Namespace) -> int:
    """
    启动 Web/API 服务（可被 run.py / main.py 调用）。

    负责 PID 文件管理、前端 dev server 拉起、uvicorn 启动与关闭。
    """
    # 0) 启动前自检
    check_web_dependencies()

    # 1) 延迟导入（在依赖自检通过之后）
    import uvicorn
    from src.web.backend.main import app

    # 2) 决定是否启用前端 dev server
    enable_dev = (
        not args.no_dev
        and os.getenv("ENABLE_FRONTEND_DEV", "0") == "1"
    )

    # 3) 检查并写入 PID 文件
    existing = read_pid_file()
    if existing and is_process_alive(existing.get("pid", -1)):
        log("supervisor", C_RED,
            f"检测到已有 Neo Agent 进程在运行 (PID {existing['pid']}, "
            f"端口 {existing.get('port', '?')})")
        log("supervisor", C_RED,
            "请先执行: python run.py stop")
        return 1
    if existing:
        remove_pid_file()
    write_pid_file(pid=os.getpid(), port=args.port)

    frontend_proc: Optional[subprocess.Popen] = None
    reader_thread: Optional[threading.Thread] = None

    if enable_dev:
        frontend_dir = PROJECT_ROOT / "src" / "web" / "frontend"
        frontend_proc = spawn_frontend_dev(frontend_dir)
        if frontend_proc is not None:
            reader_thread = threading.Thread(
                target=_stream_subprocess_output,
                args=(frontend_proc, "vite", C_VITE),
                daemon=True,
                name="vite-output-reader",
            )
            reader_thread.start()

    # 4) 单进程模式：自动挂载前端构建产物
    if not args.no_static:
        dist_dir = find_frontend_dist()
        if dist_dir is not None:
            mount_static(app, dist_dir)
        else:
            log("supervisor", C_SUPER,
                "未检测到前端构建产物 "
                "(src/web/frontend/dist 或 src/web/static)")
            log("supervisor", C_SUPER,
                "请先执行: cd src/web/frontend && npm run build")
            if not enable_dev:
                log("supervisor", C_DIM,
                    "或设置 ENABLE_FRONTEND_DEV=1 启动 vite dev server")

    # 5) 安装信号处理：SIGINT / SIGTERM 优雅关闭
    shutdown_requested = threading.Event()

    def _signal_handler(signum, _frame):
        if shutdown_requested.is_set():
            return
        shutdown_requested.set()
        log("supervisor", C_SUPER,
            f"收到信号 {signum}，开始优雅关闭...")

    original_sigint = signal.signal(signal.SIGINT, _signal_handler)
    original_sigterm = signal.signal(signal.SIGTERM, _signal_handler)

    # 6) 启动 uvicorn
    uvicorn_config = uvicorn.Config(
        "src.web.backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=None,
    )
    server = uvicorn.Server(uvicorn_config)

    log("supervisor", C_SUPER,
        f"启动 FastAPI at http://{args.host}:{args.port}")
    log("supervisor", C_SUPER,
        f"API 文档: http://{args.host}:{args.port}/docs")

    rc = 0
    try:
        server.run()
    except KeyboardInterrupt:
        log("supervisor", C_SUPER, "收到 KeyboardInterrupt，正在关闭...")
    except Exception as e:  # noqa: BLE001
        log("supervisor", C_RED, f"Web 模式启动失败: {e}")
        import traceback
        traceback.print_exc()
        rc = 1
    finally:
        # 7) 先停前端 dev server，再等 reader 线程退出
        stop_frontend_dev(frontend_proc)
        if reader_thread is not None and reader_thread.is_alive():
            reader_thread.join(timeout=2)
        remove_pid_file()
        # 恢复信号处理
        try:
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)
        except Exception:
            pass

    return rc


def main() -> int:
    """Web GUI 启动主函数。可被 main.py / run.py 调用。"""
    args = _parse_args()
    return run_web_server(args)


if __name__ == "__main__":
    sys.exit(main())
