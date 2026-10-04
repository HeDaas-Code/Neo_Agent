"""WebSocket 事件广播系统"""
import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from aiohttp import web


class EventType(str, Enum):
    """服务事件类型"""
    SCENE_CHANGED = "scene_changed"
    EMOTION_UPDATED = "emotion_updated"
    MESSAGE_RECEIVED = "message_received"
    SCHEDULE_TRIGGERED = "schedule_triggered"
    RELATIONSHIP_CHANGED = "relationship_changed"
    DAILY_ITINERARY_GENERATED = "daily_itinerary_generated"
    SYSTEM_STATUS_CHANGED = "system_status_changed"


@dataclass
class ServiceEvent:
    """服务事件"""
    type: EventType
    timestamp: str
    data: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class EventBroadcaster:
    """WebSocket 事件广播器，支持多客户端订阅"""
    
    def __init__(self):
        self._clients: Set[web.WebSocketResponse] = set()
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._broadcast_task: Optional[asyncio.Task] = None
        self._last_event_time = 0.0
        self._throttle_interval = 0.1  # 最多 10 次/秒

    async def start(self):
        """启动广播任务"""
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self):
        """停止广播任务"""
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

    def add_client(self, ws: web.WebSocketResponse):
        """添加客户端"""
        self._clients.add(ws)

    def remove_client(self, ws: web.WebSocketResponse):
        """移除客户端"""
        self._clients.discard(ws)

    async def emit(self, event: ServiceEvent):
        """发送事件到队列（非阻塞）"""
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            # 队列满时丢弃最旧的事件
            try:
                self._event_queue.get_nowait()
                self._event_queue.put_nowait(event)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    async def _broadcast_loop(self):
        """后台广播循环"""
        while True:
            try:
                event = await self._event_queue.get()
                
                # 节流控制
                now = asyncio.get_event_loop().time()
                elapsed = now - self._last_event_time
                if elapsed < self._throttle_interval:
                    await asyncio.sleep(self._throttle_interval - elapsed)
                
                self._last_event_time = asyncio.get_event_loop().time()
                
                # 广播给所有客户端
                if self._clients:
                    message = json.dumps(event.to_dict())
                    dead_clients = set()
                    
                    for client in self._clients:
                        try:
                            await client.send_str(message)
                        except Exception:
                            dead_clients.add(client)
                    
                    # 清理断开的客户端
                    for client in dead_clients:
                        self.remove_client(client)
                        
            except asyncio.CancelledError:
                break
            except Exception:
                # 记录错误但不中断广播循环
                await asyncio.sleep(0.1)

    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """处理 WebSocket 连接"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.add_client(ws)
        
        try:
            # 发送欢迎消息
            welcome = ServiceEvent(
                type=EventType.SYSTEM_STATUS_CHANGED,
                timestamp=datetime.now().isoformat(),
                data={"status": "connected"}
            )
            await ws.send_str(json.dumps(welcome.to_dict()))
            
            # 保持连接直到客户端断开
            async for msg in ws:
                pass  # 只接收心跳，不处理客户端消息
                
        finally:
            self.remove_client(ws)
            
        return ws
