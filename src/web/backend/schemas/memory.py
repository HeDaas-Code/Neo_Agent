"""
Memory schemas - Pydantic v2 models for /api/memory/* endpoints.
记忆 / 话题时间线相关的 Pydantic v2 模型。

Stage B.4: 为 /api/memory/timeline 与 /api/memory/loop/{uuid}/context 提供契约。
- 数据源：``open_loops`` 表（由 OpenLoopTracker 写入）。
- 失败降级：节点为空 / 链接为空 / 上下文为空 list，不抛 5xx。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TimelineNode(BaseModel):
    """
    话题时间线节点（open_loops 一行）。

    Attributes:
        uuid: 话题唯一标识（open_loops.uuid）
        topic: 话题标题（open_loops.topic）
        date: 节点日期（YYYY-MM-DD，从 raised_at 截取前 10 位）
        status: 话题状态（'open' / 'closed'/'resolved' 等）
        category: 话题分类（暂为 '其他'，留给前端做兼容）
        mention_count: 提及次数（open_loops.mention_count）
        keywords: 关联关键词列表（open_loops.related_keywords_json）
    """
    uuid: str
    topic: str
    date: str
    status: str = "open"
    category: str = "其他"
    mention_count: int = 0
    keywords: List[str] = Field(default_factory=list)


class TimelineLink(BaseModel):
    """
    话题时间线链接（节点之间的关联关系）。

    Attributes:
        source: 源节点 uuid
        target: 目标节点 uuid
        relation: 关系类型（'keyword' / 'time' / 'manual' 等，默认 'keyword'）
    """
    source: str
    target: str
    relation: str = "keyword"


class TimelineResponse(BaseModel):
    """
    时间线响应（ECharts 关系图 / 散点图所需最小集）。

    Attributes:
        nodes: 节点列表
        links: 链接列表
        days: 查询时间范围（天），默认 7
        total: 节点数量（便于前端展示）
    """
    nodes: List[TimelineNode] = Field(default_factory=list)
    links: List[TimelineLink] = Field(default_factory=list)
    days: int = 7
    total: int = 0


class LoopContextItem(BaseModel):
    """
    话题上下文条目（单条对话消息 / 锚点）。

    Attributes:
        role: 角色（'user' / 'assistant' / 'system'）
        content: 文本内容
        timestamp: ISO 8601 时间戳（可空）
        source: 数据来源（'short_term_memory' / 'open_loop_context' / 'fallback'）
    """
    role: str = "system"
    content: str = ""
    timestamp: Optional[str] = None
    source: str = "short_term_memory"


class LoopContextResponse(BaseModel):
    """
    话题上下文响应。

    Attributes:
        uuid: 话题 uuid（路径参数透传）
        topic: 话题标题（找不到时为空字符串）
        status: 话题状态
        items: 上下文条目列表（失败 / 未找到时为空 list）
        total: 条目数量
    """
    uuid: str
    topic: str = ""
    status: str = "unknown"
    items: List[LoopContextItem] = Field(default_factory=list)
    total: int = 0


__all__ = [
    "TimelineNode",
    "TimelineLink",
    "TimelineResponse",
    "LoopContextItem",
    "LoopContextResponse",
]
