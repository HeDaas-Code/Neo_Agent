"""WebSocket 客户端，用于接收服务端事件推送"""
import asyncio
import json
from typing import Callable, Dict, Any, Optional
from aiohttp import ClientSession, WSMsgType


class WebSocketClient:
    """WebSocket 事件监听客户端"""
    
    def __init__(self, url: str = "ws://localhost:8765/ws"):
        self.url = url
        self.session: Optional[ClientSession] = None
        self.ws = None
        self.callbacks: Dict[str, list[Callable]] = {}
        self.running = False
        self._listener_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """连接 WebSocket 服务"""
        if self.session is None:
            self.session = ClientSession()
        
        try:
            self.ws = await self.session.ws_connect(self.url)
            self.running = True
            self._listener_task = asyncio.create_task(self._listen_loop())
            return True
        except Exception as e:
            print(f"WebSocket 连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        self.running = False
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            await self.ws.close()
        
        if self.session:
            await self.session.close()
    
    def on(self, event_type: str, callback: Callable):
        """注册事件回调"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)
    
    def off(self, event_type: str, callback: Callable):
        """移除事件回调"""
        if event_type in self.callbacks:
            self.callbacks[event_type] = [
                cb for cb in self.callbacks[event_type] if cb != callback
            ]
    
    async def _listen_loop(self):
        """监听事件循环"""
        while self.running and self.ws:
            try:
                msg = await self.ws.receive()
                
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    event_type = data.get("type", "")
                    
                    # 触发对应的回调
                    if event_type in self.callbacks:
                        for callback in self.callbacks[event_type]:
                            try:
                                # 如果是协程函数，用 create_task 异步执行
                                if asyncio.iscoroutinefunction(callback):
                                    asyncio.create_task(callback(data))
                                else:
                                    callback(data)
                            except Exception as e:
                                print(f"事件回调错误: {e}")
                
                elif msg.type in (WSMsgType.CLOSED, WSMsgType.ERROR):
                    break
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"WebSocket 监听错误: {e}")
                await asyncio.sleep(1.0)
                break
        
        # 尝试重连
        if self.running:
            await asyncio.sleep(2.0)
            await self.connect()
