"""
Schedule schemas - Pydantic v2 models for schedule endpoints.
日程相关的 Pydantic v2 模型。

Stage A.3: 为 /api/schedules/* 提供日程项/创建/更新的契约。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ScheduleDTO(BaseModel):
    """
    日程数据传输对象（只读视图）。
    Attributes:
        id: 日程主键
        title: 标题
        description: 详细描述
        start_time: ISO 8601 开始时间
        end_time: ISO 8601 结束时间（可选）
        priority: 优先级（low / normal / high）
        status: 状态（pending / done / cancelled）
        schedule_type: 类型（personal / work / birthday ...）
    """
    id: int
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    priority: str = "normal"
    status: str = "pending"
    schedule_type: str = "personal"


class ScheduleCreate(BaseModel):
    """
    创建日程请求。
    Attributes:
        title: 标题（必填，1-200 字符）
        description: 详细描述
        start_time: ISO 8601 开始时间
        end_time: ISO 8601 结束时间
        priority: 优先级
        schedule_type: 类型
    """
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_time: str
    end_time: Optional[str] = None
    priority: str = "normal"
    schedule_type: str = "personal"


class ScheduleUpdate(BaseModel):
    """
    更新日程请求（部分字段更新）。
    Attributes:
        id: 必填，待更新日程主键
        title / description / start_time / end_time / priority / status: 可选更新
    """
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


__all__ = ["ScheduleDTO", "ScheduleCreate", "ScheduleUpdate"]
