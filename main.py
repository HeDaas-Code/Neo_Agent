#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent - Main Entry Point (Compatibility Wrapper)
Neo Agent 主程序入口（兼容层）

自 v4.1 起，统一入口已迁移至 run.py。本文件保留为薄兼容层，
使原有 `python main.py` 调用继续工作，实际逻辑全部委托给 run.py。

用法：
    python main.py
    python main.py --no-dev --no-static          # 纯 API 模式
    python main.py --port 8080 --host 127.0.0.1

等效于：
    python run.py web
    python run.py web --no-dev --no-static
    python run.py web --port 8080 --host 127.0.0.1
"""

import sys

import run


if __name__ == "__main__":
    sys.exit(run.main())
