#!/usr/bin/env python3
"""Neo Agent CLI 入口"""
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description="Neo Agent - 虚拟群友 Agentic 系统")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "restart", "tui"],
        help="命令: start(启动服务) | stop(停止服务) | status(查看状态) | restart(重启) | tui(启动TUI)"
    )
    
    args = parser.parse_args()
    
    if args.command == "tui":
        from neo_agent.ui.v2.app import run_tui
        run_tui()
    
    elif args.command == "start":
        print("服务启动功能开发中...")
        print("提示: 当前可使用 'neo-agent tui' 直接启动 TUI（模拟服务模式）")
    
    elif args.command == "stop":
        print("服务停止功能开发中...")
    
    elif args.command == "status":
        print("服务状态检查功能开发中...")
    
    elif args.command == "restart":
        print("服务重启功能开发中...")


if __name__ == "__main__":
    main()
