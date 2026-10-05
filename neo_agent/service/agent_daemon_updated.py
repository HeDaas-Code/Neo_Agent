"""Neo Agent 守护进程：Unix socket 服务器 + JSON-RPC 2.0 + 后台调度器"""
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
        
        # ✨ 新增：后台调度器
        self.scene_scheduler = None
        self.daily_itinerary = None
        self._background_tasks = []
        
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
        except Exception as exc:
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(exc),
                    "data": {"type": type(exc).__name__}
                },
                "id": req_id
            }, status=500)
    
    async def _delayed_shutdown(self):
        """延迟关闭（允许响应返回）"""
        await asyncio.sleep(0.5)
        self._shutdown_requested = True
    
    async def _setup_services(self):
        """初始化运行时服务"""
        # 初始化 PyVDisk 存储
        vdisk_path = self.data_dir / "data.vdisk"
        self.store = DiskStore.open(str(vdisk_path))
        
        # 初始化事件广播
        self.broadcaster = EventBroadcaster()
        await self.broadcaster.start()
        
        # ✨ 初始化各运行时服务
        from neo_agent.runtime.agent import AgentRuntime
        from neo_agent.runtime.role import SingleRoleService
        from neo_agent.runtime.scene import SceneService
        from neo_agent.runtime.schedule import ScheduleService
        from neo_agent.runtime.relationship import RelationshipService, EmotionService
        
        services = {
            "role": SingleRoleService(self.store),
            "scene": SceneService(self.store),
            "schedule": ScheduleService(self.store),
            "relationship": RelationshipService(self.store),
            "emotion": EmotionService(self.store),
            "agent": AgentRuntime(self.store)  # ✨ 关键：Agent 运行时
        }
        
        # 初始化 RPC 处理器
        self.handlers = RPCHandlers(services)
        
        # ✨ 新增：初始化后台调度器
        await self._setup_schedulers()
    
    async def _setup_schedulers(self):
        """初始化后台调度器"""
        from neo_agent.runtime.scene_scheduler import SceneScheduler
        from neo_agent.runtime.daily_itinerary import DailyItineraryService
        
        # 场景调度器
        self.scene_scheduler = SceneScheduler(self.store)
        await self.scene_scheduler.start()
        print("✓ 场景调度器已启动（每分钟检查场景切换）", file=sys.stderr)
        
        # 每日行程生成器
        self.daily_itinerary = DailyItineraryService(self.store)
        
        # 启动每日检查任务（每小时检查一次，如果今天没生成则生成）
        self._background_tasks.append(
            asyncio.create_task(self._daily_itinerary_worker())
        )
        print("✓ 每日行程生成器已启动（每小时检查）", file=sys.stderr)
    
    async def _daily_itinerary_worker(self):
        """每日行程生成 worker"""
        while not self._shutdown_requested:
            try:
                # 启动时立即检查一次
                if self.daily_itinerary.should_generate_today():
                    print("📅 生成今日行程...", file=sys.stderr)
                    plan = self.daily_itinerary.generate_today_itinerary()
                    count = len(plan.get("schedule_items", []))
                    print(f"✓ 今日行程已生成（{count} 个活动）", file=sys.stderr)
                    
                    # 广播事件
                    if self.broadcaster:
                        await self.broadcaster.broadcast({
                            "type": "itinerary.generated",
                            "date": plan.get("date"),
                            "count": count
                        })
            except Exception as exc:
                print(f"❌ 生成今日行程失败: {exc}", file=sys.stderr)
            
            # 每小时检查一次
            await asyncio.sleep(3600)
    
    async def _cleanup_schedulers(self):
        """清理调度器"""
        if self.scene_scheduler:
            await self.scene_scheduler.stop()
            print("✓ 场景调度器已停止", file=sys.stderr)
        
        # 取消后台任务
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        print("✓ 后台任务已清理", file=sys.stderr)
    
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
        
        # 清理调度器
        await self._cleanup_schedulers()
        
        # 清理
        await self.broadcaster.stop()
        await self.site.stop()
        await self.runner.cleanup()
        
        self.store.close()
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self._shutdown_requested = True
    
    def start(self, daemonize: bool = True):
        """启动守护进程"""
        if self.is_running():
            print("服务已在运行", file=sys.stderr)
            return
        
        if daemonize:
            context = DaemonContext(
                working_directory=str(self.data_dir),
                pidfile=PIDLockFile(str(self.pid_file)),
                stdout=open(self.log_file, "a"),
                stderr=open(self.log_file, "a"),
                signal_map={
                    signal.SIGTERM: self._signal_handler,
                    signal.SIGINT: self._signal_handler,
                }
            )
            
            with context:
                asyncio.run(self._run_server())
        else:
            # 前台模式（用于调试）
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # 写入 PID
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
            
            try:
                asyncio.run(self._run_server())
            finally:
                if self.pid_file.exists():
                    self.pid_file.unlink()
    
    def stop(self):
        """停止守护进程"""
        if not self.is_running():
            print("服务未运行", file=sys.stderr)
            return
        
        pid = self.get_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"已发送停止信号到进程 {pid}", file=sys.stderr)
                
                # 等待进程结束
                for _ in range(30):
                    time.sleep(0.5)
                    if not self.is_running():
                        print("✓ 服务已停止", file=sys.stderr)
                        return
                
                print("服务未能在15秒内停止，强制终止", file=sys.stderr)
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                print("进程不存在", file=sys.stderr)
        
        # 清理 PID 文件
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def status(self):
        """检查服务状态"""
        if self.is_running():
            pid = self.get_pid()
            print(f"✓ 服务运行中 (PID: {pid})", file=sys.stderr)
            print(f"  Socket: {self.socket_path}", file=sys.stderr)
        else:
            print("✗ 服务未运行", file=sys.stderr)
