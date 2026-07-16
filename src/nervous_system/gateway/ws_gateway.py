"""
WebSocketGateway - WebSocket 外部访问网关骨架。

MVP 阶段仅提供接口和基本连接管理，完整实现后续补充。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from src.nervous_system.gateway.base_gateway import BaseGateway, GatewayRequest, GatewayResponse
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType

logger = logging.getLogger(__name__)


class WebSocketGateway(BaseGateway):
    """
    WebSocket 网关。

    职责：
    - 管理 WebSocket 连接生命周期
    - 将客户端消息转换为 GatewayRequest
    - 通过 CentralRouter 与内部模块通信
    - 将内部事件/响应推送给客户端
    """

    gateway_id = "websocket"

    def __init__(self, router: CentralRouter) -> None:
        self.router = router
        self._connections: Dict[str, Any] = {}

    async def start(self) -> None:
        logger.info("[WebSocketGateway] 已启动")

    async def stop(self) -> None:
        logger.info("[WebSocketGateway] 已停止")

    async def handle(self, request: GatewayRequest) -> GatewayResponse:
        """
        处理一条 WebSocket 消息。

        MVP 阶段将消息转发给 cortex.echo。
        """
        trace_id = request.metadata.get("trace_id") or uuid.uuid4().hex
        user_id = request.metadata.get("user_id") or "default"
        conn_id = request.metadata.get("conn_id") or uuid.uuid4().hex

        packet = Packet(
            trace_id=trace_id,
            source="nervous_system.gateway.websocket",
            target="cortex.echo",
            packet_type=PacketType.REQUEST,
            channel="chat",
            payload=request.body,
            metadata={
                "user_id": user_id,
                "conn_id": conn_id,
            },
        )

        response = await self.router.route(packet)

        if response.is_error():
            return GatewayResponse(
                status_code=500,
                body={
                    "type": "error",
                    "error": response.payload.get("error", "unknown error"),
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

    async def register_connection(self, conn_id: str, websocket: Any) -> None:
        """
        注册一个 WebSocket 连接。
        """
        self._connections[conn_id] = websocket
        logger.debug("[WebSocketGateway] 注册连接: %s", conn_id)

    async def unregister_connection(self, conn_id: str) -> None:
        """
        注销一个 WebSocket 连接。
        """
        self._connections.pop(conn_id, None)
        logger.debug("[WebSocketGateway] 注销连接: %s", conn_id)

    async def push(self, conn_id: str, message: Dict[str, Any]) -> None:
        """
        向指定连接推送消息。
        """
        ws = self._connections.get(conn_id)
        if ws is None:
            logger.warning("[WebSocketGateway] 连接不存在: %s", conn_id)
            return
        try:
            await ws.send_json(message)
        except Exception as exc:
            logger.error("[WebSocketGateway] 推送失败: %s", exc)
