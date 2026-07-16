"""
Database API Router
``/api/database`` 端点 — 业务表查询 / 计数 / 受控删除。

Stage C.5:
- 列出白名单中实际存在的业务表
- 分页查询 + 记录总数
- 按 uuid 删除（带 ``X-Confirm: true`` 头二次确认）

设计要点：
1. 复用 ``database_service``：所有 SQL 拼接已由 ``_validate_table`` 防御。
2. 失败路径 4xx：按硬约束，所有异常路径均返回 4xx（无 5xx）。
3. 错误响应统一为 ``{"error": "..."}`` 格式（不依赖 FastAPI 默认 detail）。
4. DELETE 二次确认：必须传 ``X-Confirm: true`` 头；缺失 → 400。
5. ``app.include_router(database.router)`` 由 main.py 完成。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.web.backend.services.database_service import (  # noqa: E402
    database_service,
)
from src.web.backend.schemas.database import (  # noqa: E402
    CountResponse,
    DeleteResponse,
    TableDataResponse,
    TablesListResponse,
)


router = APIRouter(prefix="/api/database", tags=["database"])


# ----------------------------------------------------------------------
# 内部：错误响应统一格式
# ----------------------------------------------------------------------
def _error_response(status_code: int, message: str) -> JSONResponse:
    """
    统一错误响应格式：``{"error": "..."}``。
    状态码必须在 4xx 范围内。
    """
    if status_code < 400 or status_code >= 500:
        status_code = 400
    return JSONResponse(
        status_code=status_code,
        content={"error": message},
    )


# ----------------------------------------------------------------------
# 内部：表名白名单校验包装
# ----------------------------------------------------------------------
def _safe_validate_table(table: str) -> str:
    """
    包装 ``database_service._validate_table``：
    - 失败时抛 ``ValueError``；调用方负责转成 4xx 响应。
    """
    try:
        return database_service._validate_table(table)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Table {table!r} not allowed: {exc}") from exc


# ----------------------------------------------------------------------
# 内部：单表 COUNT(*)
# ----------------------------------------------------------------------
def _count_table_rows(safe_table: str) -> int:
    """
    对已经通过白名单校验的表名执行 ``SELECT COUNT(*)``。
    任何异常路径均返回 0（不抛出）。
    """
    try:
        db = database_service.get_db()
        if db is None:
            return 0
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT COUNT(*) FROM {safe_table}")
            row = cur.fetchone()
            if row is None:
                return 0
            try:
                if isinstance(row, dict):
                    return int(list(row.values())[0])
                return int(row[0])
            except (KeyError, IndexError, TypeError, ValueError):
                return 0
    except Exception:  # noqa: BLE001
        return 0


# ----------------------------------------------------------------------
# 1) GET /api/database/tables
# ----------------------------------------------------------------------
@router.get(
    "/tables",
    response_model=TablesListResponse,
    summary="List whitelisted business tables",
)
async def list_tables() -> Any:
    """
    返回白名单中实际存在的业务表名列表。

    响应：
    - ``tables``: 表名列表（按字典序）
    - ``total``: 表数量
    """
    try:
        table_names = database_service.get_tables() or []
    except Exception as exc:  # noqa: BLE001
        # 按硬约束：失败路径返回 4xx
        return _error_response(400, f"DatabaseService 不可用: {exc}")

    return TablesListResponse(tables=list(table_names), total=len(table_names))


# ----------------------------------------------------------------------
# 2) GET /api/database/{table}?limit=100&offset=0
# ----------------------------------------------------------------------
@router.get(
    "/{table}",
    response_model=TableDataResponse,
    summary="Query rows of a whitelisted table (paginated)",
)
async def query_table(
    table: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Any:
    """
    分页查询指定表的数据。

    - ``limit``: 1-1000（默认 100）
    - ``offset``: >=0（默认 0）
    - 表名必须在白名单内；不在白名单 → 400
    - 响应字段：``table`` / ``rows`` / ``total``（本次返回行数）
    """
    try:
        _safe_validate_table(table)
    except ValueError as exc:
        return _error_response(400, str(exc))

    try:
        rows = database_service.query_table(table, limit=limit, offset=offset) or []
    except ValueError as exc:
        return _error_response(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error_response(400, f"查询失败: {exc}")

    return TableDataResponse(
        table=table,
        rows=list(rows),
        total=len(rows),
    )


# ----------------------------------------------------------------------
# 3) GET /api/database/{table}/count
# ----------------------------------------------------------------------
@router.get(
    "/{table}/count",
    response_model=CountResponse,
    summary="Count total rows of a whitelisted table",
)
async def count_table(table: str) -> Any:
    """
    返回指定表的总记录数（``SELECT COUNT(*) FROM table``）。

    - 表名必须在白名单内；不在白名单 → 400
    - 响应字段：``table`` / ``total``
    """
    try:
        safe_table = _safe_validate_table(table)
    except ValueError as exc:
        return _error_response(400, str(exc))

    total = _count_table_rows(safe_table)
    return CountResponse(table=table, total=int(total))


# ----------------------------------------------------------------------
# 4) DELETE /api/database/{table}/{uuid}
# ----------------------------------------------------------------------
@router.delete(
    "/{table}/{uuid}",
    response_model=DeleteResponse,
    summary="Delete a single row by uuid (requires X-Confirm header)",
)
async def delete_record(
    table: str,
    uuid: str,
    x_confirm: Optional[str] = Header(
        None,
        alias="X-Confirm",
        description="必须传 X-Confirm: true 才执行删除（防误删）",
    ),
) -> Any:
    """
    按 uuid 删除指定表的一条记录。

    - 必须传 ``X-Confirm: true`` 头；缺失或非 true → 400
    - 表名必须在白名单内；不在白名单 → 400
    - uuid 为空 → 400
    - 数据库层未匹配到记录（rowcount == 0）→ 404
    - 响应字段：``table`` / ``uuid`` / ``deleted``
    """
    # 二次确认：必须传 X-Confirm: true
    if x_confirm is None or str(x_confirm).strip().lower() != "true":
        return _error_response(400, "需要 X-Confirm: true 头确认")

    try:
        _safe_validate_table(table)
    except ValueError as exc:
        return _error_response(400, str(exc))

    if not uuid or not isinstance(uuid, str):
        return _error_response(400, "uuid 不能为空")

    try:
        ok = bool(database_service.delete_record(table, uuid))
    except ValueError as exc:
        return _error_response(400, str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error_response(400, f"删除失败: {exc}")

    if not ok:
        # 数据库层未匹配到记录
        return _error_response(404, f"未在 {table} 中找到 uuid={uuid} 的记录")

    return DeleteResponse(table=table, uuid=uuid, deleted=True)


__all__ = ["router"]
