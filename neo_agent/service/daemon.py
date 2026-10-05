"""Neo Agent 守护进程服务"""
import os
import sys
import asyncio
import signal
from pathlib import Path
from aiohttp import web
import json
import logging

from ..storage.disk_store import DiskStore
from ..runtime.role import SingleRoleService
from ..runtime.scene import SceneService
from ..runtime.schedule import ScheduleService
from ..runtime.relationship import RelationshipService, EmotionService
from .rpc_handlers import RPCHandlers


class NeoAgentDaemon:
    """Neo Agent 守护进程"""
    
    def __init__(self, data_dir: str = "~/.neo_agent"):
        self.data_dir = Path(data_dir).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.socket_path = self.data_dir / "agent.sock"
        self.pid_file = self.data_dir / "agent.pid"
        self.log_file = self.data_dir / "agent.log"
        
        self.store: DiskStore = None
        self.services = {}
        self.rpc_handlers: RPCHandlers = None
        
        self.app = None
        self.runner = None
        self.site = None
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("neo_agent.daemon")
    
    async def setup(self):
        """初始化服务"""
        self.logger.info("Initializing Neo Agent daemon...")
        
        # 初始化 DiskStore
        vdisk_path = self.data_dir / "data.vdisk"
        self.logger.info(f"Opening DiskStore at {vdisk_path}")
        self.store = DiskStore.open(str(vdisk_path))
        
        # 初始化各个服务
        self.logger.info("Initializing services...")
        
        self.services["role"] = SingleRoleService(self.store)
        self.services["scene"] = SceneService(self.store)
        self.services["schedule"] = ScheduleService(self.store)
        self.services["relationship"] = RelationshipService(self.store)
        self.services["emotion"] = EmotionService(self.store)
        
        # 初始化角色和场景
        self.logger.info("Initializing character...")
        character = self.services["role"].initialize()
        self.logger.info(f"Character loaded: {character.get('name')}")
        
        self.logger.info("Initializing scene...")
        scene = self.services["scene"].initialize()
        self.logger.info(f"Current scene: {scene.get('location', {}).get('name')}")
        
        # 初始化 RPC 处理器
        self.rpc_handlers = RPCHandlers(self.services)
        
        self.logger.info("Services initialized successfully")
    
    async def handle_rpc(self, request):
        """处理 JSON-RPC 请求"""
        try:
            data = await request.json()
            
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            # 查找处理器方法
            handler_name = method.replace(".", "_")
            handler = getattr(self.rpc_handlers, handler_name, None)
            
            if not handler:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": request_id
                })
            
            # 调用处理器
            result = await handler(params)
            
            return web.json_response({
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            })
        
        except Exception as e:
            self.logger.error(f"RPC error: {e}", exc_info=True)
            return web.json_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": data.get("id") if 'data' in locals() else None
            })
    
    async def start_server(self):
        """启动 HTTP 服务器"""
        self.logger.info("Starting HTTP server...")
        
        # 创建应用
        self.app = web.Application()
        self.app.router.add_post("/rpc", self.handle_rpc)
        
        # 删除旧 socket
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        # 启动服务器
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.UnixSite(self.runner, str(self.socket_path))
        await self.site.start()
        
        self.logger.info(f"Server started on {self.socket_path}")
    
    async def run(self):
        """运行守护进程"""
        # 写入 PID 文件
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        try:
            await self.setup()
            await self.start_server()
            
            self.logger.info("Neo Agent daemon is running")
            
            # 保持运行
            await asyncio.Event().wait()
        
        except Exception as e:
            self.logger.error(f"Daemon error: {e}", exc_info=True)
            raise
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理资源"""
        self.logger.info("Cleaning up...")
        
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()
        
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        if self.pid_file.exists():
            self.pid_file.unlink()
        
        self.logger.info("Cleanup complete")
    
    def handle_signal(self, signum, frame):
        """处理信号"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        sys.exit(0)


async def main():
    """主入口"""
    daemon = NeoAgentDaemon()
    
    # 注册信号处理
    signal.signal(signal.SIGTERM, daemon.handle_signal)
    signal.signal(signal.SIGINT, daemon.handle_signal)
    
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())
