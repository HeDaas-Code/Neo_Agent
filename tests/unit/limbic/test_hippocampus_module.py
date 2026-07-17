"""
HippocampusModule 单元测试。
"""

import asyncio

import pytest

from src.limbic.hippocampus.module import HippocampusModule
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class FakeMemoryManager:
    """
    模拟长效记忆管理器。
    """

    def __init__(self, db_manager=None):
        self.messages = []
        self.query_count = 0
        self.context_count = 0
        self.stats_count = 0

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})

    def get_recent_messages(self, count=10):
        self.query_count += 1
        return self.messages[-count:]

    def get_context_for_chat(self, recent_count=10):
        self.context_count += 1
        return "fake context"

    def get_statistics(self):
        self.stats_count += 1
        return {"short_term": {"rounds": len(self.messages)}}


class FakeSessionStore:
    """
    模拟会话存储。
    """

    def __init__(self, db_manager=None):
        self.sessions = {}
        self.messages = {}
        self._next_id = 1

    def create(self, user_id, title="新会话"):
        sid = self._next_id
        self._next_id += 1
        self.sessions[sid] = {"id": sid, "user_id": user_id, "title": title}
        return sid

    def list(self, user_id, limit=50, offset=0):
        return [s for s in self.sessions.values() if s["user_id"] == user_id]

    def get(self, session_id):
        return self.sessions.get(session_id)

    def delete(self, session_id):
        return self.sessions.pop(session_id, None) is not None

    def update_title(self, session_id, title):
        if session_id in self.sessions:
            self.sessions[session_id]["title"] = title
            return True
        return False

    def add_message(self, session_id, role, content, emotion_json=None, conn_id=None):
        mid = self._next_id
        self._next_id += 1
        self.messages.setdefault(session_id, []).append({
            "id": mid, "role": role, "content": content,
        })
        return mid

    def list_messages(self, session_id, limit=200, before_id=None):
        return self.messages.get(session_id, [])


class FakeKnowledgeBase:
    """
    模拟知识库。
    """

    def __init__(self, db_manager=None, **kwargs):
        pass


def test_hippocampus_module_session_create(monkeypatch):
    """
    测试 HippocampusModule 处理 session_create 通道。
    """
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.LongTermMemoryManager", FakeMemoryManager
    )
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.KnowledgeBase", FakeKnowledgeBase
    )

    router = CentralRouter()
    module = HippocampusModule(router)
    module._session_store = FakeSessionStore()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="session_create",
            payload={"user_id": "alice", "title": "测试会话"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["session_id"] == 1
    finally:
        asyncio.run(router.shutdown())


def test_hippocampus_module_memory_store(monkeypatch):
    """
    测试 HippocampusModule 处理 memory_store 通道。
    """
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.LongTermMemoryManager", FakeMemoryManager
    )
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.KnowledgeBase", FakeKnowledgeBase
    )

    router = CentralRouter()
    module = HippocampusModule(router)
    module._session_store = FakeSessionStore()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="memory_store",
            payload={"role": "user", "content": "你好"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "stored"
        assert len(module._memory_manager.messages) == 1
    finally:
        asyncio.run(router.shutdown())


def test_hippocampus_module_message_add(monkeypatch):
    """
    测试 HippocampusModule 处理 message_add 通道。
    """
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.LongTermMemoryManager", FakeMemoryManager
    )
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.KnowledgeBase", FakeKnowledgeBase
    )

    router = CentralRouter()
    module = HippocampusModule(router)
    module._session_store = FakeSessionStore()
    session_id = module._session_store.create("alice")

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="message_add",
            payload={"session_id": session_id, "role": "user", "content": "你好"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["message_id"] == 2
    finally:
        asyncio.run(router.shutdown())


def test_hippocampus_module_unknown_channel(monkeypatch):
    """
    测试 HippocampusModule 处理未知通道。
    """
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.LongTermMemoryManager", FakeMemoryManager
    )
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.KnowledgeBase", FakeKnowledgeBase
    )

    router = CentralRouter()
    module = HippocampusModule(router)
    module._session_store = FakeSessionStore()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="unknown_channel",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "unknown_channel"
    finally:
        asyncio.run(router.shutdown())


def test_hippocampus_module_memory_query_cache(monkeypatch):
    """
    测试 memory_query 在 TTL 内命中缓存，不重复查询底层 memory_manager。
    """
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.LongTermMemoryManager", FakeMemoryManager
    )
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.KnowledgeBase", FakeKnowledgeBase
    )

    router = CentralRouter()
    module = HippocampusModule(router)
    module._session_store = FakeSessionStore()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="memory_query",
            payload={"limit": 5},
        )
        response1 = asyncio.run(router.route(packet))
        response2 = asyncio.run(router.route(packet))

        assert response1.is_response()
        assert response2.is_response()
        assert response1.payload == response2.payload
        # 底层只应被调用一次
        assert module._memory_manager.query_count == 1
    finally:
        asyncio.run(router.shutdown())


def test_hippocampus_module_memory_store_invalidates_cache(monkeypatch):
    """
    测试 memory_store 会使 memory_query 缓存失效。
    """
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.LongTermMemoryManager", FakeMemoryManager
    )
    monkeypatch.setattr(
        "src.limbic.hippocampus.module.KnowledgeBase", FakeKnowledgeBase
    )

    router = CentralRouter()
    module = HippocampusModule(router)
    module._session_store = FakeSessionStore()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        query_packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="memory_query",
            payload={"limit": 5},
        )
        asyncio.run(router.route(query_packet))

        store_packet = Packet(
            source="test.client",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="memory_store",
            payload={"role": "user", "content": "新消息"},
        )
        asyncio.run(router.route(store_packet))

        asyncio.run(router.route(query_packet))

        # 写入后缓存失效，应再次查询底层
        assert module._memory_manager.query_count == 2
    finally:
        asyncio.run(router.shutdown())
