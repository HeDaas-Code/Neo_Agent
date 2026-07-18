"""
Database schemas - Pydantic v2 models for database management endpoints.
数据库管理端点相关的 Pydantic v2 模型。

Stage C.5: 为 /api/database/* 提供 list/count/query/delete 契约。
字段命名与前端 ``src/web/frontend/src/types/database.ts`` 对齐。
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class TablesListResponse(BaseModel):
    """
    白名单表列表响应。
    Attributes:
        tables: 表名列表（仅白名单中实际存在的表）
        total: 表数量
    """
    tables: List[str] = Field(default_factory=list)
    total: int = 0


class TableDataResponse(BaseModel):
    """
    业务表数据查询响应。
    Attributes:
        table: 表名
        rows: 行数据列表（每行为 dict）
        total: 本次返回的行数
    """
    table: str
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class CountResponse(BaseModel):
    """
    表记录数响应。
    Attributes:
        table: 表名
        total: 该表的总记录数
    """
    table: str
    total: int = 0


class DeleteResponse(BaseModel):
    """
    删除记录响应。
    Attributes:
        table: 表名
        uuid: 被删除记录的 uuid
        deleted: 是否成功删除
    """
    table: str
    uuid: str
    deleted: bool = False


__all__ = [
    "TablesListResponse",
    "TableDataResponse",
    "CountResponse",
    "DeleteResponse",
]
