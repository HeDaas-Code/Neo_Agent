"""
Knowledge schemas - Pydantic v2 models for knowledge base endpoints.
知识库相关的 Pydantic v2 模型。

Stage A.3: 为 /api/knowledge/* 提供实体/定义的契约。
Stage C.1: 新增 KnowledgeCreate / KnowledgeUpdate，提供前端 CRUD 强约束。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgeEntity(BaseModel):
    """
    知识库实体。
    Attributes:
        uuid: 实体唯一标识
        name: 原始名称
        normalized_name: 归一化名称
        created_at: ISO 8601 时间戳
    """
    uuid: str
    name: str
    normalized_name: str
    created_at: str


class KnowledgeDefinition(BaseModel):
    """
    知识库实体定义（实体下属的事实/属性/关系）。
    Attributes:
        id: 自增主键
        entity_uuid: 所属实体 uuid
        content: 定义内容
        type: 定义类型（fact / attribute / relation ...）
        confidence: 置信度（0.0-1.0）
        priority: 优先级
    """
    id: int
    entity_uuid: str
    content: str
    type: str
    confidence: float
    priority: int


class KnowledgeSearchRequest(BaseModel):
    """
    知识库搜索请求。
    Attributes:
        q: 搜索关键词（必填，至少 1 字符）
        limit: 返回上限（默认 20）
    """
    q: str = Field(..., min_length=1)
    limit: int = 20


class KnowledgeSearchResponse(BaseModel):
    """
    知识库搜索响应。
    Attributes:
        results: 实体列表
        total: 总匹配条数
    """
    results: List[KnowledgeEntity]
    total: int


# =====================================================================
# Stage C.1: Web 端 CRUD 强约束
# =====================================================================

class KnowledgeCreate(BaseModel):
    """
    创建知识实体的请求体（Stage C.1）。

    Attributes:
        entity_name: 实体名称（必填，1-100 字符）
        category: 分类（可选，<= 64 字符；将作为 entity_definitions.type）
        description: 描述（可选，<= 4000 字符；将作为 entity_definitions.content）
        related_info: 相关信息字典（可选，key->value 写入 entity_related_info）
    """
    entity_name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=4000)
    related_info: Optional[Dict[str, Any]] = None


class KnowledgeUpdate(BaseModel):
    """
    更新知识实体的请求体（Stage C.1）。

    所有字段均可选；至少要传一个字段。
    Attributes:
        entity_name: 新名称（1-100 字符）
        category: 新分类（<= 64 字符）
        description: 新描述（<= 4000 字符）
        related_info: 替换该实体的全部相关信息
    """
    entity_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=4000)
    related_info: Optional[Dict[str, Any]] = None


__all__ = [
    "KnowledgeEntity",
    "KnowledgeDefinition",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "KnowledgeCreate",
    "KnowledgeUpdate",
]
