"""
HTTPGateway - HTTP 外部访问网关。

职责：
- 将外部 HTTP 请求转换为 GatewayRequest
- 将 GatewayRequest 通过 CentralRouter 转发给内部模块
- 将内部模块的 Packet 响应转换为 GatewayResponse
- 统一处理鉴权、限流、日志
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from src.nervous_system.gateway.base_gateway import BaseGateway, GatewayRequest, GatewayResponse
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType

logger = logging.getLogger(__name__)


class HTTPGateway(BaseGateway):
    """
    HTTP 网关。

    在 FastAPI 中使用示例：
        @app.post("/api/v4/chat")
        async def chat_v4(request: Request):
            gateway_request = await http_gateway.parse_request(request)
            response = await http_gateway.handle(gateway_request)
            return JSONResponse(status_code=response.status_code, content=response.body)
    """

    gateway_id = "http"

    def __init__(self, router: CentralRouter) -> None:
        self.router = router

    async def start(self) -> None:
        logger.info("[HTTPGateway] 已启动")

    async def stop(self) -> None:
        logger.info("[HTTPGateway] 已停止")

    async def handle(self, request: GatewayRequest) -> GatewayResponse:
        """
        处理 HTTP 请求。

        当前 MVP 仅支持 /api/v4/chat，转发给 cortex.echo 或 cortex.llm_core。
        """
        trace_id = request.metadata.get("trace_id") or uuid.uuid4().hex
        user_id = request.metadata.get("user_id") or "default"

        packet = Packet(
            trace_id=trace_id,
            source="nervous_system.gateway.http",
            target=self._resolve_target(request.path),
            packet_type=PacketType.REQUEST,
            channel=self._resolve_channel(request.path),
            payload=request.body,
            metadata={
                "user_id": user_id,
                "http_method": request.method,
                "http_path": request.path,
                "query_params": request.query_params,
            },
        )

        response = await self.router.route(packet)

        if response.is_error():
            return GatewayResponse(
                status_code=500,
                body={
                    "error": response.payload.get("error", "unknown error"),
                    "code": response.payload.get("code", "INTERNAL_ERROR"),
                    "trace_id": response.trace_id,
                },
            )

        return GatewayResponse(
            status_code=200,
            body={
                "data": response.payload,
                "trace_id": response.trace_id,
                "metadata": response.metadata,
            },
        )

    async def parse_fastapi_request(self, request) -> GatewayRequest:
        """
        将 FastAPI Request 转换为 GatewayRequest。
        """
        from fastapi import Request

        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        return GatewayRequest(
            method=request.method,
            path=request.url.path,
            headers=dict(request.headers),
            query_params=dict(request.query_params),
            body=body,
            metadata={
                "user_id": request.headers.get("X-User-Id", "default"),
                "trace_id": request.headers.get("X-Trace-Id", ""),
            },
        )

    def _resolve_target(self, path: str) -> str:
        """
        根据路径解析目标模块。MVP 阶段硬编码映射。
        """
        if path.startswith("/api/v4/chat"):
            return "cortex.echo"
        if path.startswith("/api/v4/memory"):
            return "limbic.hippocampus"
        return "cortex.echo"

    def _resolve_channel(self, path: str) -> str:
        """
        根据路径解析业务通道。
        """
        if path.startswith("/api/v4/chat"):
            return "chat"
        if path.startswith("/api/v4/memory"):
            return "memory"
        return "default"
