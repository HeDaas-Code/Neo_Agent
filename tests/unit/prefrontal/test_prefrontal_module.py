"""
PrefrontalModule 单元测试。
"""

import asyncio

import pytest

from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType
from src.prefrontal.module import PrefrontalModule


class FakeSchedule:
    """
    模拟日程对象。
    """

    def __init__(self, schedule_id, title):
        self.schedule_id = schedule_id
        self.title = title

    def to_dict(self):
        return {"schedule_id": self.schedule_id, "title": self.title}


class FakeEvent:
    """
    模拟事件对象。
    """

    def __init__(self, event_id, title):
        self.event_id = event_id
        self.title = title

    def to_dict(self):
        return {"event_id": self.event_id, "title": self.title}


class FakeScheduleManager:
    """
    模拟日程管理器。
    """

    def __init__(self, db_manager=None):
        self.schedules = [
            FakeSchedule("s1", "测试日程 1"),
            FakeSchedule("s2", "测试日程 2"),
        ]
        self.deleted = []
        self.added = []

    def list_schedules(self, **kwargs):
        return self.schedules

    def add_schedule(self, **kwargs):
        schedule = FakeSchedule("new-sid", kwargs.get("title", "新日程"))
        self.added.append(schedule)
        return True, schedule, "日程创建成功"

    def delete_schedule(self, schedule_id):
        self.deleted.append(schedule_id)
        return True


class FakeProactiveEngine:
    """
    模拟主动决策引擎。
    """

    def __init__(self, db_manager=None, event_manager=None):
        self.should_send_result = (True, "pass")
        self.scheduled = []

    def should_send(self, user, now=None):
        return self.should_send_result

    def schedule_next_proactive(self, user, now=None, delay_hours=None):
        self.scheduled.append({"user": user, "delay_hours": delay_hours})


class FakeEventManager:
    """
    模拟事件管理器。
    """

    def __init__(self, db_manager=None):
        self.events = [
            FakeEvent("e1", "测试事件 1"),
            FakeEvent("e2", "测试事件 2"),
        ]
        self.added = []

    def get_events(self, status=None, event_type=None, limit=100):
        return self.events[:limit]

    def add_event(self, **kwargs):
        event = FakeEvent("new-eid", kwargs.get("title", "新事件"))
        self.added.append(event)
        return event


@pytest.fixture
def prefrontal_module(monkeypatch):
    """
    使用 fake 管理器构造 PrefrontalModule 实例。
    """
    monkeypatch.setattr(
        "src.prefrontal.module.ScheduleManager", FakeScheduleManager
    )
    monkeypatch.setattr(
        "src.prefrontal.module.EventManager", FakeEventManager
    )
    monkeypatch.setattr(
        "src.prefrontal.module.ProactiveEngine", FakeProactiveEngine
    )

    router = CentralRouter()
    module = PrefrontalModule(router)
    router.register_module(module.module_id, module)
    yield module


def test_prefrontal_module_schedule_list(prefrontal_module):
    """
    测试 schedule_list 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="schedule_list",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["total"] == 2
        assert response.payload["schedules"][0]["schedule_id"] == "s1"
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_schedule_add(prefrontal_module):
    """
    测试 schedule_add 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="schedule_add",
            payload={
                "title": "新增测试日程",
                "description": "描述",
                "schedule_type": "appointment",
                "start_time": "2024-01-01T10:00:00",
                "end_time": "2024-01-01T11:00:00",
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["success"] is True
        assert response.payload["schedule"]["schedule_id"] == "new-sid"
        assert len(module._schedule_manager.added) == 1
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_schedule_delete(prefrontal_module):
    """
    测试 schedule_delete 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="schedule_delete",
            payload={"schedule_id": "s1"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["deleted"] is True
        assert "s1" in module._schedule_manager.deleted
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_schedule_delete_missing_id(prefrontal_module):
    """
    测试 schedule_delete 通道缺少 schedule_id 时返回错误。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="schedule_delete",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_error()
        assert response.payload["code"] == "INVALID_REQUEST"
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_proactive_should_send(prefrontal_module):
    """
    测试 proactive_should_send 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="proactive_should_send",
            payload={"user": "alice"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["should_send"] is True
        assert response.payload["reason"] == "pass"
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_proactive_schedule_next(prefrontal_module):
    """
    测试 proactive_schedule_next 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="proactive_schedule_next",
            payload={"user": "alice", "delay_hours": 3.5},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "scheduled"
        assert module._proactive_engine.scheduled[0]["user"] == "alice"
        assert module._proactive_engine.scheduled[0]["delay_hours"] == 3.5
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_event_list(prefrontal_module):
    """
    测试 event_list 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="event_list",
            payload={"status": "pending"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["total"] == 2
        assert response.payload["events"][0]["event_id"] == "e1"
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_event_add(prefrontal_module):
    """
    测试 event_add 通道。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="event_add",
            payload={
                "title": "新增测试事件",
                "description": "描述",
                "event_type": "notification",
                "priority": 2,
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["event_id"] == "new-eid"
        assert len(module._event_manager.added) == 1
    finally:
        asyncio.run(router.shutdown())


def test_prefrontal_module_unknown_channel(prefrontal_module):
    """
    测试未知通道处理。
    """
    module = prefrontal_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="unknown_channel",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "unknown_channel"
    finally:
        asyncio.run(router.shutdown())
