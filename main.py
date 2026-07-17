#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Main Entry Point
Neo Agent 主程序入口

自 v4.1 起，原 Tkinter GUI 已移除。本入口固定启动 Web / API 服务
（FastAPI + 可选前端 dev server / 静态资源），参数直接透传给 run_web.py。

用法：
    python main.py
    python main.py --no-dev --no-static          # 纯 API 模式
    python main.py --port 8080 --host 127.0.0.1
"""

import sys
import os
from typing import Any

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _run_web(args: Any) -> int:
    """将参数透传给 run_web.main() 启动 Web / API 服务。"""
    import run_web

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
        print(f"[main] Web/API 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        sys.argv = argv_backup


def main() -> int:
    """主入口：解析参数并启动 Web / API 服务。"""
    import argparse

    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Neo Agent Web / API 启动器（FastAPI 后端）",
    )
    parser.add_argument('--port', type=int, default=8000,
                        help='FastAPI 监听端口（默认 8000）')
    parser.add_argument('--host', default='0.0.0.0',
                        help='FastAPI 监听地址（默认 0.0.0.0）')
    parser.add_argument('--no-dev', action='store_true',
                        help='跳过前端 dev server（生产模式）')
    parser.add_argument('--no-static', action='store_true',
                        help='不挂载前端构建产物（纯 API 模式）')
    parser.add_argument('--reload', action='store_true',
                        help='启用 uvicorn 代码热重载（仅开发态）')

    args = parser.parse_args()
    print('[main] 启动 Web/API 模式')
    return _run_web(args)


if __name__ == "__main__":
    sys.exit(main())