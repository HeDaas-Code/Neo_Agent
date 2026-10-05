"""Neo Agent 守护进程：Unix socket 服务器 + JSON-RPC 2.0"""
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from daemon import DaemonContext
from aiohttp import web
from lockfile.pidlockfile import PIDLockFile

from neo_agent.storage import DiskStore
from .events import EventBroadcaster
from .rpc_handlers import RPCHandlers


class AgentDaemon:
    """Neo Agent 守护进程"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".neo_agent"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.socket_path = self.data_dir / "agent.sock"
        self.pid_file = self.data_dir / "agent.pid"
        self.log_file = self.data_dir / "agent.log"
        
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.UnixSite] = None
        
        self.store: Optional[DiskStore] = None
        self.broadcaster: Optional[EventBroadcaster] = None
        self.handlers: Optional[RPCHandlers] = None
        
        self._shutdown_requested = False
        
    def is_running(self) -> bool:
        """检查服务是否在运行"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False
    
    def get_pid(self) -> Optional[int]:
        """获取服务 PID"""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file) as f:
                return int(f.read().strip())
        except (ValueError, FileNotFoundError):
            return None
    
    async def handle_jsonrpc(self, request: web.Request) -> web.Response:
        """处理 JSON-RPC 2.0 请求"""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            }, status=400)
        
        if not isinstance(body, dict):
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": None
            }, status=400)
        
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")
        
        if method == "system.shutdown":
            asyncio.create_task(self._delayed_shutdown())
            return web.json_response({
                "jsonrpc": "2.0",
                "result": {"status": "shutting down"},
                "id": req_id
            })
        
        # 转发到 RPC 处理器
        try:
            result = await self.handlers.handle_rpc_call(method, params)
            return web.json_response({
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": req_id
            }, status=500)
    
    async def _delayed_shutdown(self):
        """延迟关闭（给响应时间）"""
        await asyncio.sleep(0.5)
        self._shutdown_requested = True
    
    def shutdown(self):
        """请求关闭服务"""
        if not self.is_running():
            return False
        
        pid = self.get_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                return False
            
            # 等待进程退出
            for _ in range(20):
                time.sleep(0.5)
                if not self.is_running():
                    return True
            
            # 强制杀死
            try:
                os.kill(pid, signal.SIGKILL)
                time.sleep(0.5)
            except ProcessLookupError:
                pass
        
        return not self.is_running()
    
    async def _cleanup_services(self):
        """清理服务资源"""
        if self.broadcaster:
            await self.broadcaster.stop()
        
        if self.store:
            self.store.close()
    
    async def _setup_services(self):
        """初始化运行时服务"""
        # 初始化 PyVDisk 存储
        vdisk_path = self.data_dir / "data.vdisk"
        self.store = DiskStore.open(str(vdisk_path))
        
        # 初始化事件广播
        self.broadcaster = EventBroadcaster()
        await self.broadcaster.start()
        
        # 初始化 RPC 处理器
        self.handlers = RPCHandlers(self.store, self.broadcaster)
    
    async def _run_server(self):
        """运行 HTTP 服务器"""
        # 设置服务
        await self._setup_services()
        
        # 创建 aiohttp 应用
        self.app = web.Application()
        self.app.router.add_post("/rpc", self.handle_jsonrpc)
        self.app.router.add_get("/ws", self.broadcaster.handle_websocket)
        
        # 清理旧 socket
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        # 启动 Unix socket 服务器
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.UnixSite(self.runner, str(self.socket_path))
        await self.site.start()
        
        print(f"✓ Neo Agent 服务已启动", file=sys.stderr)
        print(f"  Socket: {self.socket_path}", file=sys.stderr)
        
        # 等待关闭信号
        while not self._shutdown_requested:
            await asyncio.sleep(0.5)
        
        print("正在关闭服务...", file=sys.stderr)
        
        # 清理
        await self.runner.cleanup()
        await self._cleanup_services()
        
        if self.socket_path.exists():
            self.socket_path.unlink()
    
    def start_foreground(self):
        """前台启动（用于调试）"""
        def signal_handler(signum, frame):
            print("\nReceived shutdown signal", file=sys.stderr)
            self._shutdown_requested = True
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # 写入 PID
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))
        
        try:
            asyncio.run(self._run_server())
        finally:
            if self.pid_file.exists():
                self.pid_file.unlink()
    
    def start_daemon(self):
        """后台启动（守护进程）"""
        if self.is_running():
            raise RuntimeError("Service is already running")
        
        # **关键修复**：保存当前环境变量，特别是 LLM 配置
        preserved_env = {
            key: value for key, value in os.environ.items()
            if any(key.startswith(prefix) for prefix in [
                'OPENAI_', 'SILICONFLOW_', 'MODEL_', 'PATH', 'HOME', 
                'USER', 'LANG', 'LC_', 'PYTHONPATH'
            ])
        }
        
        # 守护进程上下文
        pidfile = PIDLockFile(str(self.pid_file))
        
        with DaemonContext(
            pidfile=pidfile,
            working_directory=str(self.data_dir),
            stdout=open(self.log_file, "a"),
            stderr=open(self.log_file, "a"),
            # **保留环境变量**
            files_preserve=[],
            # **信号处理**
            signal_map={
                signal.SIGTERM: lambda signum, frame: setattr(self, '_shutdown_requested', True),
                signal.SIGINT: lambda signum, frame: setattr(self, '_shutdown_requested', True),
            }
        ):
            # **恢复环境变量**
            os.environ.update(preserved_env)
            asyncio.run(self._run_server())

    def print_status(self):
        """打印服务状态"""
        if not self.is_running():
            print("Neo Agent 服务未运行")
            return
        
        pid = self.get_pid()
        print(f"Neo Agent 服务正在运行")
        print(f"  PID: {pid}")
        print(f"  Socket: {self.socket_path}")
        print(f"  日志: {self.log_file}")
        
        # 检查 socket 是否可访问
        if self.socket_path.exists():
            print(f"  状态: ✓ Socket 可用")
        else:
            print(f"  状态: ⚠ Socket 文件不存在")
