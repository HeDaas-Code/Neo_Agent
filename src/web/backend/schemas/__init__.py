"""
Schemas package - 统一导出所有 Pydantic v2 模型。
Schemas package - re-export all Pydantic v2 models.

Stage A.3: 供 /api/* 路由按需导入：
    from src.web.backend.schemas import ChatRequest, ChatResponse

Stage B.3: 新增 EmotionResponse（情感雷达响应）。
"""

from __future__ import annotations

from .chat import ChatChunk, ChatRequest, ChatResponse
from .creative import (
    AdvanceRequest,
    AdvanceResponse,
    Chapter,
    Character,
    CharacterRelation,
    CreativeAdvanceRequest,
    CreativeAdvanceResponse,
    CreativeProject,
    CreativeProjectCreate,
    CreativeProjectDetail,
    CreativeProjectListResponse,
    CreativeProjectSummary,
    StoryBible,
)
from .database import (
    CountResponse,
    DeleteResponse,
    TableDataResponse,
    TablesListResponse,
)
from .emotion import EmotionLatestResponse, EmotionResponse, PLUTCHIK_KEYS
from .event import EventDTO, EventListResponse
from .knowledge import (
    KnowledgeDefinition,
    KnowledgeEntity,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from .memory import (
    LoopContextItem,
    LoopContextResponse,
    TimelineLink,
    TimelineNode,
    TimelineResponse,
)
from .schedule import ScheduleCreate, ScheduleDTO, ScheduleUpdate

__all__ = [
    "ChatRequest",
    "ChatChunk",
    "ChatResponse",
    "CountResponse",
    "CreativeProject",
    "CreativeProjectCreate",
    "CreativeProjectListResponse",
    "CreativeProjectSummary",
    "CreativeProjectDetail",
    "CreativeAdvanceRequest",
    "CreativeAdvanceResponse",
    "AdvanceRequest",
    "AdvanceResponse",
    "StoryBible",
    "Character",
    "CharacterRelation",
    "Chapter",
    "DeleteResponse",
    "EmotionResponse",
    "EmotionLatestResponse",
    "PLUTCHIK_KEYS",
    "EventDTO",
    "EventListResponse",
    "KnowledgeEntity",
    "KnowledgeDefinition",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "TableDataResponse",
    "TablesListResponse",
    "TimelineNode",
    "TimelineLink",
    "TimelineResponse",
    "LoopContextItem",
    "LoopContextResponse",
    "ScheduleDTO",
    "ScheduleCreate",
    "ScheduleUpdate",
]
