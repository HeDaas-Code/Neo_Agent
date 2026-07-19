"""
WebSocketGateway - WebSocket 外部访问网关。

职责：
- 管理 WebSocket 连接生命周期
- 将客户端消息转换为 GatewayRequest
- 通过 CentralRouter 与内部模块通信（支持同步与流式路由）
- 将内部事件/响应推送给客户端
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, AsyncIterator, Dict

from src.nervous_system.gateway.base_gateway import BaseGateway, GatewayRequest, GatewayResponse
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType

logger = logging.getLogger(__name__)


class WebSocketGateway(BaseGateway):
    """
    WebSocket 网关。

    将 /ws/chat 等 WebSocket 消息路由到 CentralRouter，
    并支持流式返回（SSE/WS chunk）。
    """

    gateway_id = "websocket"

    def __init__(self, router: CentralRouter) -> None:
        self.router = router
        self._connections: Dict[str, Any] = {}

    async def start(self) -> None:
        logger.info("[WebSocketGateway] 已启动")

    async def stop(self) -> None:
        self._connections.clear()
        logger.info("[WebSocketGateway] 已停止")

    async def handle(self, request: GatewayRequest) -> GatewayResponse:
        """
        处理一条 WebSocket 消息（同步路径）。

        默认将 /ws/chat 消息转发给 prefrontal.workflow 的 chat_workflow 通道。
        """
        packet = self._build_packet(request)
        response = await self.router.route(packet)

        if response.is_error():
            return GatewayResponse(
                status_code=500,
                body={
                    "type": "error",
                    "error": response.payload.get("error", "unknown error"),
                    "code": response.payload.get("code", "INTERNAL_ERROR"),
                    "trace_id": response.trace_id,
                },
            )

        return GatewayResponse(
            status_code=200,
            body={
                "type": "message",
                "data": response.payload,
                "trace_id": response.trace_id,
            },
        )

    async def handle_stream(
        self,
        request: GatewayRequest,
    ) -> AsyncIterator[Packet]:
        """
        流式处理一条 WebSocket 消息。

        将请求构造为 Packet 后，调用 CentralRouter.route_stream，
        直接 yield 目标模块返回的流式 Packet（chunk / done / error）。
        """
        packet = self._build_packet(request)
        target = self._resolve_target(request.path)
        channel = self._resolve_channel(request.path)
        packet.target = target
        packet.channel = channel

        async for response_packet in self.router.route_stream(packet):
            yield response_packet

    async def register_connection(self, conn_id: str, websocket: Any) -> None:
        """注册一个 WebSocket 连接。"""
        self._connections[conn_id] = websocket
        logger.debug("[WebSocketGateway] 注册连接: %s", conn_id)

    async def unregister_connection(self, conn_id: str) -> None:
        """注销一个 WebSocket 连接。"""
        self._connections.pop(conn_id, None)
        logger.debug("[WebSocketGateway] 注销连接: %s", conn_id)

    async def push(self, conn_id: str, message: Dict[str, Any]) -> None:
        """向指定连接推送消息。"""
        ws = self._connections.get(conn_id)
        if ws is None:
            logger.warning("[WebSocketGateway] 连接不存在: %s", conn_id)
            return
        try:
            await ws.send_json(message)
        except Exception as exc:
            logger.error("[WebSocketGateway] 推送失败: %s", exc)

    def _build_packet(self, request: GatewayRequest) -> Packet:
        """将 GatewayRequest 转换为 CentralRouter 可路由的 Packet。"""
        trace_id = request.metadata.get("trace_id") or uuid.uuid4().hex
        user_id = request.metadata.get("user_id") or "default"
        conn_id = request.metadata.get("conn_id") or uuid.uuid4().hex

        target = self._resolve_target(request.path)
        channel = self._resolve_channel(request.path)

        return Packet(
            trace_id=trace_id,
            source="nervous_system.gateway.websocket",
            target=target,
            packet_type=PacketType.REQUEST,
            channel=channel,
            payload=request.body,
            metadata={
                "user_id": user_id,
                "conn_id": conn_id,
                **request.metadata,
            },
        )

    def _resolve_target(self, path: str) -> str:
        """根据 WebSocket 路径解析目标模块。"""
        if path == "/ws/chat" or path.endswith("/ws/chat"):
            return "prefrontal.workflow"
        return "cortex.llm_core"

    def _resolve_channel(self, path: str) -> str:
        """根据 WebSocket 路径解析业务通道。"""
        if path == "/ws/chat" or path.endswith("/ws/chat"):
            return "chat_workflow"
        return "chat"


__all__ = ["WebSocketGateway"]