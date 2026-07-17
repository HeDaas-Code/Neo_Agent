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

        v4.0：EchoCortex 作为 cortex 入口，负责：
        1. 查询海马体获取记忆上下文
        2. 组装 system prompt + 记忆 + 用户输入
        3. 通过 LLMGateway 调用真实 LLM
        4. 触发记忆存储事件
        """
        user_input = packet.payload.get("content", "")

        # 1) 查询记忆
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

        # 2) 构造消息
        messages = self._build_messages(user_input, memory_context)

        # 3) 根据配置决定是否调用真实 LLM
        reply = ""
        use_llm = packet.payload.get("use_llm", False)

        if use_llm:
            try:
                llm_resp = await self.request(
                    target="nervous_system.gateway.llm",
                    channel="llm_chat",
                    payload={"messages": messages, "task_type": "main"},
                    metadata=packet.metadata,
                )
                if not llm_resp.is_error():
                    reply = llm_resp.payload.get("content", "")
                else:
                    reply = f"【Echo 降级回复】我收到了你的消息：\"{user_input}\"。（LLM 错误: {llm_resp.payload.get('error')}）"
            except Exception as exc:
                reply = f"【Echo 降级回复】我收到了你的消息：\"{user_input}\"。（LLM 调用失败: {exc}）"

        if not reply:
            reply = self._build_echo_reply(user_input, memory_context)

        # 4) 发送记忆存储事件
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
            "model": "cortex.echo-via-llm_gateway",
            "memory_count": len(memory_context),
        })

    def _build_echo_reply(self, user_input: str, memory_context: list) -> str:
        """
        构造 Echo 回复（不调用真实 LLM）。
        """
        if not user_input:
            return "你好，我是 Neo。请告诉我你想聊什么？"

        if memory_context:
            return (
                f"【Echo 回复】我收到了你的消息：\"{user_input}\"。\n"
                f"（我回忆起 {len(memory_context)} 条相关记忆）"
            )

        return f"【Echo 回复】我收到了你的消息：\"{user_input}\"。"

    def _build_messages(self, user_input: str, memory_context: list) -> list:
        """
        构造发送给 LLM 的消息列表。
        """
        system_prompt = "你是 Neo，一个温暖、聪明的 AI 伴侣。请根据上下文自然回复。"
        messages = [{"role": "system", "content": system_prompt}]

        for mem in memory_context:
            role = mem.get("role", "user")
            content = mem.get("content", "")
            messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_input})
        return messages
