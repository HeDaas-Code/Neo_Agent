"""
HippocampusModule - 海马体模块（v4.0 神经系统接入层）。

将 src.limbic.hippocampus 中的记忆、会话、知识库能力包装为 BaseModule，
使其可以通过 CentralRouter 被其他模块调用。

module_id: limbic.hippocampus.full，提供持久化记忆、会话与知识库能力。
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

from src.core.database_manager import DatabaseManager
from src.limbic.hippocampus.knowledge_store import KnowledgeBase
from src.limbic.hippocampus.memory_store import LongTermMemoryManager
from src.limbic.hippocampus.session_store import SessionStore
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


class HippocampusModule(BaseModule):
    """
    完整版海马体模块。

    负责持久化会话、短期/长期记忆、知识库查询。
    """

    module_id = "limbic.hippocampus.full"
    module_type = "limbic"

    def __init__(self, router: "CentralRouter", db_manager: DatabaseManager | None = None) -> None:
        super().__init__(router)
        self._db = db_manager or DatabaseManager()
        self._session_store = SessionStore(self._db)
        self._memory_manager: LongTermMemoryManager | None = None
        self._knowledge_base: KnowledgeBase | None = None
        # 高频通道内存缓存（memory_query / memory_context / memory_stats）
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._cache_ttl_seconds = 5.0

    async def initialize(self) -> None:
        self._memory_manager = LongTermMemoryManager(db_manager=self._db)
        self._knowledge_base = KnowledgeBase(db_manager=self._db)
        await super().initialize()

    async def shutdown(self) -> None:
        self._memory_manager = None
        self._knowledge_base = None
        await super().shutdown()

    # ------------------------------------------------------------------
    # 缓存层 helpers
    # ------------------------------------------------------------------
    def _cache_key(self, channel: str, payload: Dict[str, Any]) -> str:
        """基于通道与 payload 构造缓存 key（忽略 trace_id 等元数据）。"""
        items = sorted(
            (k, v) for k, v in payload.items()
            if k not in ("trace_id", "timestamp", "metadata")
        )
        return f"{channel}:{items}"

    def _get_cached(self, key: str) -> Optional[Any]:
        """读取缓存，过期返回 None 并清理。"""
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.time() - ts > self._cache_ttl_seconds:
            self._cache.pop(key, None)
            return None
        return value

    def _set_cached(self, key: str, value: Any) -> None:
        """写入缓存。"""
        self._cache[key] = (time.time(), value)

    def _invalidate_memory_cache(self) -> None:
        """记忆写入后使相关读取缓存失效。"""
        prefixes = ("memory_query:", "memory_context:", "memory_stats:")
        for key in list(self._cache.keys()):
            if key.startswith(prefixes):
                self._cache.pop(key, None)

    async def handle(self, packet: Packet) -> Packet:
        """
        处理记忆、会话、知识库相关请求。

        Channels:
            - memory_query: 查询相关记忆
            - memory_store: 存储消息
            - memory_context: 获取聊天上下文字符串
            - memory_stats: 获取记忆统计
            - session_create/list/get/delete/update_title
            - message_add/list
        """
        channel = packet.channel
        payload = packet.payload

        if channel == "memory_query":
            return self._handle_memory_query(packet, payload)
        if channel == "memory_store":
            return self._handle_memory_store(packet, payload)
        if channel == "memory_context":
            return self._handle_memory_context(packet, payload)
        if channel == "memory_stats":
            return self._handle_memory_stats(packet, payload)
        if channel == "session_create":
            return self._handle_session_create(packet, payload)
        if channel == "session_list":
            return self._handle_session_list(packet, payload)
        if channel == "session_get":
            return self._handle_session_get(packet, payload)
        if channel == "session_delete":
            return self._handle_session_delete(packet, payload)
        if channel == "session_update_title":
            return self._handle_session_update_title(packet, payload)
        if channel == "message_add":
            return self._handle_message_add(packet, payload)
        if channel == "message_list":
            return self._handle_message_list(packet, payload)

        return packet.response({
            "status": "unknown_channel",
            "channel": channel,
        })

    def _handle_memory_query(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        if self._memory_manager is None:
            return packet.error("HippocampusModule not initialized", code="NOT_INITIALIZED")

        key = self._cache_key("memory_query", payload)
        cached = self._get_cached(key)
        if cached is not None:
            return packet.response(cached)

        limit = payload.get("limit", 10)
        messages = self._memory_manager.get_recent_messages(count=limit)
        result = {
            "memories": messages,
            "total": len(messages),
        }
        self._set_cached(key, result)
        return packet.response(result)

    def _handle_memory_store(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        if self._memory_manager is None:
            return packet.error("HippocampusModule not initialized", code="NOT_INITIALIZED")

        role = payload.get("role", "user")
        content = payload.get("content", "")
        self._memory_manager.add_message(role, content)
        self._invalidate_memory_cache()
        return packet.response({"status": "stored"})

    def _handle_memory_context(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        if self._memory_manager is None:
            return packet.error("HippocampusModule not initialized", code="NOT_INITIALIZED")

        key = self._cache_key("memory_context", payload)
        cached = self._get_cached(key)
        if cached is not None:
            return packet.response(cached)

        context = self._memory_manager.get_context_for_chat(
            recent_count=payload.get("recent_count", 10)
        )
        result = {"context": context}
        self._set_cached(key, result)
        return packet.response(result)

    def _handle_memory_stats(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        if self._memory_manager is None:
            return packet.error("HippocampusModule not initialized", code="NOT_INITIALIZED")

        key = self._cache_key("memory_stats", payload)
        cached = self._get_cached(key)
        if cached is not None:
            return packet.response(cached)

        stats = self._memory_manager.get_statistics()
        self._set_cached(key, stats)
        return packet.response(stats)

    def _handle_session_create(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        user_id = payload.get("user_id", "default")
        title = payload.get("title", "新会话")
        session_id = self._session_store.create(user_id, title)
        return packet.response({"session_id": session_id})

    def _handle_session_list(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        user_id = payload.get("user_id", "default")
        sessions = self._session_store.list(
            user_id,
            limit=payload.get("limit", 50),
            offset=payload.get("offset", 0),
        )
        return packet.response({"sessions": sessions})

    def _handle_session_get(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        session_id = payload.get("session_id")
        if session_id is None:
            return packet.error("session_id required", code="INVALID_REQUEST")
        session = self._session_store.get(int(session_id))
        return packet.response({"session": session})

    def _handle_session_delete(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        session_id = payload.get("session_id")
        if session_id is None:
            return packet.error("session_id required", code="INVALID_REQUEST")
        deleted = self._session_store.delete(int(session_id))
        return packet.response({"deleted": deleted})

    def _handle_session_update_title(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        session_id = payload.get("session_id")
        title = payload.get("title")
        if session_id is None or title is None:
            return packet.error("session_id and title required", code="INVALID_REQUEST")
        updated = self._session_store.update_title(int(session_id), title)
        return packet.response({"updated": updated})

    def _handle_message_add(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        session_id = payload.get("session_id")
        role = payload.get("role", "user")
        content = payload.get("content", "")
        if session_id is None:
            return packet.error("session_id required", code="INVALID_REQUEST")
        message_id = self._session_store.add_message(
            int(session_id), role, content,
            emotion_json=payload.get("emotion_json"),
            conn_id=payload.get("conn_id"),
        )
        return packet.response({"message_id": message_id})

    def _handle_message_list(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        session_id = payload.get("session_id")
        if session_id is None:
            return packet.error("session_id required", code="INVALID_REQUEST")
        messages = self._session_store.list_messages(
            int(session_id),
            limit=payload.get("limit", 200),
            before_id=payload.get("before_id"),
        )
        return packet.response({"messages": messages})


__all__ = ["HippocampusModule"]
