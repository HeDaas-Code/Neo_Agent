"""
EchoCortex - 大脑皮层的 MVP 模拟模块。

用于验证 CentralRouter + Gateway 的端到端通路。
实际回复会调用 LLMGateway，但 MVP 阶段先用 Echo 逻辑。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


class EchoCortex(BaseModule):
    """
    Echo 皮层模块。

    处理 chat 通道请求，返回一个模拟的 LLM 回复，
    同时展示如何向 hippocampus 请求记忆上下文。
    """

    module_id = "cortex.echo"
    module_type = "cortex"

    def __init__(self, router: "CentralRouter") -> None:
        super().__init__(router)

    async def handle(self, packet: Packet) -> Packet:
        """
        处理 chat 请求。
        """
        user_input = packet.payload.get("content", "")

        # MVP：先尝试获取记忆上下文（如果 hippocampus 存在）
        memory_context = []
        try:
            memory_resp = await self.request(
                target="limbic.hippocampus",
                channel="memory_query",
                payload={"query": user_input, "limit": 3},
                metadata=packet.metadata,
            )
            if not memory_resp.is_error():
                memory_context = memory_resp.payload.get("memories", [])
        except Exception:
            pass

        reply = self._build_reply(user_input, memory_context)

        # 发送记忆存储事件
        await self.emit(
            channel="memory_store",
            payload={
                "role": "user",
                "content": user_input,
                "user_id": packet.metadata.get("user_id", "default"),
            },
        )
        await self.emit(
            channel="memory_store",
            payload={
                "role": "assistant",
                "content": reply,
                "user_id": packet.metadata.get("user_id", "default"),
            },
        )

        return packet.response({
            "role": "assistant",
            "content": reply,
            "model": "echo-cortex-mvp",
            "memory_count": len(memory_context),
        })

    def _build_reply(self, user_input: str, memory_context: list) -> str:
        """
        构造 Echo 回复。
        """
        if not user_input:
            return "你好，我是 Neo。请告诉我你想聊什么？"

        if memory_context:
            return (
                f"【Echo 回复】我收到了你的消息：\"{user_input}\"。\n"
                f"（我回忆起 {len(memory_context)} 条相关记忆）"
            )

        return f"【Echo 回复】我收到了你的消息：\"{user_input}\"。"
