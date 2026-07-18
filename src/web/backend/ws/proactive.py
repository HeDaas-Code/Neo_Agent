"""
``/ws/proactive`` 端点 — 主动消息通道
``/ws/proactive`` endpoint — proactive message channel.

Stage A.2: 骨架实现（accept + ack）。
Stage D.2: 完善 — 订阅 ``EventService`` 的 ``proactive_message`` 事件，
           包装 payload 为前端约定的格式后广播给客户端。
           - 频率节流：``PROACTIVE_MESSAGE_INTERVAL``（秒）可配置；
             低于阈值的重复消息不上推（前端可配置）。
           - 不修改 ``ProactiveEngine`` 现有逻辑，仅在端点层做节流。
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .manager import manager

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
            def log_info(self, *args, **kwargs): pass
            def log_warn(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        return _Stub()

debug_logger = get_debug_logger()


router = APIRouter()
CHANNEL = "proactive"


# ----------------------------------------------------------------------
# 频率节流配置
# ----------------------------------------------------------------------
def _get_proactive_interval() -> float:
    """
    读取 ``PROACTIVE_MESSAGE_INTERVAL`` 环境变量（秒）。
    解析失败或未设置 → 返回 0（不节流，沿用 ProactiveEngine 自身节流）。
    """
    raw = os.getenv("PROACTIVE_MESSAGE_INTERVAL", "")
    try:
        if raw is None or str(raw).strip() == "":
            return 0.0
        v = float(str(raw).strip())
        return max(0.0, v)
    except (TypeError, ValueError):
        return 0.0


# 进程内节流状态（按 channel 共享即可）
_last_proactive_at: float = 0.0
_PROACTIVE_INTERVAL_SEC: float = _get_proactive_interval()


def _should_throttle() -> bool:
    """
    是否被节流。返回 True 表示应跳过本次上推。
    """
    if _PROACTIVE_INTERVAL_SEC <= 0:
        return False
    now = time.time()
    if (now - _last_proactive_at) < _PROACTIVE_INTERVAL_SEC:
        return True
    return False


def _mark_proactive_pushed() -> None:
    global _last_proactive_at
    _last_proactive_at = time.time()


# ----------------------------------------------------------------------
# Payload 包装
# ----------------------------------------------------------------------
def _wrap_proactive_payload(payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将 EventManager / ProactiveEngine 推送的 payload 包装为前端期望的格式。
    字段：
    - type:        "proactive_message"
    - content:     主动消息文本
    - timestamp:   ISO 8601 时间戳
    - user:        接收用户
    - reason:      想法来源（habit_care / open_loop_recall / creative_share / weather_note）
    - play_sound:  是否播放通知音（默认 True）
    """
    if not isinstance(payload, dict):
        payload = {}
    content = str(payload.get("content") or payload.get("text") or "")
    timestamp = str(payload.get("timestamp") or "")
    user = str(payload.get("user") or "default")
    reason = str(payload.get("reason") or payload.get("source") or "")
    priority = str(payload.get("priority") or "normal")
    return {
        "type": "proactive_message",
        "content": content,
        "timestamp": timestamp,
        "user": user,
        "reason": reason,
        "priority": priority,
        "idea_id": str(payload.get("idea_id") or ""),
        "source": str(payload.get("source") or "ProactiveEngine"),
        "play_sound": bool(payload.get("play_sound", True)),
    }


# ----------------------------------------------------------------------
# 端点
# ----------------------------------------------------------------------
@router.websocket("/ws/proactive")
async def proactive_endpoint(websocket: WebSocket) -> None:
    """
    主动消息通道 WebSocket 端点。

    协议：
    - 客户端 connect → 服务端发送 ``{"type": "ack", "conn_id": ..., "channel": "proactive"}``。
    - 客户端发送任意消息 → 服务端回 ``{"type": "ack", "received": true}``。
    - 主动推送：服务端通过 ``EventService`` 监听 ``proactive_message`` 事件，
      节流检查后包装为前端约定格式并广播。
    """
    await websocket.accept()
    conn_id = uuid.uuid4().hex
    try:
        await manager.connect(websocket, conn_id, CHANNEL)
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.proactive', f'connect 失败: {e}', e)
        except Exception:
            pass

    # Stage D.2: 订阅 proactive_message 事件
    unsubscribers = []
    try:
        es = get_event_service()
        if es is not None:
            async def _listener(event_type: str, payload: Dict[str, Any]) -> None:
                if event_type != "proactive_message":
                    return
                if _should_throttle():
                    try:
                        debug_logger.log_info(
                            'ws.proactive',
                            '主动消息被节流（间隔 < PROACTIVE_MESSAGE_INTERVAL）',
                        )
                    except Exception:
                        pass
                    return
                wrapped = _wrap_proactive_payload(payload)
                try:
                    await manager.broadcast(CHANNEL, wrapped)
                    _mark_proactive_pushed()
                except Exception as e:  # noqa: BLE001
                    try:
                        debug_logger.log_error(
                            'ws.proactive', f'广播失败: {e}', e,
                        )
                    except Exception:
                        pass

            try:
                unsub = es.register_websocket_listener(
                    "proactive_message", _listener,
                )
                if unsub is not None:
                    unsubscribers.append(unsub)
            except Exception as e:  # noqa: BLE001
                try:
                    debug_logger.log_warn(
                        'ws.proactive',
                        f'订阅 proactive_message 失败: {e}',
                    )
                except Exception:
                    pass
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_warn('ws.proactive', f'初始化 listener 失败: {e}')
        except Exception:
            pass

    try:
        await websocket.send_json(
            {"type": "ack", "conn_id": conn_id, "channel": CHANNEL}
        )

        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break
            # 简单 ack
            try:
                await websocket.send_json({"type": "ack", "received": True})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.proactive', f'主循环异常: {exc}', exc)
        except Exception:
            pass
    finally:
        # 取消订阅
        for u in unsubscribers:
            try:
                u()
            except Exception:
                pass
        try:
            manager.disconnect(conn_id)
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass


__all__ = ["router", "CHANNEL"]
