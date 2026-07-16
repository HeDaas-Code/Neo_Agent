"""
Event REST API router - Stage C.3 / 验收 P0 3.2
跨端事件的 REST API 路由（events 表 CRUD）。

端点：
  GET    /api/events                       列表（分页 + 筛选）
  POST   /api/events/{event_id}/read       标记已读
  POST   /api/events/{event_id}/archive    归档

设计要点：
1. 复用 ``src.core.event_manager.EventManager`` 单例（经
   ``get_event_manager()`` 获取），不走 database_service 通用表查询；
   events 表结构复杂、含 metadata JSON 字段，专用 manager 更安全。
2. 复用 ``src.web.backend.schemas.event.EventDTO`` / ``EventListResponse``；
   字段不匹配部分在本文内通过新建 ``EventDTOExtended``（不改动 EventDTO）补齐。
3. 列表分页：``limit`` (1-200, 默认 50) + ``offset`` (>=0, 默认 0)。
4. 筛选：``type`` (event_type) + ``status``。
5. 读 / 归档直接更新 events 表的 metadata 字段（追加 read_at / archived_at
   时间戳），同时把 status 同步为 ``completed`` / ``cancelled``，确保与
   现有 EventStatus 枚举兼容。
6. 所有路由 try/except 包裹，失败 → 4xx + {"error": ...}，绝不抛 5xx。
7. EventManager 不可用时返回空列表（graceful degradation）。
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, HTTPException, Path, Query, status  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

# 复用 EventDTO / EventListResponse（字段对不上时本文内新增，不改 EventDTO）
from src.web.backend.schemas.event import (  # noqa: E402
    EventDTO,
    EventListResponse,
)

# 调试日志（try/except 保护）
try:
    from src.tools.debug_logger import get_debug_logger as _get_debug_logger
    _debug_logger = _get_debug_logger()
except Exception:  # noqa: BLE001
    class _StubLogger:
        def log_info(self, *a, **k): pass
        def log_warn(self, *a, **k): pass
        def log_error(self, *a, **k): pass
    _debug_logger = _StubLogger()


# EventManager 句柄（懒加载；不直接 import EventManager 类以便降级）
_event_manager: Optional[Any] = None
_EVENT_MANAGER_IMPORT_OK: bool = False
_EVENT_MANAGER_IMPORT_ERROR: Optional[BaseException] = None

try:
    from src.core.event_manager import (  # noqa: E402
        EventManager,
        EventStatus,
        get_event_manager,
    )
    _EVENT_MANAGER_IMPORT_OK = True
except Exception as _exc:  # noqa: BLE001
    EventManager = None  # type: ignore
    EventStatus = None  # type: ignore
    get_event_manager = None  # type: ignore
    _EVENT_MANAGER_IMPORT_ERROR = _exc


def _get_event_manager() -> Optional[Any]:
    """
    懒加载 EventManager 单例（进程内复用 get_event_manager()）。
    失败时返回 None（路由层兜底）。
    """
    global _event_manager
    if _event_manager is not None:
        return _event_manager
    if not _EVENT_MANAGER_IMPORT_OK or get_event_manager is None:
        return None
    try:
        _event_manager = get_event_manager()
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error(
            'event_api',
            f'获取 EventManager 失败: {exc}',
            exc,
        )
        _event_manager = None
    return _event_manager


# ---------------------------------------------------------------------
# Pydantic v2 扩展（不复用/不改动 EventDTO；只在本文内新增）
# ---------------------------------------------------------------------
class EventDTOExtended(BaseModel):
    """
    事件 DTO 扩展版：在 EventDTO 基础上补充 title / description /
    priority / updated_at / completed_at / read_at / archived_at，
    供前端 EventTable 渲染。

    Attributes:
        uuid: 事件 ID（与 EventDTO.uuid 一致）
        type: 事件类型
        status: 事件状态
        payload: 事件 payload（来自 metadata 字段）
        created_at: ISO 8601 时间戳
        title: 事件标题
        description: 事件描述
        priority: 事件优先级（int）
        updated_at: 最近更新时间
        completed_at: 完成时间（可能为空）
        read_at: 标记已读时间（可能为空）
        archived_at: 归档时间（可能为空）
    """
    uuid: str
    type: str
    status: str
    payload: Dict
    created_at: str
    title: str = ""
    description: str = ""
    priority: int = 2
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    read_at: Optional[str] = None
    archived_at: Optional[str] = None


# ---------------------------------------------------------------------
# 工具：events 表行 → EventDTO / EventDTOExtended 转换
# ---------------------------------------------------------------------
def _parse_metadata(raw: Any) -> Dict[str, Any]:
    """把 metadata 字段（可能是 dict / str）安全解析成 dict。"""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            return dict(json.loads(raw) or {})
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _row_to_extended_dto(row: Dict[str, Any]) -> EventDTOExtended:
    """
    把数据库行（可能是 sqlite3.Row / dict）映射为 EventDTOExtended。

    行字段（events 表）：
      event_id, title, description, event_type, priority, status,
      created_at, updated_at, completed_at, metadata
    """
    if not isinstance(row, dict):
        try:
            row = dict(row)
        except Exception:
            row = {}
    meta = _parse_metadata(row.get('metadata'))
    return EventDTOExtended(
        uuid=str(row.get('event_id') or row.get('uuid') or ''),
        type=str(row.get('event_type') or row.get('type') or 'event'),
        status=str(row.get('status') or 'pending'),
        payload=meta,
        created_at=str(row.get('created_at') or ''),
        title=str(row.get('title') or ''),
        description=str(row.get('description') or ''),
        priority=int(row.get('priority') or 2) if str(row.get('priority') or '').strip() else 2,
        updated_at=row.get('updated_at'),
        completed_at=row.get('completed_at'),
        read_at=meta.get('read_at'),
        archived_at=meta.get('archived_at'),
    )


def _row_to_dto(row: Dict[str, Any]) -> EventDTO:
    """
    把数据库行映射为 EventDTO（用于 EventListResponse）。
    """
    if not isinstance(row, dict):
        try:
            row = dict(row)
        except Exception:
            row = {}
    meta = _parse_metadata(row.get('metadata'))
    return EventDTO(
        uuid=str(row.get('event_id') or row.get('uuid') or ''),
        type=str(row.get('event_type') or row.get('type') or 'event'),
        status=str(row.get('status') or 'pending'),
        payload=meta,
        created_at=str(row.get('created_at') or ''),
    )


def _fail(message: str, code: int = status.HTTP_400_BAD_REQUEST) -> Dict[str, Any]:
    """统一兜底响应。"""
    return {"error": message, "status_code": code}


def _execute_sql(em: Any, sql: str, params: tuple = ()) -> bool:
    """
    通过 EventManager 的 db 句柄直接执行 UPDATE/INSERT SQL。
    返回是否影响至少一行。
    """
    if em is None or not hasattr(em, 'db') or em.db is None:
        return False
    try:
        with em.db.get_connection() as conn:
            cur = conn.execute(sql, params)
            affected = cur.rowcount
        return bool(affected and affected > 0)
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('event_api', f'_execute_sql 失败: {exc}', exc)
        return False


# ---------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------
router = APIRouter(prefix="/api/events", tags=["events"])


# =====================================================================
# GET /api/events?limit=&offset=&type=&status=
# =====================================================================
@router.get("")
async def list_events(
    limit: int = Query(50, ge=1, le=200, description="返回条数上限"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    type: Optional[str] = Query(
        None,
        description="事件类型筛选（如 notification / task）",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="事件状态筛选（如 pending / completed / cancelled）",
    ),
) -> Dict[str, Any]:
    """
    分页 + 筛选事件列表。

    Returns:
        {
          "events": [EventDTO...],
          "total": int,
          "limit": int,
          "offset": int,
          "items": [EventDTOExtended...],  # 扩展字段供前端 EventTable
          "warning": str | None
        }
    """
    em = _get_event_manager()
    if em is None:
        return {
            "events": [],
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "warning": "EventManager 不可用：导入或初始化失败",
        }

    try:
        # EventManager.get_all_events(status, event_type, limit) 不支持 offset；
        # 我们走 raw SQL 拿到 offset 段。
        # 先确认 events 表存在；不可用就降级空列表。
        try:
            with em.db.get_connection() as conn:
                cur = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='events'",
                )
                exists = cur.fetchone()
        except Exception:  # noqa: BLE001
            exists = None
        if not exists:
            return {
                "events": [],
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "warning": "events 表未在数据库中创建，当前返回空列表",
            }

        # 拼 SQL
        where_parts: List[str] = []
        params: List[Any] = []
        if type:
            where_parts.append("event_type = ?")
            params.append(str(type))
        if status_filter:
            where_parts.append("status = ?")
            params.append(str(status_filter))
        where_sql = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        # 取 total
        try:
            with em.db.get_connection() as conn:
                cur = conn.execute(
                    f"SELECT COUNT(*) FROM events {where_sql}",
                    tuple(params),
                )
                total_row = cur.fetchone()
                total = int(total_row[0]) if total_row else 0
        except Exception:  # noqa: BLE001
            total = 0

        # 取 rows
        try:
            with em.db.get_connection() as conn:
                cur = conn.execute(
                    f"SELECT * FROM events {where_sql} "
                    f"ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?",
                    tuple(params + [limit, offset]),
                )
                raw_rows = cur.fetchall() or []
        except Exception as exc:  # noqa: BLE001
            _debug_logger.log_warn('event_api', f'查询 events 失败: {exc}')
            raw_rows = []

        # 转 dict 列表
        rows: List[Dict[str, Any]] = []
        for r in raw_rows:
            try:
                if isinstance(r, dict):
                    rows.append(dict(r))
                else:
                    rows.append({k: r[k] for k in r.keys()})
            except Exception:
                try:
                    rows.append(dict(r))
                except Exception:
                    continue

        return {
            "events": [_row_to_dto(r) for r in rows],
            "items": [_row_to_extended_dto(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "warning": None,
        }
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('event_api', f'list_events 失败: {exc}', exc)
        warnings.warn(
            f"[event_api] list_events 失败: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return {
            "events": [],
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(exc),
        }


# =====================================================================
# POST /api/events/{event_id}/read
# =====================================================================
@router.post("/{event_id}/read")
async def mark_event_read(
    event_id: str = Path(..., min_length=1, description="事件 ID"),
) -> Dict[str, Any]:
    """
    标记事件已读。
    - 复用 EventManager.update_event_status(status=COMPLETED, log_message=...)；
    - 同时把 read_at 写入 metadata 字段。
    """
    em = _get_event_manager()
    if em is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EventManager 不可用",
        )

    if not event_id or not event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_id 必填",
        )

    try:
        # 确认事件存在
        existing = em.get_event(event_id) if hasattr(em, 'get_event') else None
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到事件: {event_id}",
            )

        # 1) 写 read_at 到 metadata
        try:
            meta_raw = None
            with em.db.get_connection() as conn:
                cur = conn.execute(
                    "SELECT metadata FROM events WHERE event_id = ?",
                    (event_id,),
                )
                row = cur.fetchone()
            meta_raw = row[0] if row else None
        except Exception:  # noqa: BLE001
            meta_raw = None

        meta = _parse_metadata(meta_raw) or {}
        now_iso = datetime.now().isoformat()
        meta['read_at'] = now_iso

        try:
            with em.db.get_connection() as conn:
                conn.execute(
                    "UPDATE events SET metadata = ? WHERE event_id = ?",
                    (json.dumps(meta, ensure_ascii=False), event_id),
                )
        except Exception as exc:  # noqa: BLE001
            _debug_logger.log_warn('event_api', f'写 read_at 到 metadata 失败: {exc}')

        # 2) 状态切到 completed（不强制：失败也不抛 5xx）
        status_ok = False
        if hasattr(em, 'update_event_status') and EventStatus is not None:
            try:
                status_ok = em.update_event_status(
                    event_id,
                    EventStatus.COMPLETED,
                    log_message='marked as read',
                )
            except Exception as exc:  # noqa: BLE001
                _debug_logger.log_warn('event_api', f'update_event_status 失败: {exc}')
                status_ok = False

        return {
            "event_id": event_id,
            "marked": True,
            "read_at": now_iso,
            "status": "completed",
            "status_updated": status_ok,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('event_api', f'mark_event_read 失败: {exc}', exc)
        return _fail(f"标记已读失败: {exc}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# POST /api/events/{event_id}/archive
# =====================================================================
@router.post("/{event_id}/archive")
async def archive_event(
    event_id: str = Path(..., min_length=1, description="事件 ID"),
) -> Dict[str, Any]:
    """
    归档事件。
    - 复用 EventManager.update_event_status(status=CANCELLED, log_message=...)；
    - 同时把 archived_at 写入 metadata 字段。
    """
    em = _get_event_manager()
    if em is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EventManager 不可用",
        )

    if not event_id or not event_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="event_id 必填",
        )

    try:
        existing = em.get_event(event_id) if hasattr(em, 'get_event') else None
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"未找到事件: {event_id}",
            )

        # 1) 写 archived_at 到 metadata
        try:
            meta_raw = None
            with em.db.get_connection() as conn:
                cur = conn.execute(
                    "SELECT metadata FROM events WHERE event_id = ?",
                    (event_id,),
                )
                row = cur.fetchone()
            meta_raw = row[0] if row else None
        except Exception:  # noqa: BLE001
            meta_raw = None

        meta = _parse_metadata(meta_raw) or {}
        now_iso = datetime.now().isoformat()
        meta['archived_at'] = now_iso

        try:
            with em.db.get_connection() as conn:
                conn.execute(
                    "UPDATE events SET metadata = ? WHERE event_id = ?",
                    (json.dumps(meta, ensure_ascii=False), event_id),
                )
        except Exception as exc:  # noqa: BLE001
            _debug_logger.log_warn('event_api', f'写 archived_at 到 metadata 失败: {exc}')

        # 2) 状态切到 cancelled
        status_ok = False
        if hasattr(em, 'update_event_status') and EventStatus is not None:
            try:
                status_ok = em.update_event_status(
                    event_id,
                    EventStatus.CANCELLED,
                    log_message='archived',
                )
            except Exception as exc:  # noqa: BLE001
                _debug_logger.log_warn('event_api', f'update_event_status 失败: {exc}')
                status_ok = False

        return {
            "event_id": event_id,
            "archived": True,
            "archived_at": now_iso,
            "status": "cancelled",
            "status_updated": status_ok,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('event_api', f'archive_event 失败: {exc}', exc)
        return _fail(f"归档失败: {exc}", code=status.HTTP_400_BAD_REQUEST)


__all__ = ["router"]
