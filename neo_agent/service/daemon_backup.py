"""Neo Agent 守护进程：Unix socket 服务器 + JSON-RPC 2.0"""
import asyncio
import json
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import daemon
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
        
        self._shutdown_event = asyncio.Event()
        
    def is_running(self) -> bool:
        """检查服务是否在运行"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # 检查进程是否存在
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            return False
    
    def get_pid(self) -> Optional[int]:
        """获取运行中的服务 PID"""
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
        
        jsonrpc = body.get("jsonrpc")
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")
        
        if jsonrpc != "2.0":
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": req_id
            }, status=400)
        
        if not method:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Method required"},
                "id": req_id
            }, status=400)
        
        try:
            result = await self.handlers.handle_rpc_call(method, params)
            
            # 检查是否是关闭命令
            if method == "system.shutdown":
                asyncio.create_task(self._delayed_shutdown())
            
            return web.json_response({
                "jsonrpc": "2.0",
                "result": result,
                "id": req_id
            })
            
        except ValueError as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": str(e)},
                "id": req_id
            }, status=404)
        except PermissionError as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": req_id
            }, status=403)
        except Exception as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": req_id
            }, status=500)
    
    async def _delayed_shutdown(self):
        """延迟关闭，给响应时间返回"""
        await asyncio.sleep(0.5)
        self._shutdown_event.set()
    
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
    
    async def _cleanup_services(self):
        """清理服务资源"""
        if self.broadcaster:
            await self.broadcaster.stop()
        
        if self.store:
            self.store.close()
    
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
        
        # 等待关闭信号（轮询标志位）
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
        """后台守护进程启动"""
        if self.is_running():
            print(f"Service already running (PID: {self.get_pid()})", file=sys.stderr)
            return False
        
        # 守护进程上下文
        context = daemon.DaemonContext(
            working_directory=str(self.data_dir),
            pidfile=PIDLockFile(str(self.pid_file)),
            stdout=open(self.log_file, "a"),
            stderr=open(self.log_file, "a"),
            signal_map={
                signal.SIGTERM: lambda signum, frame: self._shutdown_event.set(),
                signal.SIGINT: lambda signum, frame: self._shutdown_event.set(),
            }
        )
        
        with context:
            asyncio.run(self._run_server())
        
        return True
    
    def stop(self) -> bool:
        """停止服务"""
        pid = self.get_pid()
        if not pid:
            print("Service is not running", file=sys.stderr)
            return False
        
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent shutdown signal to PID {pid}", file=sys.stderr)
            return True
        except ProcessLookupError:
            print(f"Process {pid} not found", file=sys.stderr)
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False
    
    def status(self) -> Dict[str, Any]:
        """获取服务状态"""
        if self.is_running():
            return {
                "running": True,
                "pid": self.get_pid(),
                "socket": str(self.socket_path),
            }
        else:
            return {
                "running": False,
                "pid": None,
                "socket": str(self.socket_path),
            }
