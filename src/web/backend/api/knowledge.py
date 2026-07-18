"""
Knowledge REST API router.
知识库 REST API 路由（Stage C.1）。

端点：
  GET    /api/knowledge/search        关键词搜索（?q=...&limit=20）
  GET    /api/knowledge               列出所有实体（?limit=50）
  POST   /api/knowledge               新增实体（body 走 KnowledgeCreate 校验）
  PUT    /api/knowledge/{uuid}        更新实体（body 走 KnowledgeUpdate 校验）
  DELETE /api/knowledge/{uuid}        删除实体

设计要点：
1. 所有路由都用 try/except 包裹，失败返回 4xx + {"error": str(e)}，
   不冒 5xx（Stage C.1 验证标准）。
2. 复用现有 DatabaseManager：search_knowledge / get_all_entities /
   add_entity / update_entity / delete_entity。
3. Pydantic v2 schema 校验（KnowledgeCreate / KnowledgeUpdate）在
   FastAPI 入口处自动完成；非法 body 直接 422。
4. 路径参数 uuid 透传给 db 层；不存在时返回 404（不抛 500）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse

# Pydantic v2 schema（强类型契约）
from src.web.backend.schemas.knowledge import (
    KnowledgeCreate,
    KnowledgeUpdate,
)

# DatabaseManager（懒加载 + try/except 保护）
try:
    from src.core.database_manager import DatabaseManager  # type: ignore
    _DB_IMPORT_OK = True
    _DB_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _exc:  # noqa: BLE001
    DatabaseManager = None  # type: ignore
    _DB_IMPORT_OK = False
    _DB_IMPORT_ERROR = _exc


router = APIRouter()


# ---------------------------------------------------------------------
# DatabaseManager 单例（懒加载）
# ---------------------------------------------------------------------
_db_singleton: Optional[Any] = None


def _get_db() -> Optional[Any]:
    """
    懒加载 DatabaseManager 单例。
    失败时返回 None，由路由层兜底为 503。
    """
    global _db_singleton
    if _db_singleton is not None:
        return _db_singleton
    if not _DB_IMPORT_OK or DatabaseManager is None:
        return None
    try:
        _db_singleton = DatabaseManager()
    except Exception:  # noqa: BLE001
        _db_singleton = None
    return _db_singleton


# ---------------------------------------------------------------------
# 工具：把 ValueError / 不存在 uuid 等转成 4xx，绝不 5xx
# ---------------------------------------------------------------------
def _fail(message: str, code: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    return JSONResponse(status_code=code, content={"error": message})


# =====================================================================
# GET /api/knowledge/search?q=...&limit=20
# =====================================================================
@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=200, description="返回条数上限"),
) -> Dict[str, Any]:
    """
    关键词搜索知识库实体（Stage C.1）。

    Args:
        q: 搜索关键词（必填）
        limit: 返回上限（默认 20，1-200）

    Returns:
        {"results": [...], "total": int}
    """
    try:
        db = _get_db()
        if db is None:
            return _fail(
                "DatabaseManager 不可用：导入或初始化失败",
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        results: List[Dict[str, Any]] = db.search_knowledge(query=q, limit=limit)
        # 过滤掉非 dict 的脏数据，避免 JSON 序列化失败
        clean: List[Dict[str, Any]] = [r for r in results if isinstance(r, dict)]
        return {"results": clean, "total": len(clean)}
    except ValueError as e:  # noqa: BLE001
        return _fail(f"参数错误: {e}", code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:  # noqa: BLE001
        return _fail(f"搜索失败: {e}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# GET /api/knowledge?limit=50
# =====================================================================
@router.get("")
async def list_knowledge(
    limit: int = Query(50, ge=1, le=500, description="返回条数上限"),
) -> Dict[str, Any]:
    """
    列出所有知识库实体（兜底接口，Stage C.1）。

    优先复用 DatabaseManager.get_all_entities(limit)；如果 db 不可用
    或返回非列表，兜底为空列表。

    Returns:
        {"results": [...], "total": int}
    """
    try:
        db = _get_db()
        if db is None:
            return _fail(
                "DatabaseManager 不可用：导入或初始化失败",
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        rows: List[Dict[str, Any]] = db.get_all_entities(limit=limit) or []
        clean: List[Dict[str, Any]] = [r for r in rows if isinstance(r, dict)]
        return {"results": clean, "total": len(clean)}
    except ValueError as e:  # noqa: BLE001
        return _fail(f"参数错误: {e}", code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:  # noqa: BLE001
        return _fail(f"列出知识库失败: {e}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# POST /api/knowledge
# =====================================================================
@router.post("")
async def create_knowledge(
    payload: KnowledgeCreate = Body(...),
) -> Dict[str, Any]:
    """
    新增知识库实体（Stage C.1）。

    Body 通过 KnowledgeCreate (Pydantic v2) 校验。

    Returns:
        {"uuid": str, "entity_name": str, "created": true}
    """
    try:
        db = _get_db()
        if db is None:
            return _fail(
                "DatabaseManager 不可用：导入或初始化失败",
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        new_uuid: str = db.add_entity(
            entity_name=payload.entity_name,
            category=payload.category,
            description=payload.description,
            related_info=payload.related_info,
        )
        if not new_uuid:
            return _fail("新增实体失败：未返回 uuid", code=status.HTTP_400_BAD_REQUEST)

        return {
            "uuid": new_uuid,
            "entity_name": payload.entity_name,
            "created": True,
        }
    except ValueError as e:  # noqa: BLE001
        return _fail(f"参数错误: {e}", code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:  # noqa: BLE001
        return _fail(f"新增实体失败: {e}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# PUT /api/knowledge/{uuid}
# =====================================================================
@router.put("/{uuid}")
async def update_knowledge(
    uuid: str = Path(..., min_length=1, description="实体 uuid"),
    payload: KnowledgeUpdate = Body(...),
) -> Dict[str, Any]:
    """
    更新知识库实体（Stage C.1）。

    Body 通过 KnowledgeUpdate (Pydantic v2) 校验。

    Returns:
        {"uuid": str, "updated": bool}
    """
    try:
        db = _get_db()
        if db is None:
            return _fail(
                "DatabaseManager 不可用：导入或初始化失败",
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # 至少要传一个可更新字段
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return _fail("请求体为空：至少要传一个字段", code=status.HTTP_400_BAD_REQUEST)

        ok: bool = db.update_entity(
            entity_uuid=uuid,
            entity_name=payload.entity_name,
            category=payload.category,
            description=payload.description,
            related_info=payload.related_info,
        )
        if not ok:
            return _fail(
                f"未找到实体或无字段更新: {uuid}",
                code=status.HTTP_404_NOT_FOUND,
            )

        return {"uuid": uuid, "updated": True}
    except ValueError as e:  # noqa: BLE001
        return _fail(f"参数错误: {e}", code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:  # noqa: BLE001
        return _fail(f"更新实体失败: {e}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# DELETE /api/knowledge/{uuid}
# =====================================================================
@router.delete("/{uuid}")
async def delete_knowledge(
    uuid: str = Path(..., min_length=1, description="实体 uuid"),
) -> Dict[str, Any]:
    """
    删除知识库实体（Stage C.1）。

    Returns:
        {"uuid": str, "deleted": bool}
    """
    try:
        db = _get_db()
        if db is None:
            return _fail(
                "DatabaseManager 不可用：导入或初始化失败",
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ok: bool = db.delete_entity(uuid)
        if not ok:
            return _fail(
                f"未找到实体或删除失败: {uuid}",
                code=status.HTTP_404_NOT_FOUND,
            )

        return {"uuid": uuid, "deleted": True}
    except ValueError as e:  # noqa: BLE001
        return _fail(f"参数错误: {e}", code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:  # noqa: BLE001
        return _fail(f"删除实体失败: {e}", code=status.HTTP_400_BAD_REQUEST)


__all__ = ["router"]
