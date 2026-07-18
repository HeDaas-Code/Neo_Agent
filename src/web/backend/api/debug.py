"""
Debug REST API Router
- /api/debug/logs: 列表查询（带筛选）
- /api/debug/logs/export: 导出（TXT / JSON）
- /api/debug/logs/clear: 清空内存日志（Stage B.5 扩展）
- /api/debug/stats: 日志统计

Stage B.5: 与 /ws/debug 互补（WS 实时流，REST 历史筛选/导出）。

实现要点：
- 调用 DebugLogger.get_buffer() 读取历史日志；不破坏现有方法签名
- 失败路径返回空结构（不抛 5xx），与 ws 实时流不冲突
- 导出用 StreamingResponse 返回 text/plain 或 application/json
"""

from __future__ import annotations

import io
import json
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def get_buffer(self, *a, **kw): return []
            def get_logs(self, *a, **kw): return []
            def get_statistics(self): return {'total_logs': 0, 'by_type': {}, 'debug_mode': False, 'log_file': ''}
            def clear_logs(self): pass
        return _Stub()

# 兼容：当 DebugLogger 没有 get_buffer 时回退到 get_logs（不破坏现有接口）
def _read_buffer(
    module: Optional[str],
    level: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    logger = get_debug_logger()
    try:
        if hasattr(logger, "get_buffer"):
            buf = logger.get_buffer(
                module=module,
                level=level,
                start=start,
                end=end,
                limit=limit,
            )
            return list(buf or [])
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"[debug_api] get_buffer 失败: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
    # 降级：使用 get_logs + 内存端过滤
    try:
        raw = logger.get_logs(module_name=module, limit=max(limit, 1000)) or []
    except Exception:
        return []
    lvl = (level or "").strip().lower() or None
    out: List[Dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        if lvl and str(entry.get("type", "")).lower() != lvl:
            continue
        ts = entry.get("timestamp")
        if isinstance(ts, str):
            if start and ts < start:
                continue
            if end and ts > end:
                continue
        out.append(entry)
    if len(out) > limit:
        out = out[-limit:]
    return out


def _normalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """把 DebugLogger 内部字段映射到 DebugLogEntry 标准结构。"""
    if not isinstance(entry, dict):
        return {
            "timestamp": "",
            "module": "",
            "level": "INFO",
            "message": "",
            "extra": None,
        }
    level = str(entry.get("type") or entry.get("level") or "INFO").upper()
    module = str(entry.get("module") or "")
    timestamp = str(entry.get("timestamp") or "")

    # 聚合 message 字段（不同 log_* 入口字段名不一样）
    message = entry.get("message")
    if not message:
        # 兼容 log_module / log_request / log_response / log_prompt / log_error
        if "action" in entry:
            message = str(entry.get("action") or "")
            details = entry.get("details")
            if details:
                message = f"{message} | {details}" if message else str(details)
        elif "api_url" in entry:
            message = f"{entry.get('api_url', '')}"
        elif "content" in entry:
            message = str(entry.get("content") or "")
        else:
            message = ""

    # 额外字段（避免结构化信息丢失）
    extra: Optional[Dict[str, Any]] = None
    for k in (
        "action",
        "details",
        "api_url",
        "payload",
        "headers",
        "status_code",
        "elapsed_time",
        "response",
        "exception",
        "file_info",
        "traceback",
        "data",
        "prompt_type",
        "metadata",
    ):
        if k in entry and entry[k] is not None:
            extra = extra or {}
            try:
                json.dumps(entry[k])
                extra[k] = entry[k]
            except (TypeError, ValueError):
                extra[k] = str(entry[k])

    return {
        "timestamp": timestamp,
        "module": module,
        "level": level,
        "message": str(message or ""),
        "extra": extra,
    }


router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/logs")
async def list_debug_logs(
    module: Optional[str] = Query(default=None, description="按模块名精确匹配"),
    level: Optional[str] = Query(default=None, description="按日志级别筛选（INFO/WARN/ERROR/MODULE/...）"),
    start: Optional[str] = Query(default=None, description="起始时间（ISO 8601）"),
    end: Optional[str] = Query(default=None, description="结束时间（ISO 8601）"),
    limit: int = Query(default=200, ge=1, le=2000, description="返回条数上限"),
) -> dict:
    """
    从 DebugLogger 内存缓冲读取历史日志。
    返回 {logs: [...], total: int}。
    失败路径：返回空列表（不抛 5xx）。
    """
    try:
        raw = _read_buffer(module, level, start, end, limit)
        logs = [_normalize_entry(e) for e in raw]
        return {"logs": logs, "total": len(logs)}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"[debug_api] list_debug_logs 失败: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return {"logs": [], "total": 0}


@router.get("/logs/export")
async def export_debug_logs(
    format: str = Query(default="txt", pattern="^(txt|json)$"),
    module: Optional[str] = Query(default=None),
    level: Optional[str] = Query(default=None),
    start: Optional[str] = Query(default=None),
    end: Optional[str] = Query(default=None),
    limit: int = Query(default=2000, ge=1, le=10000),
) -> StreamingResponse:
    """
    导出筛选后的日志为 TXT 或 JSON。
    """
    try:
        raw = _read_buffer(module, level, start, end, limit)
        normalized = [_normalize_entry(e) for e in raw]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"导出失败: {exc}") from exc

    if format == "json":
        try:
            body = json.dumps(
                {"logs": normalized, "total": len(normalized)},
                ensure_ascii=False,
                indent=2,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=f"JSON 序列化失败: {exc}") from exc
        return StreamingResponse(
            io.BytesIO(body.encode("utf-8")),
            media_type="application/json; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="debug-logs.json"',
            },
        )

    # TXT（默认）
    lines: List[str] = []
    for entry in normalized:
        ts = entry.get("timestamp") or "-"
        lvl = entry.get("level") or "INFO"
        mod = entry.get("module") or "-"
        msg = (entry.get("message") or "").replace("\r", " ").replace("\n", " ")
        lines.append(f"[{ts}] [{lvl}] [{mod}] {msg}")
    body = "\n".join(lines) + "\n"
    return StreamingResponse(
        io.BytesIO(body.encode("utf-8")),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="debug-logs.txt"',
        },
    )


@router.post("/logs/clear")
async def clear_debug_logs() -> dict:
    """
    清空 DebugLogger 内存日志（Stage B.5 扩展）。
    """
    try:
        logger = get_debug_logger()
        if hasattr(logger, "clear_logs"):
            logger.clear_logs()
        return {"status": "ok", "message": "日志已清空"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"清空失败: {exc}") from exc


@router.get("/stats")
async def get_debug_stats() -> dict:
    """
    日志统计（按 type 聚合）。
    失败路径：返回零值结构。
    """
    try:
        logger = get_debug_logger()
        if hasattr(logger, "get_statistics"):
            stats = logger.get_statistics() or {}
            return {
                "total_logs": int(stats.get("total_logs", 0) or 0),
                "by_type": dict(stats.get("by_type", {}) or {}),
                "debug_mode": bool(stats.get("debug_mode", False)),
                "log_file": str(stats.get("log_file", "") or ""),
            }
        # 降级
        raw = _read_buffer(None, None, None, None, 10000)
        by_type: Dict[str, int] = {}
        for e in raw:
            t = str((e or {}).get("type", "UNKNOWN")).upper()
            by_type[t] = by_type.get(t, 0) + 1
        return {"total_logs": len(raw), "by_type": by_type, "debug_mode": False, "log_file": ""}
    except Exception as exc:  # noqa: BLE001
        return {
            "total_logs": 0,
            "by_type": {},
            "debug_mode": False,
            "log_file": "",
            "error": str(exc),
        }


@router.post("/logs/ingest")
async def ingest_frontend_logs(request: Request) -> JSONResponse:
    """
    REST 兜底端点：批量接收前端日志并写入 UnifiedLogger。

    请求体：
        [{"level":"ERROR","module":"frontend","message":"...", ...}, ...]

    返回：
        {"accepted": N, "rejected": M}

    异常返回 200 + error 字段，避免前端上报失败时连锁报错。
    """
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=200,
            content={"accepted": 0, "rejected": 0, "error": f"invalid json: {exc}"},
        )

    if not isinstance(body, list):
        return JSONResponse(
            status_code=200,
            content={"accepted": 0, "rejected": 0, "error": "request body must be a list"},
        )

    # 批量上限
    if len(body) > 200:
        body = body[:200]

    accepted = 0
    rejected = 0
    max_message_length = 8192

    try:
        from src.tools.unified_logger import get_unified_logger
        unified = get_unified_logger()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=200,
            content={"accepted": 0, "rejected": 0, "error": f"logger unavailable: {exc}"},
        )

    level_mapping = {
        "debug": "DEBUG",
        "info": "INFO",
        "log": "INFO",
        "warn": "WARN",
        "warning": "WARN",
        "error": "ERROR",
        "fatal": "FATAL",
        "critical": "FATAL",
    }

    for raw in body:
        if not isinstance(raw, dict):
            rejected += 1
            continue

        level = level_mapping.get(str(raw.get("level")).lower(), str(raw.get("level") or "INFO").upper())
        module = str(raw.get("module") or "frontend")
        message = str(raw.get("message") or "")

        if not module or not message:
            rejected += 1
            continue

        if len(message) > max_message_length:
            message = f"{message[:max_message_length]}...[truncated]"

        extra = raw.get("extra")
        if not isinstance(extra, dict):
            extra = {}
        for key in ("url", "userAgent", "sessionId", "rawLevel"):
            val = raw.get(key)
            if val is not None:
                extra[key] = val

        try:
            unified.log(
                level=level,
                module=module,
                message=message,
                source="frontend",
                trace_id=raw.get("trace_id") or raw.get("sessionId"),
                extra=extra,
            )
            accepted += 1
        except Exception:  # noqa: BLE001
            rejected += 1

    return JSONResponse(status_code=200, content={"accepted": accepted, "rejected": rejected})


__all__ = ["router"]
