"""
HypothalamusModule 单元测试。
"""

import asyncio
import json

import pytest

from src.hypothalamus.module import HypothalamusModule
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class FakeDatabaseManager:
    """
    模拟数据库管理器，支持 life_state 与 habit 元数据操作。
    """

    def __init__(self):
        self.life_state = {}
        self.metadata = {}

    def get_life_state_daily(self, date):
        return self.life_state.get(date)

    def upsert_life_state_daily(self, **kwargs):
        date = kwargs.get("date")
        self.life_state[date] = {
            "date": date,
            "energy": kwargs.get("energy", 0.7),
            "mood": kwargs.get("mood", "平静"),
            "state_title": kwargs.get("state_title", "常态"),
            "health": kwargs.get("health", "健康"),
            "conditions": kwargs.get("conditions", []),
            "transition_options": kwargs.get("transition_options", []),
            "energy_delta": kwargs.get("energy_delta", 0.0),
        }
        return True

    def list_metadata_keys(self, prefix=""):
        return [k for k in self.metadata if k.startswith(prefix)]

    def get_metadata(self, key, default=None):
        return self.metadata.get(key, default)

    def set_metadata(self, key, value):
        self.metadata[key] = value


@pytest.fixture
def hypothalamus_module(monkeypatch):
    """
    使用 fake 数据库构造 HypothalamusModule 实例，并启用相关功能。
    """
    monkeypatch.setattr(
        "src.hypothalamus.state.life_state.ENABLE_LIFE_STATE", True
    )
    monkeypatch.setattr(
        "src.hypothalamus.habits.user_habits.ENABLE_USER_HABITS", True
    )
    monkeypatch.setattr(
        "src.hypothalamus.state.life_state.LLMHelper.call_tool_model",
        staticmethod(
            lambda **kwargs: json.dumps(
                [
                    {"name": "常态作息", "weight": 0.6,
                     "category": "作息", "note": "保持稳定"},
                    {"name": "天气适宜", "weight": 0.4,
                     "category": "环境", "note": "外部环境平稳"},
                ],
                ensure_ascii=False,
            )
        ),
    )

    router = CentralRouter()
    db = FakeDatabaseManager()
    module = HypothalamusModule(router, db_manager=db)
    router.register_module(module.module_id, module)
    yield module


def test_life_state_snapshot(hypothalamus_module):
    """
    测试 life_state_snapshot 通道。
    """
    module = hypothalamus_module
    router = module.router
    date = "2026-07-17"
    module._life_state.db.life_state[date] = {
        "date": date,
        "energy": 0.8,
        "mood": "愉快",
        "state_title": "常态",
        "health": "健康",
        "conditions": [],
        "transition_options": [],
        "energy_delta": 0.0,
    }

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="hypothalamus.homeostasis",
            packet_type=PacketType.REQUEST,
            channel="life_state_snapshot",
            payload={"now": f"{date}T10:00:00"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["date"] == date
        assert response.payload["energy"] == 0.8
        assert response.payload["mood"] == "愉快"
    finally:
        asyncio.run(router.shutdown())


def test_life_state_transition(hypothalamus_module):
    """
    测试 life_state_transition 通道。
    """
    module = hypothalamus_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        current = {
            "date": "2026-07-17",
            "energy": 0.7,
            "mood": "平静",
            "state_title": "常态",
            "health": "健康",
            "conditions": [],
            "transition_options": [
                {"trigger": "meal_missed", "target_state": "饥饿", "weight": 1.0},
            ],
        }
        packet = Packet(
            source="test.client",
            target="hypothalamus.homeostasis",
            packet_type=PacketType.REQUEST,
            channel="life_state_transition",
            payload={
                "current": current,
                "transition_options": current["transition_options"],
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["state_title"] == "饥饿"
        assert response.payload["last_transition_trigger"] == "meal_missed"
    finally:
        asyncio.run(router.shutdown())


def test_habit_update(hypothalamus_module):
    """
    测试 habit_update 通道。
    """
    module = hypothalamus_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="hypothalamus.homeostasis",
            packet_type=PacketType.REQUEST,
            channel="habit_update",
            payload={"user": "alice", "text": "我早起喝了咖啡"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        candidates = response.payload["candidates"]
        assert len(candidates) > 0
        categories = {c["category"] for c in candidates}
        assert "作息" in categories
        assert "饮食" in categories
    finally:
        asyncio.run(router.shutdown())


def test_habit_qualified(hypothalamus_module):
    """
    测试 habit_qualified 通道。
    """
    module = hypothalamus_module
    router = module.router
    db = module._db

    # 构造两条不同日期的相同习惯，满足 ≥2 自然日准入规则
    for date in ("2026-07-16", "2026-07-17"):
        db.set_metadata(
            f"habit_alice_饮食_{date}_0001",
            json.dumps(
                {"category": "饮食", "content": "喝咖啡",
                 "observed_date": date},
                ensure_ascii=False,
            ),
        )

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="hypothalamus.homeostasis",
            packet_type=PacketType.REQUEST,
            channel="habit_qualified",
            payload={"user": "alice"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        habits = response.payload["habits"]
        assert len(habits) == 1
        assert habits[0]["category"] == "饮食"
        assert habits[0]["content"] == "喝咖啡"
        assert len(habits[0]["observed_dates"]) == 2
    finally:
        asyncio.run(router.shutdown())


def test_hypothalamus_module_unknown_channel(hypothalamus_module):
    """
    测试 HypothalamusModule 处理未知通道。
    """
    module = hypothalamus_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="hypothalamus.homeostasis",
            packet_type=PacketType.REQUEST,
            channel="unknown_channel",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "unknown_channel"
        assert response.payload["channel"] == "unknown_channel"
    finally:
        asyncio.run(router.shutdown())
