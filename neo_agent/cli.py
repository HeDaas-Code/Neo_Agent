"""Neo Agent CLI 工具"""
import sys
import subprocess
import time
from pathlib import Path
import signal
import os


DATA_DIR = Path.home() / ".neo_agent"
PID_FILE = DATA_DIR / "agent.pid"
SOCKET_FILE = DATA_DIR / "agent.sock"
LOG_FILE = DATA_DIR / "agent.log"


def get_pid():
    """获取守护进程 PID"""
    if not PID_FILE.exists():
        return None
    
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        
        # 检查进程是否存在
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, OSError):
        return None


def start_daemon(foreground=False):
    """启动守护进程"""
    pid = get_pid()
    if pid:
        print(f"Neo Agent daemon is already running (PID: {pid})")
        return 1
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if foreground:
        # 前台运行
        print("Starting Neo Agent daemon in foreground mode...")
        print(f"Logs: {LOG_FILE}")
        print(f"Socket: {SOCKET_FILE}")
        print("Press Ctrl+C to stop\n")
        
        subprocess.run([
            sys.executable, "-m", "neo_agent.service.agent_daemon"
        ])
    else:
        # 后台运行
        print("Starting Neo Agent daemon...")
        
        with open(LOG_FILE, "a") as log:
            process = subprocess.Popen(
                [sys.executable, "-m", "neo_agent.service.agent_daemon"],
                stdout=log,
                stderr=log,
                start_new_session=True
            )
        
        # 等待启动
        for _ in range(10):
            time.sleep(0.5)
            if SOCKET_FILE.exists():
                print(f"✓ Neo Agent daemon started (PID: {process.pid})")
                print(f"  Socket: {SOCKET_FILE}")
                print(f"  Logs: {LOG_FILE}")
                return 0
        
        print("✗ Failed to start daemon (check logs)")
        return 1
    
    return 0


def stop_daemon():
    """停止守护进程"""
    pid = get_pid()
    if not pid:
        print("Neo Agent daemon is not running")
        return 1
    
    print(f"Stopping Neo Agent daemon (PID: {pid})...")
    
    try:
        os.kill(pid, signal.SIGTERM)
        
        # 等待进程退出
        for _ in range(20):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print("✓ Neo Agent daemon stopped")
                return 0
        
        # 超时，强制杀死
        print("Process did not exit, force killing...")
        os.kill(pid, signal.SIGKILL)
        print("✓ Neo Agent daemon stopped (forced)")
        return 0
    
    except ProcessLookupError:
        print("✓ Neo Agent daemon stopped")
        PID_FILE.unlink(missing_ok=True)
        return 0
    except Exception as e:
        print(f"✗ Failed to stop daemon: {e}")
        return 1


def restart_daemon():
    """重启守护进程"""
    stop_daemon()
    time.sleep(1)
    return start_daemon()


def status_daemon():
    """查看守护进程状态"""
    pid = get_pid()
    
    if pid:
        print(f"Neo Agent daemon is running")
        print(f"  PID: {pid}")
        print(f"  Socket: {SOCKET_FILE}")
        print(f"  Logs: {LOG_FILE}")
        return 0
    else:
        print("Neo Agent daemon is not running")
        return 1


def main():
    """主入口"""
    if len(sys.argv) < 2:
        print("Usage: neo-agent <command>")
        print("\nCommands:")
        print("  start [--foreground]  Start the daemon")
        print("  stop                  Stop the daemon")
        print("  restart               Restart the daemon")
        print("  status                Show daemon status")
        print("  tui                   Launch TUI client")
        return 1
    
    command = sys.argv[1]
    
    if command == "start":
        foreground = "--foreground" in sys.argv
        return start_daemon(foreground)
    elif command == "stop":
        return stop_daemon()
    elif command == "restart":
        return restart_daemon()
    elif command == "status":
        return status_daemon()
    elif command == "tui":
        from neo_agent.ui.v2.app_connected import main as tui_main
        tui_main()
        return 0
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
