"""
Pipeline - 路由中间件示例。

提供常用的中间件实现：
- AuditMiddleware: 审计日志
- TraceMiddleware: 追踪链路上的跳数
- AuthMiddleware: 简单访问控制
- TimingMiddleware: 记录模块处理耗时
"""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Callable, Coroutine

from src.nervous_system.router.packet import Packet

logger = logging.getLogger(__name__)

NextHandler = Callable[[Packet], Coroutine[Any, Any, Packet]]
Middleware = Callable[[Packet, NextHandler], Coroutine[Any, Any, Packet]]
StreamNextHandler = Callable[[Packet], AsyncIterator[Packet]]
StreamMiddleware = Callable[[Packet, StreamNextHandler], AsyncIterator[Packet]]


class AuditMiddleware:
    """
    审计中间件：记录每个 Packet 的路由路径。
    """

    name = "audit"

    async def __call__(self, packet: Packet, next_handler: NextHandler) -> Packet:
        logger.info(
            "[Audit] trace=%s %s -> %s type=%s channel=%s",
            packet.trace_id,
            packet.source,
            packet.target,
            packet.packet_type.value,
            packet.channel,
        )
        response = await next_handler(packet)
        logger.info(
            "[Audit] trace=%s response type=%s",
            packet.trace_id,
            response.packet_type.value,
        )
        return response


class TraceMiddleware:
    """
    追踪中间件：记录 Packet 经过的模块跳数。
    """

    name = "trace"

    async def __call__(self, packet: Packet, next_handler: NextHandler) -> Packet:
        packet.metadata.setdefault("hops", []).append({
            "middleware": self.name,
            "timestamp": time.time(),
        })
        response = await next_handler(packet)
        response.metadata.setdefault("hops", []).extend(packet.metadata.get("hops", []))
        return response


class TimingMiddleware:
    """
    耗时中间件：记录每个请求的总处理耗时。
    """

    name = "timing"

    async def __call__(self, packet: Packet, next_handler: NextHandler) -> Packet:
        start = time.time()
        response = await next_handler(packet)
        elapsed_ms = (time.time() - start) * 1000
        response.metadata.setdefault("timings", []).append({
            "middleware": self.name,
            "elapsed_ms": elapsed_ms,
        })
        return response


class AuthMiddleware:
    """
    访问控制中间件：检查 metadata 中是否包含 user_id。

    示例用途：保护敏感模块（如 memory、schedule）不被匿名请求访问。
    """

    name = "auth"

    def __init__(self, protected_targets: list[str] | None = None) -> None:
        self.protected_targets = set(protected_targets or [])

    async def __call__(self, packet: Packet, next_handler: NextHandler) -> Packet:
        if packet.target in self.protected_targets and not packet.metadata.get("user_id"):
            from src.nervous_system.router.packet import PacketType

            return Packet(
                trace_id=packet.trace_id,
                source="nervous_system.auth",
                target=packet.source,
                packet_type=PacketType.ERROR,
                channel=packet.channel,
                payload={"error": "unauthorized", "code": "UNAUTHORIZED"},
                metadata=packet.metadata,
            )
        return await next_handler(packet)


class StreamAuditMiddleware:
    """
    流式审计中间件：记录流式 Packet 的路由路径与结束状态。
    """

    name = "stream_audit"

    async def __call__(self, packet: Packet, next_handler: StreamNextHandler) -> AsyncIterator[Packet]:
        logger.info(
            "[Audit] trace=%s stream %s -> %s type=%s channel=%s",
            packet.trace_id,
            packet.source,
            packet.target,
            packet.packet_type.value,
            packet.channel,
        )
        try:
            async for chunk in next_handler(packet):
                yield chunk
        finally:
            logger.info("[Audit] trace=%s stream ended", packet.trace_id)


class StreamTimingMiddleware:
    """
    流式耗时中间件：记录流式请求的总处理耗时。
    """

    name = "stream_timing"

    async def __call__(self, packet: Packet, next_handler: StreamNextHandler) -> AsyncIterator[Packet]:
        start = time.time()
        async for chunk in next_handler(packet):
            chunk.metadata.setdefault("timings", []).append({
                "middleware": self.name,
                "elapsed_ms": (time.time() - start) * 1000,
            })
            yield chunk
