"""JSON-RPC 客户端，连接到 Neo Agent 服务"""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp


class AgentClient:
    """异步 JSON-RPC 客户端"""
    
    def __init__(self, socket_path: Optional[Path] = None):
        self.socket_path = socket_path or Path.home() / ".neo_agent" / "agent.sock"
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._request_id = 0
        self._connected = False
        
    @property
    def connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    async def connect(self, timeout: float = 5.0) -> bool:
        """连接到服务"""
        if self._connected:
            return True
        
        try:
            connector = aiohttp.UnixConnector(path=str(self.socket_path))
            self._session = aiohttp.ClientSession(connector=connector)
            
            # 测试连接
            async with asyncio.timeout(timeout):
                result = await self.call("system.get_status", {})
                self._connected = result is not None
                return self._connected
        except (FileNotFoundError, ConnectionError, TimeoutError, OSError):
            self._connected = False
            if self._session:
                await self._session.close()
                self._session = None
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self._ws:
            await self._ws.close()
            self._ws = None
        
        if self._session:
            await self._session.close()
            self._session = None
        
        self._connected = False
    
    async def call(self, method: str, params: Dict[str, Any], timeout: float = 30.0) -> Any:
        """调用 JSON-RPC 方法"""
        if not self._session:
            raise ConnectionError("Not connected to service")
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._request_id,
        }
        
        try:
            async with asyncio.timeout(timeout):
                async with self._session.post(
                    "http://localhost/rpc",
                    json=request
                ) as response:
                    data = await response.json()
                    
                    if "error" in data:
                        error = data["error"]
                        raise RuntimeError(f"RPC error {error.get('code')}: {error.get('message')}")
                    
                    return data.get("result")
        except asyncio.TimeoutError:
            raise TimeoutError(f"RPC call {method} timed out")
    
    async def subscribe_events(self, on_event):
        """订阅服务事件（WebSocket）"""
        if not self._session:
            raise ConnectionError("Not connected to service")
        
        try:
            self._ws = await self._session.ws_connect("http://localhost/ws")
            
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        event = json.loads(msg.data)
                        await on_event(event)
                    except json.JSONDecodeError:
                        pass
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except Exception:
            pass
        finally:
            if self._ws:
                await self._ws.close()
                self._ws = None
    
    # ========== 便捷方法 ==========
    
    async def send_message(self, text: str) -> Dict[str, Any]:
        """发送消息"""
        return await self.call("session.send_message", {"text": text})
    
    async def get_context(self) -> Dict[str, Any]:
        """获取会话上下文"""
        return await self.call("session.get_context", {})
    
    async def get_character(self) -> Dict[str, Any]:
        """获取角色配置"""
        return await self.call("character.get_profile", {})
    
    async def get_today_itinerary(self) -> list:
        """获取今日行程"""
        return await self.call("schedule.get_today_itinerary", {})
    
    async def get_current_scene(self) -> Dict[str, Any]:
        """获取当前场景"""
        return await self.call("scene.get_current", {})
    
    async def get_scene_pool(self) -> list:
        """获取场景池"""
        return await self.call("scene.list_pool", {})
    
    async def search_memory(self, query: str) -> list:
        """搜索记忆"""
        return await self.call("memory.search", {"query": query})
    
    async def list_relationships(self) -> list:
        """列出所有关系"""
        return await self.call("relationship.list_all", {})
    
    async def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return await self.call("system.get_status", {})
    
    async def set_debug(self, enabled: bool) -> Dict[str, str]:
        """设置调试模式"""
        return await self.call("system.set_debug", {"enabled": enabled})
    
    async def shutdown(self) -> Dict[str, str]:
        """关闭服务"""
        return await self.call("system.shutdown", {})
