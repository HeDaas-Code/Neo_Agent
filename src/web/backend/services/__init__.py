"""
Services package - 统一导出所有 service 及其全局单例。
Services package - re-export all services and their singletons.

Stage A.3: 供 /api/* 路由 / main.py 统一导入：
    from src.web.backend.services import chat_service, database_service, event_service

Stage B.3: 新增 emotion_service（情感雷达后端）。
"""

from __future__ import annotations

from .chat_service import ChatService, chat_service
from .creative_service import CreativeService, creative_service
from .database_service import DatabaseService, database_service
from .emotion_service import EmotionService, emotion_service
from .event_service import EventService, event_service

__all__ = [
    "ChatService",
    "chat_service",
    "CreativeService",
    "creative_service",
    "DatabaseService",
    "database_service",
    "EmotionService",
    "emotion_service",
    "EventService",
    "event_service",
]
