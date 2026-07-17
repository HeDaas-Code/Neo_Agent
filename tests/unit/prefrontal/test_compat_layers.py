"""
v4.0 兼容层单元测试（前额叶）。

验证旧路径（src.core.*）仍然可以通过导入转发访问新实现。
"""

from src.core.event_manager import (
    Event as CoreEvent,
    EventManager as CoreEventManager,
    EventPriority as CoreEventPriority,
    EventStatus as CoreEventStatus,
    EventType as CoreEventType,
    NotificationEvent as CoreNotificationEvent,
    TaskEvent as CoreTaskEvent,
    get_event_manager as core_get_event_manager,
)
from src.core.proactive_engine import (
    ENABLE_PROACTIVE_ENGINE as CORE_ENABLE_PROACTIVE_ENGINE,
    ProactiveEngine as CoreProactiveEngine,
)
from src.core.schedule_generator import (
    TemporaryScheduleGenerator as CoreTemporaryScheduleGenerator,
)
from src.core.schedule_manager import (
    AppointmentSchedule as CoreAppointmentSchedule,
    CollaborationStatus as CoreCollaborationStatus,
    RecurringSchedule as CoreRecurringSchedule,
    Schedule as CoreSchedule,
    ScheduleManager as CoreScheduleManager,
    SchedulePriority as CoreSchedulePriority,
    ScheduleType as CoreScheduleType,
    TemporarySchedule as CoreTemporarySchedule,
)
from src.core.schedule_similarity_checker import (
    ScheduleSimilarityChecker as CoreScheduleSimilarityChecker,
    get_schedules_on_same_day as core_get_schedules_on_same_day,
)
from src.prefrontal.event.event_manager import (
    Event as PrefrontalEvent,
    EventManager as PrefrontalEventManager,
    EventPriority as PrefrontalEventPriority,
    EventStatus as PrefrontalEventStatus,
    EventType as PrefrontalEventType,
    NotificationEvent as PrefrontalNotificationEvent,
    TaskEvent as PrefrontalTaskEvent,
    get_event_manager as prefrontal_get_event_manager,
)
from src.prefrontal.proactive.proactive_engine import (
    ENABLE_PROACTIVE_ENGINE as PFC_ENABLE_PROACTIVE_ENGINE,
    ProactiveEngine as PrefrontalProactiveEngine,
)
from src.prefrontal.schedule.schedule_generator import (
    TemporaryScheduleGenerator as PrefrontalTemporaryScheduleGenerator,
)
from src.prefrontal.schedule.schedule_manager import (
    AppointmentSchedule as PrefrontalAppointmentSchedule,
    CollaborationStatus as PrefrontalCollaborationStatus,
    RecurringSchedule as PrefrontalRecurringSchedule,
    Schedule as PrefrontalSchedule,
    ScheduleManager as PrefrontalScheduleManager,
    SchedulePriority as PrefrontalSchedulePriority,
    ScheduleType as PrefrontalScheduleType,
    TemporarySchedule as PrefrontalTemporarySchedule,
)
from src.prefrontal.schedule.schedule_similarity_checker import (
    ScheduleSimilarityChecker as PrefrontalScheduleSimilarityChecker,
    get_schedules_on_same_day as prefrontal_get_schedules_on_same_day,
)


def test_schedule_manager_compat():
    """
    src.core.schedule_manager 应转发到 src.prefrontal.schedule.schedule_manager。
    """
    assert CoreSchedule is PrefrontalSchedule
    assert CoreRecurringSchedule is PrefrontalRecurringSchedule
    assert CoreAppointmentSchedule is PrefrontalAppointmentSchedule
    assert CoreTemporarySchedule is PrefrontalTemporarySchedule
    assert CoreScheduleType is PrefrontalScheduleType
    assert CoreSchedulePriority is PrefrontalSchedulePriority
    assert CoreCollaborationStatus is PrefrontalCollaborationStatus
    assert CoreScheduleManager is PrefrontalScheduleManager


def test_schedule_generator_compat():
    """
    src.core.schedule_generator 应转发到 src.prefrontal.schedule.schedule_generator。
    """
    assert CoreTemporaryScheduleGenerator is PrefrontalTemporaryScheduleGenerator


def test_schedule_similarity_checker_compat():
    """
    src.core.schedule_similarity_checker 应转发到
    src.prefrontal.schedule.schedule_similarity_checker。
    """
    assert CoreScheduleSimilarityChecker is PrefrontalScheduleSimilarityChecker
    assert core_get_schedules_on_same_day is prefrontal_get_schedules_on_same_day


def test_proactive_engine_compat():
    """
    src.core.proactive_engine 应转发到 src.prefrontal.proactive.proactive_engine。
    """
    assert CoreProactiveEngine is PrefrontalProactiveEngine
    assert CORE_ENABLE_PROACTIVE_ENGINE is PFC_ENABLE_PROACTIVE_ENGINE


def test_event_manager_compat():
    """
    src.core.event_manager 应转发到 src.prefrontal.event.event_manager。
    """
    assert CoreEvent is PrefrontalEvent
    assert CoreNotificationEvent is PrefrontalNotificationEvent
    assert CoreTaskEvent is PrefrontalTaskEvent
    assert CoreEventType is PrefrontalEventType
    assert CoreEventPriority is PrefrontalEventPriority
    assert CoreEventStatus is PrefrontalEventStatus
    assert CoreEventManager is PrefrontalEventManager
    assert core_get_event_manager is prefrontal_get_event_manager
