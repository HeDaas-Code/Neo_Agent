"""
Events WebSocket Router
- /ws/events：通用事件推送（scheduler_tick / proactive_message / chat_event / message / 通配）
- 通过 EventService.register_websocket_listener 订阅
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.web.backend.ws.manager import manager

try:
    from src.web.backend.services.event_service import get_event_service
except Exception:  # noqa: BLE001
    def get_event_service():
        return None

router = APIRouter()
CHANNEL = "events"


@router.websocket("/ws/events")
async def events_ws(websocket: WebSocket) -> None:
    """
    /ws/events 端点
    - 接受后注册 EventService listener（订阅常见 event types）
    - 把事件原样推送给客户端
    - 断开时自动取消订阅
    """
    try:
        await websocket.accept()
    except Exception:
        return

    conn_id = uuid.uuid4().hex
    try:
        await manager.connect(websocket, conn_id, CHANNEL)
    except Exception:
        pass

    try:
        await manager.send_personal(conn_id, {
            "type": "system", "message": "connected to /ws/events",
        })
    except Exception:
        pass

    unsubscribers = []

    try:
        es = get_event_service()
        if es is not None:
            channels = [
                'scheduler_tick',
                'proactive_message',
                'chat_event',
                'message',
            ]

            for ch in channels:
                async def _make_listener(_ch: str):
                    async def _listener(event_type: str, payload: Dict[str, Any]) -> None:
                        try:
                            await manager.broadcast(CHANNEL, {
                                "type": "event",
                                "channel": _ch,
                                "event_type": event_type,
                                "payload": payload,
                            })
                        except Exception:
                            pass
                    return _listener

                try:
                    listener = await _make_listener(ch)
                    unsub = es.register_websocket_listener(ch, listener)
                    if unsub is not None:
                        unsubscribers.append(unsub)
                except Exception:
                    pass

            # 通配订阅（兜底）
            async def _wildcard_listener(event_type: str, payload: Dict[str, Any]) -> None:
                try:
                    await manager.broadcast(CHANNEL, {
                        "type": "event",
                        "channel": "*",
                        "event_type": event_type,
                        "payload": payload,
                    })
                except Exception:
                    pass

            try:
                unsub = es.register_websocket_listener('*', _wildcard_listener)
                if unsub is not None:
                    unsubscribers.append(unsub)
            except Exception:
                pass
    except Exception:
        pass

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break
            try:
                data = json.loads(raw) if raw else {}
            except Exception:
                data = {"raw": raw}
            if (data.get("type") or "").lower() == "ping":
                try:
                    await manager.send_personal(conn_id, {"type": "pong"})
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        for u in unsubscribers:
            try:
                u()
            except Exception:
                pass
        try:
            manager.disconnect(conn_id)
        except Exception:
            pass


__all__ = ["router", "CHANNEL"]
