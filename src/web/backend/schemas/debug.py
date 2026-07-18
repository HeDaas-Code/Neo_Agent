"""
Debug schemas - Pydantic v2 models for debug log endpoints.
调试日志相关的 Pydantic v2 模型。

Stage B.5: 为 /api/debug/* 提供日志条目/列表响应契约。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DebugLogEntry(BaseModel):
    """
    调试日志条目。
    Attributes:
        timestamp: ISO 8601 时间戳
        module: 模块名
        level: 日志级别（INFO / WARN / ERROR / MODULE / PROMPT / REQUEST / RESPONSE）
        message: 消息主体（与 log_* 入口参数一致；可为空以便承载结构化日志）
        extra: 额外结构化数据（可包含 file_info / traceback / payload 等）
    """
    timestamp: str
    module: str
    level: str
    message: str = ""
    extra: Optional[Dict[str, Any]] = None


class DebugLogListResponse(BaseModel):
    """
    调试日志列表响应。
    Attributes:
        logs: 日志条目列表
        total: 总匹配条数
    """
    logs: List[DebugLogEntry] = Field(default_factory=list)
    total: int = 0


__all__ = [
    "DebugLogEntry",
    "DebugLogListResponse",
]
