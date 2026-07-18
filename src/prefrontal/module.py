"""
PrefrontalModule - 前额叶模块（v4.0 神经系统接入层）。

将 src.prefrontal.schedule、src.prefrontal.proactive、src.prefrontal.event
中的规划与决策能力包装为 BaseModule，使其可以通过 CentralRouter 被其他模块调用。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.core.database_manager import DatabaseManager
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet
from src.prefrontal.event.event_manager import (
    Event,
    EventManager,
    EventPriority,
    EventStatus,
    EventType,
)
from src.prefrontal.proactive.proactive_engine import ProactiveEngine
from src.prefrontal.schedule.schedule_manager import (
    Schedule,
    ScheduleManager,
    SchedulePriority,
    ScheduleType,
)

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


def _coerce_schedule_type(value: Any) -> Any:
    """若 value 为字符串，则转换为 ScheduleType 枚举。"""
    if isinstance(value, str):
        try:
            return ScheduleType(value)
        except ValueError:
            return value
    return value


def _coerce_schedule_priority(value: Any) -> Any:
    """若 value 为整数/字符串，则转换为 SchedulePriority 枚举。"""
    if isinstance(value, int):
        try:
            return SchedulePriority(value)
        except ValueError:
            return value
    if isinstance(value, str):
        try:
            return SchedulePriority(int(value))
        except (ValueError, TypeError):
            return value
    return value


def _coerce_event_type(value: Any) -> Any:
    """若 value 为字符串，则转换为 EventType 枚举。"""
    if isinstance(value, str):
        try:
            return EventType(value)
        except ValueError:
            return value
    return value


def _coerce_event_priority(value: Any) -> Any:
    """若 value 为整数/字符串，则转换为 EventPriority 枚举。"""
    if isinstance(value, int):
        try:
            return EventPriority(value)
        except ValueError:
            return value
    if isinstance(value, str):
        try:
            return EventPriority(int(value))
        except (ValueError, TypeError):
            return value
    return value


def _coerce_event_status(value: Any) -> Any:
    """若 value 为字符串，则转换为 EventStatus 枚举。"""
    if isinstance(value, str):
        try:
            return EventStatus(value)
        except ValueError:
            return value
    return value


def _schedule_to_dict(schedule: Schedule) -> Dict[str, Any]:
    """将 Schedule 对象序列化为字典。"""
    return schedule.to_dict()


def _event_to_dict(event: Event) -> Dict[str, Any]:
    """将 Event 对象序列化为字典。"""
    return event.to_dict()


class PrefrontalModule(BaseModule):
    """
    前额叶模块。

    负责日程管理、主动决策、事件管理等规划相关能力。
    """

    module_id = "prefrontal.planner"
    module_type = "prefrontal"

    def __init__(
        self,
        router: "CentralRouter",
        db_manager: Optional[DatabaseManager] = None,
    ) -> None:
        super().__init__(router)
        self._db = db_manager or DatabaseManager()
        self._schedule_manager = ScheduleManager(self._db)
        self._event_manager = EventManager(self._db)
        self._proactive_engine = ProactiveEngine(
            db_manager=self._db,
            event_manager=self._event_manager,
        )

    async def handle(self, packet: Packet) -> Packet:
        """
        处理规划相关请求。

        Channels:
            - schedule_list: 列出日程
            - schedule_add: 创建日程
            - schedule_delete: 删除日程
            - proactive_should_send: 主动消息发送决策
            - proactive_schedule_next: 排定下次主动消息
            - event_list: 列出事件
            - event_add: 创建事件
        """
        channel = packet.channel
        payload = packet.payload

        try:
            if channel == "schedule_list":
                return self._handle_schedule_list(packet, payload)
            if channel == "schedule_add":
                return self._handle_schedule_add(packet, payload)
            if channel == "schedule_delete":
                return self._handle_schedule_delete(packet, payload)
            if channel == "proactive_should_send":
                return self._handle_proactive_should_send(packet, payload)
            if channel == "proactive_schedule_next":
                return self._handle_proactive_schedule_next(packet, payload)
            if channel == "event_list":
                return self._handle_event_list(packet, payload)
            if channel == "event_add":
                return self._handle_event_add(packet, payload)
        except Exception as exc:  # noqa: BLE001
            return Packet.error(packet, str(exc), code="INTERNAL_ERROR")

        return packet.response({
            "status": "unknown_channel",
            "channel": channel,
        })

    def _handle_schedule_list(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        kwargs = {
            "start_time": payload.get("start_time"),
            "end_time": payload.get("end_time"),
            "queryable_only": payload.get("queryable_only", True),
            "active_only": payload.get("active_only", True),
            "include_inactive": payload.get("include_inactive", False),
            "limit": payload.get("limit", 1000),
        }
        schedules = self._schedule_manager.list_schedules(**kwargs)
        return packet.response({
            "schedules": [_schedule_to_dict(s) for s in schedules],
            "total": len(schedules),
        })

    def _handle_schedule_add(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        kwargs = dict(payload)
        if "schedule_type" in kwargs:
            kwargs["schedule_type"] = _coerce_schedule_type(kwargs["schedule_type"])
        if "priority" in kwargs:
            kwargs["priority"] = _coerce_schedule_priority(kwargs["priority"])

        success, schedule, message = self._schedule_manager.add_schedule(**kwargs)
        return packet.response({
            "success": success,
            "schedule": _schedule_to_dict(schedule) if schedule else None,
            "message": message,
        })

    def _handle_schedule_delete(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        schedule_id = payload.get("schedule_id")
        if not schedule_id:
            return Packet.error(packet, "schedule_id required", code="INVALID_REQUEST")
        deleted = self._schedule_manager.delete_schedule(schedule_id)
        return packet.response({"deleted": deleted})

    def _handle_proactive_should_send(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        user = payload.get("user")
        if not user:
            return Packet.error(packet, "user required", code="INVALID_REQUEST")
        now = _parse_datetime(payload.get("now"))
        should_send, reason = self._proactive_engine.should_send(user, now=now)
        return packet.response({"should_send": should_send, "reason": reason})

    def _handle_proactive_schedule_next(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        user = payload.get("user")
        if not user:
            return Packet.error(packet, "user required", code="INVALID_REQUEST")
        now = _parse_datetime(payload.get("now"))
        delay_hours = payload.get("delay_hours")
        if delay_hours is not None:
            try:
                delay_hours = float(delay_hours)
            except (ValueError, TypeError):
                return Packet.error(packet, "delay_hours must be a number", code="INVALID_REQUEST")
        self._proactive_engine.schedule_next_proactive(
            user, now=now, delay_hours=delay_hours
        )
        return packet.response({"status": "scheduled"})

    def _handle_event_list(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        status = _coerce_event_status(payload.get("status"))
        event_type = _coerce_event_type(payload.get("event_type"))
        limit = payload.get("limit", 100)
        events = self._event_manager.get_events(
            status=status, event_type=event_type, limit=limit
        )
        return packet.response({
            "events": [_event_to_dict(e) for e in events],
            "total": len(events),
        })

    def _handle_event_add(self, packet: Packet, payload: Dict[str, Any]) -> Packet:
        kwargs = dict(payload)
        if "event_type" in kwargs:
            kwargs["event_type"] = _coerce_event_type(kwargs["event_type"])
        if "priority" in kwargs:
            kwargs["priority"] = _coerce_event_priority(kwargs["priority"])

        event = self._event_manager.add_event(**kwargs)
        return packet.response({
            "event": _event_to_dict(event),
            "event_id": event.event_id,
        })


__all__ = ["PrefrontalModule"]
