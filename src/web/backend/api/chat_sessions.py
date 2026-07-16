"""
Chat Sessions REST API - v3.1.0
================================

端点（统一前缀 /api/chat/sessions）：
- GET    /                       列出会话（按 updated_at desc）
- POST   /                       创建新会话
- GET    /{session_id}/messages  拉取会话消息
- PATCH  /{session_id}           重命名
- DELETE /{session_id}           级联删除

设计要点：
1. 数据库访问完全走 ``db_manager.get_chat_session_repository()``。
2. 永不返回 5xx：所有路由 try/except + 4xx 包装。
3. 写操作后不主动 touch：add_message / update_title 内部已维护元信息。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.core.database_manager import DatabaseManager
except Exception:  # noqa: BLE001
    DatabaseManager = None  # type: ignore

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def log_warn(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        return _Stub()


router = APIRouter(prefix="/api/chat/sessions", tags=["chat-sessions"])
debug_logger = get_debug_logger()

# 进程内单例 db_manager
_db: Optional[DatabaseManager] = None  # type: ignore


def _get_db() -> Any:
    global _db
    if _db is None:
        if DatabaseManager is None:
            raise HTTPException(status_code=503, detail="DatabaseManager unavailable")
        _db = DatabaseManager()
    return _db


def _get_repo():
    return _get_db().get_chat_session_repository()


# ----------------------------------------------------------------------
# Pydantic schemas
# ----------------------------------------------------------------------
class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128, description="归属用户 ID")
    title: Optional[str] = Field(default="新会话", max_length=200)


class RenameSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class SessionResponse(BaseModel):
    id: int
    user_id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int = 0


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    emotion_json: Optional[str] = None
    conn_id: Optional[str] = None
    created_at: float


class MessageListResponse(BaseModel):
    items: List[MessageResponse]
    total: int


# ----------------------------------------------------------------------
# GET /api/chat/sessions
# ----------------------------------------------------------------------
@router.get("", response_model=None)
async def list_sessions(
    user_id: str = Query(default="default", min_length=1, max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """
    列出用户的会话（按 updated_at 倒序）。
    """
    try:
        repo = _get_repo()
        items = repo.list(user_id=user_id, limit=limit, offset=offset)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.chat_sessions', f'list 出错: {exc}', exc)
        except Exception:
            pass
        return {"items": [], "total": 0, "error": str(exc)}

    return {
        "items": [dict(it) for it in (items or [])],
        "total": len(items or []),
    }


# ----------------------------------------------------------------------
# POST /api/chat/sessions
# ----------------------------------------------------------------------
@router.post("", response_model=SessionResponse)
async def create_session(req: CreateSessionRequest) -> SessionResponse:
    """
    创建新会话。
    """
    try:
        repo = _get_repo()
        new_id = repo.create(user_id=req.user_id, title=req.title or "新会话")
        row = repo.get(new_id) or {}
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.chat_sessions', f'create 出错: {exc}', exc)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"create failed: {exc}")

    return SessionResponse(
        id=int(row.get("id", 0) or 0),
        user_id=str(row.get("user_id", req.user_id)),
        title=str(row.get("title", req.title or "新会话")),
        created_at=float(row.get("created_at", 0.0) or 0.0),
        updated_at=float(row.get("updated_at", 0.0) or 0.0),
        message_count=int(row.get("message_count", 0) or 0),
    )


# ----------------------------------------------------------------------
# GET /api/chat/sessions/current
# ----------------------------------------------------------------------
@router.get("/current", response_model=Optional[SessionResponse])
async def get_current_session(
    user_id: str = Query(default="default", min_length=1, max_length=128),
) -> Optional[SessionResponse]:
    """
    取指定 user_id 的最近一个活跃 session（按 updated_at 倒序的第一条）。
    """
    try:
        repo = _get_repo()
        items = repo.list(user_id=user_id, limit=1, offset=0)
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.chat_sessions', f'current 出错: {exc}', exc)
        except Exception:
            pass
        return None
    if not items:
        return None
    row = items[0]
    return SessionResponse(
        id=int(row.get("id", 0) or 0),
        user_id=str(row.get("user_id", user_id)),
        title=str(row.get("title", "新会话")),
        created_at=float(row.get("created_at", 0.0) or 0.0),
        updated_at=float(row.get("updated_at", 0.0) or 0.0),
        message_count=int(row.get("message_count", 0) or 0),
    )


# ----------------------------------------------------------------------
# GET /api/chat/sessions/{session_id}/messages
# ----------------------------------------------------------------------
@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def list_messages(
    session_id: int,
    limit: int = Query(default=200, ge=1, le=1000),
) -> MessageListResponse:
    """
    拉取会话消息（按 id 升序）。
    """
    try:
        repo = _get_repo()
        if repo.get(session_id) is None:
            raise HTTPException(status_code=404, detail="session not found")
        items = repo.list_messages(session_id=session_id, limit=limit)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.chat_sessions', f'list_messages 出错: {exc}', exc)
        except Exception:
            pass
        return MessageListResponse(items=[], total=0)

    return MessageListResponse(
        items=[MessageResponse(
            id=int(it.get("id", 0) or 0),
            session_id=int(it.get("session_id", session_id) or 0),
            role=str(it.get("role", "")),
            content=str(it.get("content", "")),
            emotion_json=it.get("emotion_json"),
            conn_id=it.get("conn_id"),
            created_at=float(it.get("created_at", 0.0) or 0.0),
        ) for it in (items or [])],
        total=len(items or []),
    )


# ----------------------------------------------------------------------
# PATCH /api/chat/sessions/{session_id}
# ----------------------------------------------------------------------
@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session(session_id: int, req: RenameSessionRequest) -> SessionResponse:
    """
    重命名会话。
    """
    try:
        repo = _get_repo()
        if repo.get(session_id) is None:
            raise HTTPException(status_code=404, detail="session not found")
        ok = repo.update_title(session_id=session_id, title=req.title)
        if not ok:
            raise HTTPException(status_code=400, detail="update failed")
        row = repo.get(session_id) or {}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.chat_sessions', f'rename 出错: {exc}', exc)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"rename failed: {exc}")

    return SessionResponse(
        id=int(row.get("id", session_id) or 0),
        user_id=str(row.get("user_id", "")),
        title=str(row.get("title", req.title)),
        created_at=float(row.get("created_at", 0.0) or 0.0),
        updated_at=float(row.get("updated_at", 0.0) or 0.0),
        message_count=int(row.get("message_count", 0) or 0),
    )


# ----------------------------------------------------------------------
# DELETE /api/chat/sessions/{session_id}
# ----------------------------------------------------------------------
@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: int) -> Response:
    """
    删除会话（依赖 ON DELETE CASCADE 删 messages）。
    """
    try:
        repo = _get_repo()
        if repo.get(session_id) is None:
            raise HTTPException(status_code=404, detail="session not found")
        repo.delete(session_id=session_id)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.chat_sessions', f'delete 出错: {exc}', exc)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"delete failed: {exc}")
    return Response(status_code=204)


__all__ = ["router"]
