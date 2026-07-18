"""
HypothalamusModule - 下丘脑模块（v4.0 神经系统接入层）。

将 src.hypothalamus.state.life_state、src.hypothalamus.habits.user_habits
中的内稳态与用户习惯能力包装为 BaseModule，使其可以通过 CentralRouter
被其他模块调用。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from src.core.database_manager import DatabaseManager
from src.hypothalamus.habits.user_habits import UserHabitTracker
from src.hypothalamus.state.life_state import LifeStateManager
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """将 ISO 格式字符串解析为 datetime，失败时返回 None。"""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


class HypothalamusModule(BaseModule):
    """
    下丘脑模块。

    负责内稳态、生理节律、生命状态、用户行为习惯。
    """

    module_id = "hypothalamus.homeostasis"
    module_type = "hypothalamus"

    def __init__(
        self,
        router: "CentralRouter",
        db_manager: Optional[DatabaseManager] = None,
        character_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(router)
        self._db = db_manager or DatabaseManager()
        self._life_state = LifeStateManager(
            db_manager=self._db,
            character_info=character_info,
        )
        self._habits = UserHabitTracker(db_manager=self._db)

    async def handle(self, packet: Packet) -> Packet:
        """
        处理下丘脑相关请求。

        Channels:
            - life_state_ensure: 确保当日状态存在
            - life_state_snapshot: 获取当前状态快照
            - life_state_transition: 应用状态转移
            - life_state_prompt: 渲染状态为 prompt
            - life_state_body_cycle: 计算生理周期
            - life_state_consume_dream_delta: 消费梦境能量差值
            - habit_update: 从用户消息更新习惯候选
            - habit_qualified: 获取已确认习惯
            - habit_proactive_event: 触发习惯主动事件
            - habit_format_schedule: 渲染习惯为 schedule 格式
        """
        channel = packet.channel
        payload = packet.payload

        try:
            if channel == "life_state_ensure":
                return self._handle_life_state_ensure(packet, payload)
            if channel == "life_state_snapshot":
                return self._handle_life_state_snapshot(packet, payload)
            if channel == "life_state_transition":
                return self._handle_life_state_transition(packet, payload)
            if channel == "life_state_prompt":
                return self._handle_life_state_prompt(packet, payload)
            if channel == "life_state_body_cycle":
                return self._handle_life_state_body_cycle(packet, payload)
            if channel == "life_state_consume_dream_delta":
                return self._handle_life_state_consume_dream_delta(packet, payload)
            if channel == "habit_update":
                return self._handle_habit_update(packet, payload)
            if channel == "habit_qualified":
                return self._handle_habit_qualified(packet, payload)
            if channel == "habit_proactive_event":
                return self._handle_habit_proactive_event(packet, payload)
            if channel == "habit_format_schedule":
                return self._handle_habit_format_schedule(packet, payload)
        except Exception as e:
            return Packet.error(packet, str(e), "HYPOTHALAMUS_ERROR")

        return packet.response({
            "status": "unknown_channel",
            "channel": channel,
        })

    def _handle_life_state_ensure(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        force = payload.get("force", False)
        weather = payload.get("weather")
        now = _parse_datetime(payload.get("now"))
        result = self._life_state.ensure_daily_state(
            force=force, weather=weather, now=now
        )
        return packet.response(result)

    def _handle_life_state_snapshot(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        now = _parse_datetime(payload.get("now"))
        result = self._life_state.get_current_state_snapshot(now=now)
        return packet.response(result)

    def _handle_life_state_transition(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        current = payload.get("current", {})
        transition_options = payload.get("transition_options")
        result = self._life_state.apply_transition(
            current=current, transition_options=transition_options
        )
        return packet.response(result)

    def _handle_life_state_prompt(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        now = _parse_datetime(payload.get("now"))
        prompt = self._life_state.format_state_for_prompt(now=now)
        return packet.response({"prompt": prompt})

    def _handle_life_state_body_cycle(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        character_info = payload.get("character_info")
        now = _parse_datetime(payload.get("now"))
        result = self._life_state.body_cycle(
            character_info=character_info, now=now
        )
        return packet.response(result)

    def _handle_life_state_consume_dream_delta(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        energy_delta = payload.get("energy_delta", 0.0)
        self._life_state.consume_dream_energy_delta(energy_delta)
        return packet.response({"status": "ok"})

    def _handle_habit_update(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        user = payload.get("user", "")
        text = payload.get("text", "")
        candidates = self._habits.update_from_message(user=user, text=text)
        return packet.response({"candidates": candidates})

    def _handle_habit_qualified(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        user = payload.get("user", "")
        habits = self._habits.qualified_habits(user=user)
        return packet.response({"habits": habits})

    def _handle_habit_proactive_event(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        user = payload.get("user", "")
        now = _parse_datetime(payload.get("now"))
        event = self._habits.habit_proactive_event(user=user, now=now)
        return packet.response({"event": event})

    def _handle_habit_format_schedule(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        limit = payload.get("limit", 8)
        prompt = self._habits.format_for_schedule(limit=limit)
        return packet.response({"prompt": prompt})
