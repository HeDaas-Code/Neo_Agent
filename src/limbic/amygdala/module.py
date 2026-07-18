"""
AmygdalaModule - 杏仁核模块（v4.0 神经系统接入层）。

将 src.limbic.amygdala.emotion_state 中的情感分析能力包装为 BaseModule，
使其可以通过 CentralRouter 被其他模块调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from src.limbic.amygdala.emotion_state import (
    EmotionRelationshipAnalyzer,
    PlutchikEmotionWheel,
)
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


class AmygdalaModule(BaseModule):
    """
    杏仁核模块。

    负责情感关系分析（累加评分）和当下情绪（Plutchik 8 维）。
    """

    module_id = "limbic.amygdala"
    module_type = "limbic"

    def __init__(self, router: "CentralRouter") -> None:
        super().__init__(router)
        self._analyzer: EmotionRelationshipAnalyzer | None = None
        self._wheel: PlutchikEmotionWheel | None = None

    async def initialize(self) -> None:
        self._analyzer = EmotionRelationshipAnalyzer()
        self._wheel = PlutchikEmotionWheel()
        await super().initialize()

    async def shutdown(self) -> None:
        self._analyzer = None
        self._wheel = None
        await super().shutdown()

    async def handle(self, packet: Packet) -> Packet:
        """
        处理情感相关请求。

        Channels:
            - emotion_analyze: 分析对话情感关系
            - emotion_latest: 获取最新情感数据
            - emotion_trend: 获取情感趋势
            - emotion_tone: 生成语气提示
            - emotion_wheel_profile: 从 8 维情绪推导 profile
        """
        channel = packet.channel
        payload = packet.payload

        if channel == "emotion_analyze":
            return self._handle_analyze(packet, payload)
        if channel == "emotion_latest":
            return self._handle_latest(packet, payload)
        if channel == "emotion_trend":
            return self._handle_trend(packet, payload)
        if channel == "emotion_tone":
            return self._handle_tone(packet, payload)
        if channel == "emotion_wheel_profile":
            return self._handle_wheel_profile(packet, payload)

        return packet.response({
            "status": "unknown_channel",
            "channel": channel,
        })

    def _handle_analyze(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        messages: List[Dict[str, str]] = payload.get("messages", [])
        character_name: str = payload.get("character_name", "AI")
        character_settings: str = payload.get("character_settings", "")
        is_initial = payload.get("is_initial")

        if self._analyzer is None:
            return packet.error("AmygdalaModule not initialized", code="NOT_INITIALIZED")

        result = self._analyzer.analyze_emotion_relationship(
            messages=messages,
            character_name=character_name,
            character_settings=character_settings,
            is_initial=is_initial,
        )
        return packet.response(result)

    def _handle_latest(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        if self._analyzer is None:
            return packet.error("AmygdalaModule not initialized", code="NOT_INITIALIZED")

        user_id: str = payload.get("user_id", "default")
        result = self._analyzer.get_latest_for_user(user_id)
        return packet.response(result)

    def _handle_trend(self, packet: Packet, _payload: Dict[str, Any]) -> Packet:
        if self._analyzer is None:
            return packet.error("AmygdalaModule not initialized", code="NOT_INITIALIZED")

        result = self._analyzer.get_emotion_trend()
        return packet.response({"trend": result})

    def _handle_tone(self, packet: Packet, _payload: Dict[str, Any]) -> Packet:
        if self._analyzer is None:
            return packet.error("AmygdalaModule not initialized", code="NOT_INITIALIZED")

        result = self._analyzer.generate_tone_prompt()
        return packet.response({"tone_prompt": result})

    def _handle_wheel_profile(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        emotions: Dict[str, float] = payload.get("emotions", {})
        if self._wheel is None:
            return packet.error("AmygdalaModule not initialized", code="NOT_INITIALIZED")

        profile = self._wheel.profile_from_basic(emotions)
        return packet.response(profile)


__all__ = ["AmygdalaModule"]
