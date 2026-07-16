"""
``/ws/event`` 端点 — 事件通道
``/ws/event`` endpoint — event channel.

Stage A.2: 骨架实现。
- 接受连接 → 注册到 ``manager`` 的 ``event`` channel。
- 保持长连接；服务端**不主动发送**（事件由 EventManager 异步触发，Stage D 接入）。
- 客户端发送的消息目前仅做 ack 回执。
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .manager import manager


router = APIRouter()


@router.websocket("/ws/event")
async def event_endpoint(websocket: WebSocket) -> None:
    """
    事件通道 WebSocket 端点。
    Event channel WebSocket endpoint.

    协议（Stage A.2 骨架）：
    - 客户端 connect → 服务端发送 ``{"type": "ack", "conn_id": ..., "channel": "event"}``。
    - 服务端**不主动推送**（Stage D 接入 EventManager 后由 ``manager.broadcast("event", ...)`` 驱动）。
    - 客户端发送任意消息 → 服务端回 ``{"type": "ack", "received": true}``。
    """
    await websocket.accept()
    conn_id = uuid.uuid4().hex
    await manager.connect(websocket, conn_id, "event")

    try:
        await websocket.send_json(
            {"type": "ack", "conn_id": conn_id, "channel": "event"}
        )

        while True:
            # 仅做接收 / ack，不主动推送（Stage D 接入）
            await websocket.receive_text()
            await websocket.send_json({"type": "ack", "received": True})

    except WebSocketDisconnect:
        manager.disconnect(conn_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[ws/event] 异常 conn_id={conn_id}: {exc}")
        manager.disconnect(conn_id)
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = ["router"]
