"""
Debug WebSocket Router
- /ws/debug：流式调试日志
- Stage D.4: 连接时注册 DebugLogger 订阅者；断开时取消订阅
- 同时也注册一个 EventService listener，把 'debug_log' 事件广播到本 channel
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

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

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            _subscribers = []
            def subscribe(self, *a, **kw): return lambda: None
            def unsubscribe(self, *a, **kw): return False
        return _Stub()

debug_logger = get_debug_logger()
router = APIRouter()
CHANNEL = "debug"


async def _safe_send_personal(conn_id: str, payload: Any) -> bool:
    try:
        return await manager.send_personal(conn_id, payload)
    except Exception:
        return False


@router.websocket("/ws/debug")
async def debug_ws(websocket: WebSocket) -> None:
    """
    /ws/debug 端点
    - 接受连接后，订阅 DebugLogger；每条日志通过 WS 推送给客户端
    - 断开时取消订阅
    - 同时也注册一个 EventService listener，把 'debug_log' 事件广播到本 channel
    """
    try:
        await websocket.accept()
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.debug', f'accept 失败: {e}', e)
        except Exception:
            pass
        return

    conn_id = uuid.uuid4().hex
    try:
        await manager.connect(websocket, conn_id, CHANNEL)
    except Exception:
        pass

    await _safe_send_personal(conn_id, {"type": "system", "message": "connected to /ws/debug"})

    # 订阅 DebugLogger
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)

    def _subscriber(log_entry: Dict[str, Any]) -> None:
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None
            if loop is not None and loop.is_running():
                loop.call_soon_threadsafe(queue.put_nowait, log_entry)
            else:
                queue.put_nowait(log_entry)
        except Exception:
            pass

    unsubscribe = None
    try:
        if hasattr(debug_logger, 'subscribe'):
            unsubscribe = debug_logger.subscribe(_subscriber)
    except Exception:
        unsubscribe = None

    # 注册 EventService listener
    es_unsub = None
    try:
        es = get_event_service()
        if es is not None:
            async def _es_listener(_event_type: str, payload: Dict[str, Any]) -> None:
                try:
                    await manager.broadcast(CHANNEL, {
                        "type": "event",
                        "event_type": _event_type,
                        "payload": payload,
                    })
                except Exception:
                    pass

            es_unsub = es.register_websocket_listener('debug_log', _es_listener)
    except Exception:
        es_unsub = None

    try:
        while True:
            # 使用 asyncio.wait 监听 receive_text 与 queue.get
            receive_task = asyncio.create_task(websocket.receive_text())
            done_event = asyncio.create_task(queue.get())
            try:
                done, _pending = await asyncio.wait(
                    {receive_task, done_event},
                    return_when=asyncio.FIRST_COMPLETED,
                )
            except Exception:
                if not receive_task.done():
                    receive_task.cancel()
                if not done_event.done():
                    done_event.cancel()
                break

            if receive_task in done:
                if not done_event.done():
                    done_event.cancel()
                try:
                    raw = receive_task.result()
                except WebSocketDisconnect:
                    break
                except Exception:
                    raw = None
                if raw is None:
                    break
                try:
                    data = json.loads(raw) if raw else {}
                except Exception:
                    data = {"raw": raw}
                if (data.get("type") or "").lower() == "ping":
                    await _safe_send_personal(conn_id, {"type": "pong"})
                continue

            if done_event in done:
                if not receive_task.done():
                    receive_task.cancel()
                try:
                    log_entry = done_event.result()
                except Exception:
                    log_entry = None
                if log_entry is not None:
                    await _safe_send_personal(conn_id, {
                        "type": "log",
                        "entry": log_entry,
                    })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            if unsubscribe is not None:
                unsubscribe()
        except Exception:
            pass
        try:
            if es_unsub is not None:
                es_unsub()
        except Exception:
            pass
        try:
            manager.disconnect(conn_id)
        except Exception:
            pass


__all__ = ["router", "CHANNEL"]
