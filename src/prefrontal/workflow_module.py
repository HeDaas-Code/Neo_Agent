"""
WorkflowModule - 跨模块工作流的神经系统接入层。

将 src.core.cross_module_workflow.ChatWorkflow 包装为 BaseModule，
通过 CentralRouter 对外暴露 chat_workflow 通道，支持同步与流式两种调用方式。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from src.core.cross_module_workflow import ChatWorkflow
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet, PacketType

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


class WorkflowModule(BaseModule):
    """
    工作流模块。

    module_id: prefrontal.workflow
    负责编排多模块协作，提供统一的 chat_workflow 入口。
    """

    module_id = "prefrontal.workflow"
    module_type = "prefrontal"

    def __init__(self, router: "CentralRouter") -> None:
        super().__init__(router)
        self._workflow: ChatWorkflow | None = None

    async def initialize(self) -> None:
        self._workflow = ChatWorkflow(self.router)
        await super().initialize()

    async def shutdown(self) -> None:
        self._workflow = None
        await super().shutdown()

    async def handle(self, packet: Packet) -> Packet:
        """
        同步处理工作流请求。

        Channel:
            - chat_workflow: 收集完整流式结果后统一返回
        """
        channel = packet.channel

        if channel == "chat_workflow":
            return await self._handle_chat_workflow_sync(packet)

        return packet.response({
            "status": "unknown_channel",
            "channel": channel,
        })

    async def handle_stream(self, packet: Packet) -> AsyncIterator[Packet]:
        """
        流式处理工作流请求。

        Channel:
            - chat_workflow: 逐 token 返回 assistant chunk，最后 yield done
        """
        channel = packet.channel

        if channel == "chat_workflow":
            user_input = packet.payload.get("user_input", "")
            user_id = packet.payload.get("user_id", "default")
            session_id = packet.payload.get("session_id")
            context = packet.payload.get("context", {})

            if not user_input:
                yield Packet.error(packet, "user_input required", code="INVALID_REQUEST")
                return

            if self._workflow is None:
                yield Packet.error(packet, "Workflow not initialized", code="NOT_INITIALIZED")
                return

            async for event in self._workflow.run_stream(
                user_input, user_id=user_id, session_id=session_id, context=context
            ):
                event_type = event.get("event")
                if event_type == "chunk":
                    content = event.get("content", "")
                    if content:
                        yield packet.stream_chunk({"role": "assistant", "content": content})
                elif event_type == "done":
                    yield packet.stream_done()
                elif event_type == "workflow_result":
                    # 将工作流结果附加到最后一个 chunk，再补一次 done
                    yield packet.stream_chunk({
                        "role": "assistant",
                        "content": "",
                        "workflow_result": event,
                    })
                    yield packet.stream_done()
            return

        # 其他 channel 委托给 handle 并模拟流式
        response = await self.handle(packet)
        if response.is_error():
            yield response
            return
        yield packet.stream_chunk(response.payload)
        yield packet.stream_done()

    async def _handle_chat_workflow_sync(self, packet: Packet) -> Packet:
        user_input = packet.payload.get("user_input", "")
        user_id = packet.payload.get("user_id", "default")
        session_id = packet.payload.get("session_id")
        context = packet.payload.get("context", {})

        if not user_input:
            return Packet.error(packet, "user_input required", code="INVALID_REQUEST")

        if self._workflow is None:
            return Packet.error(packet, "Workflow not initialized", code="NOT_INITIALIZED")

        chunks: list[str] = []
        workflow_result: dict = {}
        async for event in self._workflow.run_stream(
            user_input, user_id=user_id, session_id=session_id, context=context
        ):
            if event.get("event") == "chunk":
                chunks.append(event.get("content", ""))
            elif event.get("event") == "workflow_result":
                workflow_result = event

        full_content = "".join(chunks)
        return packet.response({
            "role": "assistant",
            "content": full_content,
            "workflow": workflow_result,
        })


__all__ = ["WorkflowModule"]