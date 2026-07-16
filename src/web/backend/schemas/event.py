"""
Event schemas - Pydantic v2 models for event listing.
事件查询相关的 Pydantic v2 模型。

Stage A.3: 为 /api/events 提供事件列表的契约。

F.7.2: 为对齐实际 events 表（event_id / event_type / source / tags），
新增可选字段并保持原 uuid / type 向后兼容。Pydantic v2 用
``model_config = ConfigDict(populate_by_name=True)`` 同时接受旧字段。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EventDTO(BaseModel):
    """
    事件数据传输对象。
    Attributes:
        uuid: 事件唯一标识（旧版别名，建议新代码使用 event_id）
        type: 事件类型（旧版别名，建议新代码使用 event_type）
        status: 事件状态（如 'pending' / 'sent' / 'failed'）
        payload: 事件 payload 字典
        created_at: ISO 8601 时间戳

    扩展字段（F.7.2，对齐 events 表）：
        event_id: 实际表主键，Optional[str] = None
        event_type: 实际表的 event_type 列，Optional[str] = None
        source: 事件来源（如 'scheduler' / 'proactive' / 'manual'），Optional[str] = None
        tags: 标签列表，Optional[List[str]] = None
    """
    # 旧字段（保持向后兼容，client 仍在用）
    uuid: str
    type: str
    status: str
    payload: Dict
    created_at: str

    # 新增字段（对齐实际表，原 uuid 字段保留）
    event_id: Optional[str] = Field(
        default=None,
        description="events.event_id 主键；为对齐实际表而扩展，uuid 仍可用",
    )
    event_type: Optional[str] = Field(
        default=None,
        description="events.event_type 列；为对齐实际表而扩展，type 仍可用",
    )
    source: Optional[str] = Field(
        default=None,
        description="事件来源（scheduler / proactive / manual / ...）",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="事件标签列表（events.metadata JSON 内的 tags 字段）",
    )

    model_config = ConfigDict(populate_by_name=True)


class EventListResponse(BaseModel):
    """
    事件列表响应。
    Attributes:
        events: 事件列表
        total: 总条数（用于分页）
    """
    events: List[EventDTO]
    total: int


__all__ = ["EventDTO", "EventListResponse"]
