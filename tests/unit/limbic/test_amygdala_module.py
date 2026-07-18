"""
AmygdalaModule 单元测试。
"""

import asyncio

import pytest

from src.limbic.amygdala.module import AmygdalaModule
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class FakeAnalyzer:
    """
    模拟情感分析器。
    """

    def __init__(self):
        self.latest = None
        self.trend = []

    def analyze_emotion_relationship(self, messages, character_name="AI",
                                     character_settings="", is_initial=None):
        return {
            "impression": "fake impression",
            "overall_score": 25,
            "relationship_type": "朋友",
            "emotional_tone": "积极",
            "is_initial": True,
        }

    def get_latest_for_user(self, user_id="default"):
        if self.latest is None:
            self.latest = {
                "timestamp": "2024-01-01T00:00:00",
                "additive_scores": {"joy": 60},
                "plutchik": {"joy": 0.6},
                "dominant": "喜悦",
            }
        return self.latest

    def get_emotion_trend(self):
        return self.trend

    def generate_tone_prompt(self):
        return "【当前情感关系状态】\nfake tone prompt"


def test_amygdala_module_analyze():
    """
    测试 AmygdalaModule 处理 emotion_analyze 通道。
    """
    router = CentralRouter()
    module = AmygdalaModule(router)
    module._analyzer = FakeAnalyzer()
    module._wheel = object()  # 不需要真实初始化

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())
        # router.initialize() 会调用 module.initialize() 创建真实 analyzer，
        # 测试里替换回 fake 避免真实 LLM 调用。
        module._analyzer = FakeAnalyzer()

        packet = Packet(
            source="test.client",
            target="limbic.amygdala",
            packet_type=PacketType.REQUEST,
            channel="emotion_analyze",
            payload={
                "messages": [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "你好呀"},
                ],
                "character_name": "Neo",
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["overall_score"] == 25
        assert response.payload["relationship_type"] == "朋友"
    finally:
        asyncio.run(router.shutdown())


def test_amygdala_module_latest():
    """
    测试 AmygdalaModule 处理 emotion_latest 通道。
    """
    router = CentralRouter()
    module = AmygdalaModule(router)
    module._analyzer = FakeAnalyzer()
    module._wheel = object()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.amygdala",
            packet_type=PacketType.REQUEST,
            channel="emotion_latest",
            payload={"user_id": "default"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["dominant"] == "喜悦"
    finally:
        asyncio.run(router.shutdown())


def test_amygdala_module_wheel_profile():
    """
    测试 AmygdalaModule 处理 emotion_wheel_profile 通道。
    """
    router = CentralRouter()
    module = AmygdalaModule(router)
    module._analyzer = None

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.amygdala",
            packet_type=PacketType.REQUEST,
            channel="emotion_wheel_profile",
            payload={
                "emotions": {
                    "joy": 0.8,
                    "trust": 0.2,
                    "fear": 0.0,
                    "surprise": 0.0,
                    "sadness": 0.0,
                    "disgust": 0.0,
                    "anger": 0.0,
                    "anticipation": 0.3,
                }
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["primary"] == "喜悦"
        assert response.payload["intensity"] > 0
    finally:
        asyncio.run(router.shutdown())


def test_amygdala_module_unknown_channel():
    """
    测试 AmygdalaModule 处理未知通道。
    """
    router = CentralRouter()
    module = AmygdalaModule(router)
    module._analyzer = FakeAnalyzer()
    module._wheel = object()

    try:
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="limbic.amygdala",
            packet_type=PacketType.REQUEST,
            channel="unknown_channel",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "unknown_channel"
    finally:
        asyncio.run(router.shutdown())
