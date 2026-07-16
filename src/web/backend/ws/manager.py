"""
WebSocket Connection Manager
集中维护所有活跃的 WebSocket 连接（按 channel 分组）。

Stage A.2 兼容（conn_id-based API）：
- active_connections: Dict[conn_id -> WebSocket]
- channels: Dict[channel_name -> Set[conn_id]]
- 已被 event.py / proactive.py 等 Stage A.2 端点使用

Stage D.3 扩展：
- 新增 alias 方法 connect_by_channel / disconnect_by_channel / broadcast_by_channel
  供新端点 (chat/debug/events) 使用
- 新增 connection_count / channels 查询方法
- 单点失败不影响其他连接（try/except 保护）
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def log_info(self, *args, **kwargs): pass
            def log_warn(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        return _Stub()

debug_logger = get_debug_logger()


class ConnectionManager:
    """
    WebSocket 连接管理器（单例友好的纯类）。

    Attributes:
        active_connections: 全局连接表，``conn_id -> WebSocket``。
        channels: 通道索引，``channel_name -> set(conn_id)``。
        _lock: 写操作的轻量锁（仅在 add/remove/broadcast 时短暂使用）。
    """

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.channels: Dict[str, Set[str]] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 注册 / 注销（Stage A.2 API）
    # ------------------------------------------------------------------
    async def connect(self, websocket: WebSocket, conn_id: str, channel: str) -> None:
        """
        注册一条连接（Stage A.2 老 API）。

        调用方需先 ``await websocket.accept()``，本方法不负责 accept。
        """
        self.register_channel(channel)
        async with self._lock:
            self.active_connections[conn_id] = websocket
            self.channels[channel].add(conn_id)
        try:
            debug_logger.log_info('WSManager', f'客户端加入 [{channel}] conn_id={conn_id}')
        except Exception:
            pass

    def disconnect(self, conn_id: str) -> None:
        """
        注销一条连接（同步、幂等）。
        """
        self.active_connections.pop(conn_id, None)
        for ch_name, members in list(self.channels.items()):
            if conn_id in members:
                members.discard(conn_id)

    # ------------------------------------------------------------------
    # Stage D.3: 接受 + 注册一行式
    # ------------------------------------------------------------------
    async def accept_and_connect(self, channel: str, websocket: WebSocket) -> str:
        """
        一步完成 accept + 注册到 channel，返回 conn_id。
        """
        try:
            await websocket.accept()
        except Exception as e:  # noqa: BLE001
            try:
                debug_logger.log_error('WSManager', f'accept 失败: {e}', e)
            except Exception:
                pass
        conn_id = uuid.uuid4().hex
        await self.connect(websocket, conn_id, channel)
        return conn_id

    async def close_and_disconnect(self, channel: str, websocket: WebSocket,
                                    conn_id: Optional[str] = None) -> None:
        """关闭 + 注销。"""
        if conn_id is not None:
            self.disconnect(conn_id)
            return
        # 兜底：反向查 conn_id
        for cid, ws in list(self.active_connections.items()):
            if ws is websocket:
                self.disconnect(cid)
                return

    # ------------------------------------------------------------------
    # 单播
    # ------------------------------------------------------------------
    async def send_personal(self, conn_id: str, message: Any) -> bool:
        """
        向指定 conn_id 发送一条消息（dict / str 均可）。
        """
        ws = self.active_connections.get(conn_id)
        if ws is None:
            return False
        try:
            if isinstance(message, (dict, list)):
                await ws.send_text(json.dumps(message, ensure_ascii=False, default=str))
            elif isinstance(message, str):
                await ws.send_text(message)
            else:
                await ws.send_text(str(message))
            return True
        except Exception as exc:  # noqa: BLE001
            try:
                debug_logger.log_warn('WSManager',
                                      f'send_personal 失败 conn_id={conn_id}: {exc}')
            except Exception:
                pass
            self.disconnect(conn_id)
            return False

    # ------------------------------------------------------------------
    # 广播
    # ------------------------------------------------------------------
    async def broadcast(self, channel: str, message: Any) -> int:
        """
        向指定 channel 内的所有连接广播一条消息。
        返回成功发送的数量。
        """
        if isinstance(message, (dict, list)):
            text = json.dumps(message, ensure_ascii=False, default=str)
        elif isinstance(message, str):
            text = message
        else:
            text = str(message)

        members = list(self.channels.get(channel, set()))
        sent = 0
        for conn_id in members:
            ws = self.active_connections.get(conn_id)
            if ws is None:
                self.channels[channel].discard(conn_id)
                continue
            try:
                await ws.send_text(text)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                try:
                    debug_logger.log_warn('WSManager',
                                          f'broadcast 失败 channel={channel} conn_id={conn_id}: {exc}')
                except Exception:
                    pass
                self.disconnect(conn_id)
        return sent

    async def broadcast_all(self, message: Any) -> int:
        """向所有已注册连接广播一条消息。"""
        if isinstance(message, (dict, list)):
            text = json.dumps(message, ensure_ascii=False, default=str)
        elif isinstance(message, str):
            text = message
        else:
            text = str(message)
        conn_ids = list(self.active_connections.keys())
        sent = 0
        for conn_id in conn_ids:
            ws = self.active_connections.get(conn_id)
            if ws is None:
                continue
            try:
                await ws.send_text(text)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                try:
                    debug_logger.log_warn('WSManager',
                                          f'broadcast_all 失败 conn_id={conn_id}: {exc}')
                except Exception:
                    pass
                self.disconnect(conn_id)
        return sent

    # ------------------------------------------------------------------
    # 通道管理 / 统计
    # ------------------------------------------------------------------
    def register_channel(self, channel: str) -> None:
        """预注册一个通道名（幂等）。"""
        if channel not in self.channels:
            self.channels[channel] = set()

    def get_stats(self) -> dict:
        per_channel: Dict[str, int] = {
            ch: len(members) for ch, members in self.channels.items()
        }
        return {
            "total_connections": len(self.active_connections),
            "channels": per_channel,
        }

    def connection_count(self, channel: Optional[str] = None) -> int:
        """查询连接数。"""
        if channel is None:
            return len(self.active_connections)
        return len(self.channels.get(str(channel), set()))

    def list_channels(self) -> List[str]:
        return list(self.channels.keys())


# 全局单例，方便其他模块直接 import
manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """获取全局 ConnectionManager 单例。"""
    return manager


__all__ = ["ConnectionManager", "manager", "get_connection_manager"]
