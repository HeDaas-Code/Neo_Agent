"""
Neo Bridge - Web 后端与新架构 nervous_system 之间的安全桥接层。

本模块允许 Web 后端的 v3 服务在不破坏现有逻辑的前提下，通过 CentralRouter
调用 v4 认知模块（cortex、limbic、prefrontal 等）。

设计要点：
1. 安全导入：不强制初始化 NeoApp，导入失败时所有 helper 静默降级。
2. 单一入口：neo_request() 统一构造 Packet 并通过 CentralRouter 路由。
3. 失败隔离：所有调用都包装在 try/except 中，返回 Packet.error 而不是抛异常。
"""

from __future__ import annotations

from typing import Any, Dict

from src.nervous_system.router.packet import Packet, PacketType


# 全局 NeoApp 引用，由 src.web.backend.main 在 startup 时注入。
_neo_app: Any = None


def set_neo_app(neo_app: Any) -> None:
    """
    注册全局 NeoApp 实例。
    由 main.py 在应用启动时调用。
    """
    global _neo_app
    _neo_app = neo_app


def get_neo_app() -> Any:
    """
    获取当前已注册的全局 NeoApp 实例。
    如果尚未初始化或不可用，返回 None。
    """
    return _neo_app


def get_neo_router() -> Any:
    """
    获取 NeoApp 内部的 CentralRouter。
    如果 NeoApp 不可用，返回 None。
    """
    if _neo_app is None:
        return None
    try:
        return _neo_app.router
    except Exception:  # noqa: BLE001
        return None


async def neo_request(
    target: str,
    channel: str,
    payload: Dict[str, Any],
    metadata: Dict[str, Any] | None = None,
) -> Packet:
    """
    通过 CentralRouter 向指定 v4 模块发送请求并返回响应 Packet。

    Args:
        target: 目标模块 ID，例如 "cortex.llm_core"、"limbic.amygdala"。
        channel: 业务通道，例如 "chat"、"emotion_latest"。
        payload: 业务数据字典。
        metadata: 可选元数据（user_id、trace_id 等）。

    Returns:
        响应 Packet。如果 v4 不可用或路由失败，返回一个 ERROR Packet。
    """
    if _neo_app is None:
        return Packet(
            source="web.backend.neo_bridge",
            target=target,
            packet_type=PacketType.ERROR,
            channel=channel,
            payload={"error": "NeoApp not initialized", "code": "NEOAPP_NOT_READY"},
            metadata=metadata or {},
        )

    router = get_neo_router()
    if router is None:
        return Packet(
            source="web.backend.neo_bridge",
            target=target,
            packet_type=PacketType.ERROR,
            channel=channel,
            payload={"error": "CentralRouter not available", "code": "ROUTER_NOT_READY"},
            metadata=metadata or {},
        )

    packet = Packet(
        source="web.backend",
        target=target,
        packet_type=PacketType.REQUEST,
        channel=channel,
        payload=payload,
        metadata=metadata or {},
    )

    try:
        response = await router.route(packet)
    except Exception as exc:  # noqa: BLE001
        response = Packet.error(packet, str(exc), code="ROUTER_EXCEPTION")

    return response


__all__ = [
    "get_neo_app",
    "get_neo_router",
    "neo_request",
    "set_neo_app",
]
