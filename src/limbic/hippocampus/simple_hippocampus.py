"""
SimpleHippocampus - 海马体的 MVP 实现。

仅保留最近 N 条记忆，用于验证：
- 记忆查询（recall）
- 记忆存储（remember，通过事件订阅）
- 与 Cortex 的跨层通信
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List

from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet, PacketType

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


class SimpleHippocampus(BaseModule):
    """
    简化版海马体。

    用内存中的 defaultdict(list) 按 user_id 存储最近消息，
    最大保留 MAX_MEMORY 条。
    """

    module_id = "limbic.hippocampus"
    module_type = "limbic"
    MAX_MEMORY = 10

    def __init__(self, router: "CentralRouter") -> None:
        super().__init__(router)
        self._memories: Dict[str, List[Dict]] = defaultdict(list)

    async def initialize(self) -> None:
        # 订阅 memory_store 事件
        self.router.subscribe("memory_store", self._on_memory_store)
        await super().initialize()

    async def handle(self, packet: Packet) -> Packet:
        """
        处理 memory_query / memory_store 请求。
        """
        if packet.channel == "memory_query":
            return self._handle_query(packet)
        if packet.channel == "memory_store":
            return self._handle_store(packet)

        return packet.response({"status": "unknown_channel", "channel": packet.channel})

    def _handle_query(self, packet: Packet) -> Packet:
        """
        根据 query 返回相关记忆。MVP 阶段简单返回最近 N 条。
        """
        user_id = packet.metadata.get("user_id", "default")
        limit = packet.payload.get("limit", 3)
        memories = self._memories.get(user_id, [])

        # MVP：简单返回最后 limit 条
        relevant = memories[-limit:] if memories else []

        return packet.response({
            "memories": relevant,
            "total": len(memories),
        })

    def _handle_store(self, packet: Packet) -> Packet:
        """
        同步存储记忆（直接请求方式）。
        """
        self._store(
            user_id=packet.payload.get("user_id", "default"),
            role=packet.payload.get("role", "user"),
            content=packet.payload.get("content", ""),
        )
        return packet.response({"status": "stored"})

    async def _on_memory_store(self, packet: Packet) -> None:
        """
        事件订阅方式存储记忆。
        """
        if packet.channel != "memory_store":
            return
        self._store(
            user_id=packet.payload.get("user_id", "default"),
            role=packet.payload.get("role", "user"),
            content=packet.payload.get("content", ""),
        )

    def _store(self, user_id: str, role: str, content: str) -> None:
        """
        存储一条记忆。
        """
        self._memories[user_id].append({
            "role": role,
            "content": content,
        })
        # 限制容量
        if len(self._memories[user_id]) > self.MAX_MEMORY:
            self._memories[user_id].pop(0)
