"""
LLMGateway - LLM 外部访问网关。

职责：
- 所有 LLM API 调用的唯一入口
- 负载均衡、重试、熔断（MVP 阶段预留接口）
- Token 计数、成本统计（MVP 阶段预留接口）
- 响应缓存（MVP 阶段预留接口）

v4.0 架构下，内部模块不直接调用 LangChain/OpenAI，而是通过 LLMGateway
向 cortex.llm_core 发送请求。
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType

logger = logging.getLogger(__name__)


class LLMGateway(BaseModule):
    """
    LLM 网关模块。

    既是一个 BaseModule（可被 CentralRouter 管理），
    也对外提供简化的 chat / embed / vision 接口。
    """

    module_id = "nervous_system.gateway.llm"
    module_type = "nervous_system"

    def __init__(self, router: CentralRouter) -> None:
        super().__init__(router)

    async def handle(self, packet: Packet) -> Packet:
        """
        处理来自 Router 的 LLM 请求，转发给 cortex.llm_core。
        """
        if packet.channel in ("llm_chat", "llm_stream", "llm_template", "llm_info"):
            return await self.router.route(Packet(
                trace_id=packet.trace_id,
                source=self.module_id,
                target="cortex.llm_core",
                packet_type=PacketType.REQUEST,
                channel=packet.channel,
                payload=packet.payload,
                metadata=packet.metadata,
            ))

        return Packet.error(packet, f"未知 LLM 通道: {packet.channel}", code="UNKNOWN_LLM_CHANNEL")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        task_type: str = "main",
        trace_id: Optional[str] = None,
    ) -> str:
        """
        同步聊天接口（简化版）。
        """
        response = await self.router.route(Packet(
            trace_id=trace_id or "",
            source=self.module_id,
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="llm_chat",
            payload={"messages": messages, "task_type": task_type},
        ))
        if response.is_error():
            raise RuntimeError(response.payload.get("error", "LLM error"))
        return response.payload.get("content", "")

    async def chat_with_template(
        self,
        template: str,
        variables: Dict[str, Any],
        task_type: str = "main",
        trace_id: Optional[str] = None,
    ) -> str:
        """
        模板聊天接口。
        """
        response = await self.router.route(Packet(
            trace_id=trace_id or "",
            source=self.module_id,
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="llm_template",
            payload={"template": template, "variables": variables, "task_type": task_type},
        ))
        if response.is_error():
            raise RuntimeError(response.payload.get("error", "LLM error"))
        return response.payload.get("content", "")
