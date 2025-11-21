"""
日程管理模块
提供日程安排、查询和提醒功能
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class SchedulePriority(Enum):
    """日程优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ScheduleStatus(Enum):
    """日程状态"""
    PENDING = "pending"  # 待办
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    OVERDUE = "overdue"  # 已过期


class Schedule:
    """日程条目"""

    def __init__(
        self,
        schedule_id: str = None,
        title: str = "",
        description: str = "",
        start_time: datetime = None,
        end_time: datetime = None,
        priority: SchedulePriority = SchedulePriority.MEDIUM,
        status: ScheduleStatus = ScheduleStatus.PENDING,
        remind_before: int = 15,  # 提前提醒时间（分钟）
        tags: List[str] = None,
        created_at: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化日程

        Args:
            schedule_id: 日程ID
            title: 标题
            description: 描述
            start_time: 开始时间
            end_time: 结束时间
            priority: 优先级
            status: 状态
            remind_before: 提前提醒时间（分钟）
            tags: 标签列表
            created_at: 创建时间
            metadata: 附加元数据
        """
        self.schedule_id = schedule_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.start_time = start_time or datetime.now()
        self.end_time = end_time or (self.start_time + timedelta(hours=1))
        self.priority = priority
        self.status = status
        self.remind_before = remind_before
        self.tags = tags or []
        self.created_at = created_at or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'schedule_id': self.schedule_id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'priority': self.priority.value,
            'status': self.status.value,
            'remind_before': self.remind_before,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Schedule':
        """从字典创建日程"""
        return cls(
            schedule_id=data.get('schedule_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            start_time=datetime.fromisoformat(data.get('start_time')),
            end_time=datetime.fromisoformat(data.get('end_time')),
            priority=SchedulePriority(data.get('priority', SchedulePriority.MEDIUM.value)),
            status=ScheduleStatus(data.get('status', ScheduleStatus.PENDING.value)),
            remind_before=data.get('remind_before', 15),
            tags=data.get('tags', []),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )

    def is_due_soon(self, minutes: int = None) -> bool:
        """
        检查是否即将开始

        Args:
            minutes: 判断时间范围（分钟），默认使用remind_before

        Returns:
            是否即将开始
        """
        if minutes is None:
            minutes = self.remind_before

        now = datetime.now()
        time_until_start = (self.start_time - now).total_seconds() / 60
        return 0 < time_until_start <= minutes

    def is_overdue(self) -> bool:
        """检查是否已过期"""
        return datetime.now() > self.end_time and self.status == ScheduleStatus.PENDING


class ScheduleManager:
    """
    日程管理器
    负责日程的创建、查询、更新和删除
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化日程管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager or DatabaseManager()
        self._init_database()

        debug_logger.log_info('ScheduleManager', '初始化日程管理器')

    def _init_database(self):
        """初始化数据库表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            priority INTEGER,
            status TEXT,
            remind_before INTEGER,
            tags TEXT,
            created_at TEXT,
            metadata TEXT
        )
        """
        self.db_manager.execute_query(create_table_sql)
        debug_logger.log_info('ScheduleManager', '数据库表初始化完成')

    def add_schedule(self, schedule: Schedule) -> bool:
        """
        添加日程

        Args:
            schedule: 日程对象

        Returns:
            是否添加成功
        """
        try:
            insert_sql = """
            INSERT INTO schedules 
            (schedule_id, title, description, start_time, end_time, priority, status, 
             remind_before, tags, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_query(
                insert_sql,
                (
                    schedule.schedule_id,
                    schedule.title,
                    schedule.description,
                    schedule.start_time.isoformat(),
                    schedule.end_time.isoformat(),
                    schedule.priority.value,
                    schedule.status.value,
                    schedule.remind_before,
                    json.dumps(schedule.tags, ensure_ascii=False),
                    schedule.created_at.isoformat(),
                    json.dumps(schedule.metadata, ensure_ascii=False)
                )
            )

            debug_logger.log_info('ScheduleManager', '添加日程成功', {
                'schedule_id': schedule.schedule_id,
                'title': schedule.title
            })
            return True

        except Exception as e:
            debug_logger.log_error('ScheduleManager', '添加日程失败', e)
            return False

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        获取指定日程

        Args:
            schedule_id: 日程ID

        Returns:
            日程对象或None
        """
        try:
            query_sql = "SELECT * FROM schedules WHERE schedule_id = ?"
            result = self.db_manager.fetch_one(query_sql, (schedule_id,))

            if result:
                return self._row_to_schedule(result)
            return None

        except Exception as e:
            debug_logger.log_error('ScheduleManager', '获取日程失败', e)
            return None

    def get_all_schedules(self, status: ScheduleStatus = None) -> List[Schedule]:
        """
        获取所有日程

        Args:
            status: 可选的状态筛选

        Returns:
            日程列表
        """
        try:
            if status:
                query_sql = "SELECT * FROM schedules WHERE status = ? ORDER BY start_time"
                results = self.db_manager.fetch_all(query_sql, (status.value,))
            else:
                query_sql = "SELECT * FROM schedules ORDER BY start_time"
                results = self.db_manager.fetch_all(query_sql)

            return [self._row_to_schedule(row) for row in results]

        except Exception as e:
            debug_logger.log_error('ScheduleManager', '获取日程列表失败', e)
            return []

    def get_schedules_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Schedule]:
        """
        获取指定时间范围内的日程

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            日程列表
        """
        try:
            query_sql = """
            SELECT * FROM schedules 
            WHERE start_time >= ? AND start_time <= ?
            ORDER BY start_time
            """
            results = self.db_manager.fetch_all(
                query_sql,
                (start_date.isoformat(), end_date.isoformat())
            )

            return [self._row_to_schedule(row) for row in results]

        except Exception as e:
            debug_logger.log_error('ScheduleManager', '获取时间范围日程失败', e)
            return []

    def get_today_schedules(self) -> List[Schedule]:
        """获取今天的日程"""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        return self.get_schedules_by_date_range(start_of_day, end_of_day)

    def get_upcoming_schedules(self, hours: int = 24) -> List[Schedule]:
        """
        获取即将到来的日程

        Args:
            hours: 未来多少小时内的日程

        Returns:
            日程列表
        """
        now = datetime.now()
        future = now + timedelta(hours=hours)

        return self.get_schedules_by_date_range(now, future)

    def update_schedule(self, schedule: Schedule) -> bool:
        """
        更新日程

        Args:
            schedule: 日程对象

        Returns:
            是否更新成功
        """
        try:
            update_sql = """
            UPDATE schedules 
            SET title = ?, description = ?, start_time = ?, end_time = ?,
                priority = ?, status = ?, remind_before = ?, tags = ?, metadata = ?
            WHERE schedule_id = ?
            """
            self.db_manager.execute_query(
                update_sql,
                (
                    schedule.title,
                    schedule.description,
                    schedule.start_time.isoformat(),
                    schedule.end_time.isoformat(),
                    schedule.priority.value,
                    schedule.status.value,
                    schedule.remind_before,
                    json.dumps(schedule.tags, ensure_ascii=False),
                    json.dumps(schedule.metadata, ensure_ascii=False),
                    schedule.schedule_id
                )
            )

            debug_logger.log_info('ScheduleManager', '更新日程成功', {
                'schedule_id': schedule.schedule_id
            })
            return True

        except Exception as e:
            debug_logger.log_error('ScheduleManager', '更新日程失败', e)
            return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        删除日程

        Args:
            schedule_id: 日程ID

        Returns:
            是否删除成功
        """
        try:
            delete_sql = "DELETE FROM schedules WHERE schedule_id = ?"
            self.db_manager.execute_query(delete_sql, (schedule_id,))

            debug_logger.log_info('ScheduleManager', '删除日程成功', {
                'schedule_id': schedule_id
            })
            return True

        except Exception as e:
            debug_logger.log_error('ScheduleManager', '删除日程失败', e)
            return False

    def check_due_schedules(self) -> List[Schedule]:
        """
        检查即将到期的日程

        Returns:
            即将到期的日程列表
        """
        all_schedules = self.get_all_schedules(ScheduleStatus.PENDING)
        due_schedules = [s for s in all_schedules if s.is_due_soon()]

        if due_schedules:
            debug_logger.log_info('ScheduleManager', '发现即将到期的日程', {
                'count': len(due_schedules)
            })

        return due_schedules

    def update_overdue_schedules(self) -> int:
        """
        更新过期日程的状态

        Returns:
            更新的数量
        """
        all_schedules = self.get_all_schedules(ScheduleStatus.PENDING)
        count = 0

        for schedule in all_schedules:
            if schedule.is_overdue():
                schedule.status = ScheduleStatus.OVERDUE
                if self.update_schedule(schedule):
                    count += 1

        if count > 0:
            debug_logger.log_info('ScheduleManager', '更新过期日程', {
                'count': count
            })

        return count

    def _row_to_schedule(self, row: tuple) -> Schedule:
        """
        将数据库行转换为Schedule对象

        Args:
            row: 数据库查询结果行

        Returns:
            Schedule对象
        """
        return Schedule(
            schedule_id=row[0],
            title=row[1],
            description=row[2],
            start_time=datetime.fromisoformat(row[3]),
            end_time=datetime.fromisoformat(row[4]),
            priority=SchedulePriority(row[5]),
            status=ScheduleStatus(row[6]),
            remind_before=row[7],
            tags=json.loads(row[8]) if row[8] else [],
            created_at=datetime.fromisoformat(row[9]),
            metadata=json.loads(row[10]) if row[10] else {}
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取日程统计信息

        Returns:
            统计信息字典
        """
        all_schedules = self.get_all_schedules()

        stats = {
            'total': len(all_schedules),
            'pending': len([s for s in all_schedules if s.status == ScheduleStatus.PENDING]),
            'in_progress': len([s for s in all_schedules if s.status == ScheduleStatus.IN_PROGRESS]),
            'completed': len([s for s in all_schedules if s.status == ScheduleStatus.COMPLETED]),
            'overdue': len([s for s in all_schedules if s.status == ScheduleStatus.OVERDUE]),
            'today': len(self.get_today_schedules()),
            'upcoming_24h': len(self.get_upcoming_schedules(24))
        }

        return stats
