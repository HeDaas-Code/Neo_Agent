"""TUI 客户端 - 连接到 Neo Agent 服务"""
import asyncio
import aiohttp
from aiohttp import UnixConnector
from typing import Any, Dict, Optional
import json


class ServiceClient:
    """Neo Agent 服务客户端"""
    
    def __init__(self, socket_path: str = "/home/hedass/.neo_agent/agent.sock"):
        self.socket_path = socket_path
        self.session: Optional[aiohttp.ClientSession] = None
        self._request_id = 0
    
    async def connect(self):
        """连接到服务"""
        connector = UnixConnector(path=self.socket_path)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def disconnect(self):
        """断开连接"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def close(self):
        """关闭客户端（disconnect 的别名）"""
        await self.disconnect()
    
    async def call(self, method: str, params: Dict[str, Any] = None) -> Any:
        """调用 RPC 方法"""
        if not self.session:
            raise RuntimeError("Not connected to service")
        
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._request_id
        }
        
        async with self.session.post("http://localhost/rpc", json=request) as resp:
            result = await resp.json()
            
            if "error" in result:
                raise RuntimeError(f"RPC error: {result['error']}")
            
            return result.get("result")
    
    # === 会话管理 ===
    
    async def send_message(self, text: str) -> Dict[str, Any]:
        """发送消息到 Agent"""
        return await self.call("session.send_message", {"text": text})
    
    async def get_context(self) -> Dict[str, Any]:
        """获取会话上下文"""
        return await self.call("session.get_context")
    
    # === 角色与状态 ===
    
    async def get_character_profile(self) -> Dict[str, Any]:
        """获取角色资料"""
        return await self.call("character.get_profile")
    
    # === 日程与场景 ===
    
    async def get_today_itinerary(self) -> list:
        """获取今日行程"""
        return await self.call("schedule.get_today_itinerary")
    
    async def get_current_scene(self) -> Dict[str, Any]:
        """获取当前场景"""
        return await self.call("scene.get_current")
    
    async def get_scene_pool(self) -> list:
        """获取场景池"""
        return await self.call("scene.list_pool")
    
    # === 记忆与知识 ===
    
    async def search_memory(self, query: str) -> list:
        """搜索记忆"""
        return await self.call("memory.search", {"query": query})
    
    async def query_knowledge(self, topic: str) -> list:
        """查询知识"""
        return await self.call("knowledge.query", {"topic": topic})
    
    # === 关系与情绪 ===
    
    async def get_relationship_status(self, entity: str = "user") -> Dict[str, Any]:
        """获取关系状态"""
        return await self.call("relationship.get_status", {"entity": entity})
    
    async def get_current_emotion(self) -> Dict[str, Any]:
        """获取当前情绪"""
        return await self.call("emotion.get_current")
    
    # === 系统控制 ===
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return await self.call("system.get_status")
    
    async def set_debug_mode(self, enabled: bool) -> bool:
        """设置调试模式"""
        return await self.call("system.set_debug", {"enabled": enabled})
