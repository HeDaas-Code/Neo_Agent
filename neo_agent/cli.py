"""Neo Agent 命令行工具"""
import sys
import time
from pathlib import Path

from neo_agent.service.daemon import AgentDaemon



# 加载 .env 文件
from pathlib import Path
import os

_project_root = Path(__file__).parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())

def cmd_start(args):
    """启动服务"""
    daemon = AgentDaemon()
    
    if daemon.is_running():
        print(f"✗ 服务已在运行 (PID: {daemon.get_pid()})")
        return 1
    
    if args.foreground:
        print("⚡ 前台启动服务...")
        daemon.start_foreground()
    else:
        print("⚡ 后台启动服务...")
        daemon.start_daemon()
        
        # 等待启动
        for _ in range(10):
            time.sleep(0.5)
            if daemon.is_running():
                print(f"✓ 服务已启动 (PID: {daemon.get_pid()})")
                print(f"  Socket: {daemon.socket_path}")
                return 0
        
        print("✗ 服务启动失败，检查日志：")
        print(f"  {daemon.log_file}")
        return 1
    
    return 0


def cmd_stop(args):
    """停止服务"""
    daemon = AgentDaemon()
    
    if not daemon.is_running():
        print("✗ 服务未运行")
        return 1
    
    print("⏸ 停止服务...")
    if daemon.shutdown():
        # 等待进程退出
        for _ in range(20):
            time.sleep(0.5)
            if not daemon.is_running():
                print("✓ 服务已停止")
                return 0
        
        print("✗ 服务停止超时")
        return 1
    else:
        return 1


def cmd_restart(args):
    """重启服务"""
    daemon = AgentDaemon()
    
    if daemon.is_running():
        print("⏸ 停止现有服务...")
        daemon.shutdown()
        
        # 等待停止
        for _ in range(20):
            time.sleep(0.5)
            if not daemon.is_running():
                break
        else:
            print("✗ 服务停止超时")
            return 1
    
    print("⚡ 启动服务...")
    daemon.start_daemon()
    
    # 等待启动
    for _ in range(10):
        time.sleep(0.5)
        if daemon.is_running():
            print(f"✓ 服务已重启 (PID: {daemon.get_pid()})")
            return 0
    
    print("✗ 服务启动失败")
    return 1


def cmd_status(args):
    """查看服务状态"""
    daemon = AgentDaemon()
    
    if daemon.is_running():
        print(f"✓ 服务运行中")
        print(f"  PID: {daemon.get_pid()}")
        print(f"  Socket: {daemon.socket_path}")
        print(f"  Log: {daemon.log_file}")
    else:
        print("✗ 服务未运行")
        print(f"  Socket: {daemon.socket_path}")
        print(f"  Log: {daemon.log_file}")
    
    return 0 if daemon.is_running() else 1


def cmd_tui(args):
    """启动 TUI 客户端"""
    from neo_agent.ui.v2 import run_tui
    
    # 检查服务是否运行
    daemon = AgentDaemon()
    if not daemon.is_running():
        print("⚠ 服务未运行，正在启动...")
        daemon.start_daemon()
        
        # 等待启动
        for _ in range(10):
            time.sleep(0.5)
            if daemon.is_running():
                print(f"✓ 服务已启动 (PID: {daemon.get_pid()})")
                break
        else:
            print("✗ 服务启动失败")
            return 1
    
    # 启动 TUI
    run_tui()
    return 0


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog="neo-agent",
        description="Neo Agent - 虚拟群友 Agentic 系统"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # start 命令
    parser_start = subparsers.add_parser("start", help="启动服务")
    parser_start.add_argument(
        "-f", "--foreground",
        action="store_true",
        help="前台运行（用于调试）"
    )
    parser_start.set_defaults(func=cmd_start)
    
    # stop 命令
    parser_stop = subparsers.add_parser("stop", help="停止服务")
    parser_stop.set_defaults(func=cmd_stop)
    
    # restart 命令
    parser_restart = subparsers.add_parser("restart", help="重启服务")
    parser_restart.set_defaults(func=cmd_restart)
    
    # status 命令
    parser_status = subparsers.add_parser("status", help="查看服务状态")
    parser_status.set_defaults(func=cmd_status)
    
    # tui 命令
    parser_tui = subparsers.add_parser("tui", help="启动 TUI 客户端")
    parser_tui.set_defaults(func=cmd_tui)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n已中断")
        return 130
    except Exception as e:
        print(f"✗ 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
