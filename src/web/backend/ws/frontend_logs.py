"""
Frontend Logs WebSocket Router
- /ws/frontend-logs：接收前端批量日志并写入 UnifiedLogger

Stage v4.1: 前端日志统一采集
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.web.backend.ws.manager import manager

try:
    from src.tools.unified_logger import get_unified_logger
except Exception:  # noqa: BLE001
    def get_unified_logger(*a, **kw):
        class _Stub:
            def log(self, *a, **kw): pass
        return _Stub()

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def log_warn(self, *a, **kw): pass
            def log_error(self, *a, **kw): pass
        return _Stub()

router = APIRouter()
CHANNEL = "frontend-logs"

# 安全限制
MAX_BATCH_SIZE = 50
MAX_MESSAGE_LENGTH = 8192
MAX_LOGS_PER_SECOND = 100


async def _safe_send(ws: WebSocket, payload: Any) -> bool:
    """安全发送 WS 消息，失败不抛异常。"""
    try:
        await ws.send_text(json.dumps(payload, ensure_ascii=False, default=str))
        return True
    except Exception:
        return False


def _truncate_message(message: str, max_length: int = MAX_MESSAGE_LENGTH) -> str:
    """截断过长消息。"""
    if len(message) <= max_length:
        return message
    return f"{message[:max_length]}...[truncated]"


def _normalize_level(level: Any) -> str:
    """标准化日志级别。"""
    mapping = {
        "debug": "DEBUG",
        "info": "INFO",
        "log": "INFO",
        "warn": "WARN",
        "warning": "WARN",
        "error": "ERROR",
        "fatal": "FATAL",
        "critical": "FATAL",
    }
    return mapping.get(str(level).lower(), str(level).upper() if level else "INFO")


def _process_entries(entries: List[Any], session_id: Optional[str] = None) -> Dict[str, int]:
    """
    处理前端日志条目，写入 UnifiedLogger。

    返回 {"accepted": int, "rejected": int}。
    """
    accepted = 0
    rejected = 0
    unified = get_unified_logger()

    if not isinstance(entries, list):
        return {"accepted": 0, "rejected": 0}

    # 单批上限截断
    if len(entries) > MAX_BATCH_SIZE:
        entries = entries[:MAX_BATCH_SIZE]

    for raw in entries:
        if not isinstance(raw, dict):
            rejected += 1
            continue

        level = _normalize_level(raw.get("level"))
        module = str(raw.get("module") or "frontend")
        message = str(raw.get("message") or "")

        if not module or not message:
            rejected += 1
            continue

        message = _truncate_message(message)

        extra = raw.get("extra")
        if not isinstance(extra, dict):
            extra = {}

        # 保留前端上下文到 extra
        for key in ("url", "userAgent", "sessionId", "rawLevel"):
            val = raw.get(key)
            if val is not None:
                extra[key] = val

        trace_id = raw.get("trace_id") or session_id

        try:
            unified.log(
                level=level,
                module=module,
                message=message,
                source="frontend",
                trace_id=trace_id,
                extra=extra,
            )
            accepted += 1
        except Exception:
            rejected += 1

    return {"accepted": accepted, "rejected": rejected}


@router.websocket("/ws/frontend-logs")
async def frontend_logs_ws(websocket: WebSocket) -> None:
    """
    /ws/frontend-logs 端点

    接收消息格式：
        {"type": "logs", "entries": [...]}

    返回确认：
        {"type": "ack", "accepted": N, "rejected": M}

    限流提示：
        {"type": "rate_limited", "message": "..."}
    """
    debug_logger = get_debug_logger()
    conn_id: Optional[str] = None

    try:
        conn_id = await manager.accept_and_connect(CHANNEL, websocket)
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.frontend_logs', f'accept/connect 失败: {e}', e)
        except Exception:
            pass
        return

    # 限流状态
    rate_window_start = time.time()
    rate_count = 0

    try:
        await _safe_send(websocket, {
            "type": "system",
            "message": "connected to /ws/frontend-logs",
        })

        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception:
                break

            if not raw:
                continue

            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                await _safe_send(websocket, {
                    "type": "error",
                    "message": "invalid json",
                })
                continue

            msg_type = str(data.get("type") or "").lower()

            if msg_type == "ping":
                await _safe_send(websocket, {"type": "pong"})
                continue

            if msg_type != "logs":
                await _safe_send(websocket, {
                    "type": "error",
                    "message": "unsupported message type",
                })
                continue

            entries = data.get("entries")
            if not isinstance(entries, list):
                await _safe_send(websocket, {
                    "type": "error",
                    "message": "entries must be a list",
                })
                continue

            # 限流检查
            now = time.time()
            if now - rate_window_start >= 1.0:
                rate_window_start = now
                rate_count = 0

            total_entries = len(entries)
            if rate_count + total_entries > MAX_LOGS_PER_SECOND:
                allowed = max(0, MAX_LOGS_PER_SECOND - rate_count)
                entries = entries[:allowed]
                rate_count = MAX_LOGS_PER_SECOND
                await _safe_send(websocket, {
                    "type": "rate_limited",
                    "message": f"rate limited: max {MAX_LOGS_PER_SECOND} logs/second per connection",
                })
            else:
                rate_count += total_entries

            # 处理日志
            session_id = data.get("sessionId")
            result = _process_entries(entries, session_id=session_id)
            await _safe_send(websocket, {
                "type": "ack",
                **result,
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.frontend_logs', f'处理前端日志失败: {e}', e)
        except Exception:
            pass
    finally:
        if conn_id is not None:
            try:
                manager.disconnect(conn_id)
            except Exception:
                pass


__all__ = ["router", "CHANNEL"]
