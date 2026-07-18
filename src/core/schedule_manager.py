"""
Schedule Manager - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.prefrontal.schedule.schedule_manager
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.prefrontal.schedule.schedule_manager
"""

from __future__ import annotations

from src.prefrontal.schedule.schedule_manager import (
    AppointmentSchedule,
    CollaborationStatus,
    RecurringSchedule,
    Schedule,
    ScheduleManager,
    SchedulePriority,
    ScheduleType,
    TemporarySchedule,
)

__all__ = [
    "Schedule",
    "RecurringSchedule",
    "AppointmentSchedule",
    "TemporarySchedule",
    "ScheduleType",
    "SchedulePriority",
    "CollaborationStatus",
    "ScheduleManager",
]
