"""
智能体日程管理模块
支持周期日程、预约日程和临时日程三种类型
自动处理优先级和冲突检测
"""

import uuid
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class SchedulePriority(Enum):
    """日程优先级枚举"""
    LOW = 1          # 低优先级 - 临时起意的日程
    MEDIUM = 2       # 中等优先级 - 一般预约
    HIGH = 3         # 高优先级 - 重要预约
    URGENT = 4       # 紧急优先级 - 周期性固定日程


class ScheduleType(Enum):
    """日程类型枚举"""
    RECURRING = "recurring"    # 周期日程（如周一到周五的课程表）
    APPOINTMENT = "appointment"  # 预约日程（如周三下午开会）
    IMPROMPTU = "impromptu"    # 临时起意日程（如今晚看月亮）


class RecurrencePattern(Enum):
    """重复模式枚举"""
    NONE = "none"              # 不重复
    DAILY = "daily"            # 每天
    WEEKLY = "weekly"          # 每周
    WEEKDAYS = "weekdays"      # 工作日（周一到周五）
    WEEKENDS = "weekends"      # 周末
    MONTHLY = "monthly"        # 每月
    CUSTOM = "custom"          # 自定义（使用weekday_list）


class Schedule:
    """
    日程基类
    """

    def __init__(
        self,
        schedule_id: str = None,
        title: str = "",
        description: str = "",
        schedule_type: ScheduleType = ScheduleType.APPOINTMENT,
        priority: SchedulePriority = SchedulePriority.MEDIUM,
        start_time: str = None,  # ISO格式时间戳或时间字符串
        end_time: str = None,
        date: str = None,  # 日期 YYYY-MM-DD
        recurrence_pattern: RecurrencePattern = RecurrencePattern.NONE,
        weekday_list: List[int] = None,  # 0=周一, 6=周日
        recurrence_end_date: str = None,  # 重复结束日期
        location: str = "",
        created_at: str = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化日程

        Args:
            schedule_id: 日程唯一标识符
            title: 日程标题
            description: 日程描述
            schedule_type: 日程类型
            priority: 优先级
            start_time: 开始时间（HH:MM格式或ISO时间戳）
            end_time: 结束时间（HH:MM格式或ISO时间戳）
            date: 日期（YYYY-MM-DD）
            recurrence_pattern: 重复模式
            weekday_list: 自定义重复的星期列表（0-6）
            recurrence_end_date: 重复结束日期
            location: 地点
            created_at: 创建时间
            metadata: 附加元数据
        """
        self.schedule_id = schedule_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.schedule_type = schedule_type
        self.priority = priority
        self.start_time = start_time
        self.end_time = end_time
        self.date = date
        self.recurrence_pattern = recurrence_pattern
        self.weekday_list = weekday_list or []
        self.recurrence_end_date = recurrence_end_date
        self.location = location
        self.created_at = created_at or datetime.now().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        将日程转换为字典

        Returns:
            日程字典表示
        """
        return {
            'schedule_id': self.schedule_id,
            'title': self.title,
            'description': self.description,
            'schedule_type': self.schedule_type.value,
            'priority': self.priority.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'date': self.date,
            'recurrence_pattern': self.recurrence_pattern.value,
            'weekday_list': self.weekday_list,
            'recurrence_end_date': self.recurrence_end_date,
            'location': self.location,
            'created_at': self.created_at,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Schedule':
        """
        从字典创建日程

        Args:
            data: 日程字典数据

        Returns:
            日程对象
        """
        return cls(
            schedule_id=data.get('schedule_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            schedule_type=ScheduleType(data.get('schedule_type', 'appointment')),
            priority=SchedulePriority(data.get('priority', 2)),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            date=data.get('date'),
            recurrence_pattern=RecurrencePattern(data.get('recurrence_pattern', 'none')),
            weekday_list=data.get('weekday_list', []),
            recurrence_end_date=data.get('recurrence_end_date'),
            location=data.get('location', ''),
            created_at=data.get('created_at'),
            metadata=data.get('metadata', {})
        )

    def is_recurring(self) -> bool:
        """检查是否为重复日程"""
        return self.recurrence_pattern != RecurrencePattern.NONE

    def get_weekday(self, date_str: str) -> int:
        """
        获取指定日期是星期几

        Args:
            date_str: 日期字符串 YYYY-MM-DD

        Returns:
            星期几（0=周一, 6=周日）
        """
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.weekday()

    def applies_to_date(self, target_date: str) -> bool:
        """
        检查日程是否适用于指定日期

        Args:
            target_date: 目标日期 YYYY-MM-DD

        Returns:
            是否适用
        """
        # 如果不是重复日程，检查日期是否匹配
        if not self.is_recurring():
            return self.date == target_date

        # 检查目标日期是否在重复范围内
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
        
        # 检查是否在开始日期之后
        if self.date:
            start_dt = datetime.strptime(self.date, '%Y-%m-%d')
            if target_dt < start_dt:
                return False

        # 检查是否在结束日期之前
        if self.recurrence_end_date:
            end_dt = datetime.strptime(self.recurrence_end_date, '%Y-%m-%d')
            if target_dt > end_dt:
                return False

        # 检查重复模式
        weekday = target_dt.weekday()

        if self.recurrence_pattern == RecurrencePattern.DAILY:
            return True
        elif self.recurrence_pattern == RecurrencePattern.WEEKLY:
            # 检查是否与开始日期同一星期几
            if self.date:
                start_weekday = self.get_weekday(self.date)
                return weekday == start_weekday
            return False
        elif self.recurrence_pattern == RecurrencePattern.WEEKDAYS:
            return weekday < 5  # 周一到周五
        elif self.recurrence_pattern == RecurrencePattern.WEEKENDS:
            return weekday >= 5  # 周六和周日
        elif self.recurrence_pattern == RecurrencePattern.MONTHLY:
            # 检查是否与开始日期同一天
            if self.date:
                start_dt = datetime.strptime(self.date, '%Y-%m-%d')
                return target_dt.day == start_dt.day
            return False
        elif self.recurrence_pattern == RecurrencePattern.CUSTOM:
            return weekday in self.weekday_list

        return False


class ScheduleManager:
    """
    日程管理器
    负责日程的创建、存储、检索、冲突检测和优先级处理
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化日程管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager or DatabaseManager()
        self._initialize_database()
        
        debug_logger.log_module('ScheduleManager', '日程管理器初始化完成')

    def _initialize_database(self):
        """初始化数据库表"""
        with self.db.get_connection() as conn:
            # 创建日程表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schedules (
                    schedule_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    schedule_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    date TEXT NOT NULL,
                    recurrence_pattern TEXT DEFAULT 'none',
                    weekday_list TEXT,
                    recurrence_end_date TEXT,
                    location TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    metadata TEXT
                )
            ''')
            
            # 创建索引以提高查询性能
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_type ON schedules(schedule_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_priority ON schedules(priority)')
        
        debug_logger.log_info('ScheduleManager', '数据库表初始化完成')

    def _parse_time(self, time_str: str) -> time:
        """
        解析时间字符串

        Args:
            time_str: 时间字符串（HH:MM格式）

        Returns:
            time对象
        """
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            # 尝试ISO格式
            try:
                return datetime.fromisoformat(time_str).time()
            except:
                raise ValueError(f"无效的时间格式: {time_str}")

    def _check_time_overlap(
        self,
        start1: str,
        end1: str,
        start2: str,
        end2: str
    ) -> bool:
        """
        检查两个时间段是否重叠

        Args:
            start1: 时间段1开始时间
            end1: 时间段1结束时间
            start2: 时间段2开始时间
            end2: 时间段2结束时间

        Returns:
            是否重叠
        """
        t1_start = self._parse_time(start1)
        t1_end = self._parse_time(end1)
        t2_start = self._parse_time(start2)
        t2_end = self._parse_time(end2)

        # 检查重叠：A的结束时间 > B的开始时间 且 A的开始时间 < B的结束时间
        return t1_end > t2_start and t1_start < t2_end

    def check_conflict(
        self,
        schedule: Schedule,
        target_date: str = None,
        exclude_schedule_id: str = None
    ) -> Tuple[bool, List[Schedule]]:
        """
        检查日程冲突

        Args:
            schedule: 要检查的日程
            target_date: 目标日期（用于重复日程），如果为None则使用schedule.date
            exclude_schedule_id: 排除的日程ID（用于更新时排除自身）

        Returns:
            (是否有冲突, 冲突的日程列表)
        """
        check_date = target_date or schedule.date
        if not check_date:
            return False, []

        # 获取当天的所有日程
        existing_schedules = self.get_schedules_by_date(check_date)

        conflicts = []
        for existing in existing_schedules:
            # 排除自身
            if exclude_schedule_id and existing.schedule_id == exclude_schedule_id:
                continue

            # 检查时间是否重叠
            if self._check_time_overlap(
                schedule.start_time, schedule.end_time,
                existing.start_time, existing.end_time
            ):
                conflicts.append(existing)

        has_conflict = len(conflicts) > 0
        return has_conflict, conflicts

    def resolve_conflict_by_priority(
        self,
        new_schedule: Schedule,
        conflicts: List[Schedule]
    ) -> Tuple[bool, List[str]]:
        """
        通过优先级解决冲突

        Args:
            new_schedule: 新日程
            conflicts: 冲突的日程列表

        Returns:
            (是否成功解决, 被删除的日程ID列表)
        """
        removed_ids = []

        for conflict in conflicts:
            # 新日程优先级更高，删除低优先级的旧日程
            if new_schedule.priority.value > conflict.priority.value:
                if self.delete_schedule(conflict.schedule_id):
                    removed_ids.append(conflict.schedule_id)
                    debug_logger.log_info(
                        'ScheduleManager',
                        f'删除低优先级日程: {conflict.title}',
                        {'schedule_id': conflict.schedule_id}
                    )
            else:
                # 新日程优先级不高于现有日程，无法解决冲突
                debug_logger.log_warning(
                    'ScheduleManager',
                    f'无法添加日程，优先级不足: {new_schedule.title}'
                )
                return False, []

        return True, removed_ids

    def add_schedule(
        self,
        title: str,
        description: str = "",
        schedule_type: ScheduleType = ScheduleType.APPOINTMENT,
        priority: SchedulePriority = None,
        start_time: str = None,
        end_time: str = None,
        date: str = None,
        recurrence_pattern: RecurrencePattern = RecurrencePattern.NONE,
        weekday_list: List[int] = None,
        recurrence_end_date: str = None,
        location: str = "",
        auto_resolve_conflicts: bool = True
    ) -> Tuple[bool, Optional[Schedule], str]:
        """
        添加日程

        Args:
            title: 日程标题
            description: 日程描述
            schedule_type: 日程类型
            priority: 优先级（如果为None，根据类型自动设置）
            start_time: 开始时间（HH:MM）
            end_time: 结束时间（HH:MM）
            date: 日期（YYYY-MM-DD）
            recurrence_pattern: 重复模式
            weekday_list: 自定义重复的星期列表
            recurrence_end_date: 重复结束日期
            location: 地点
            auto_resolve_conflicts: 是否自动解决冲突

        Returns:
            (是否成功, 日程对象, 消息)
        """
        debug_logger.log_module('ScheduleManager', '添加新日程', {
            'title': title,
            'type': schedule_type.value
        })

        # 自动设置优先级
        if priority is None:
            if schedule_type == ScheduleType.RECURRING:
                priority = SchedulePriority.URGENT
            elif schedule_type == ScheduleType.APPOINTMENT:
                priority = SchedulePriority.MEDIUM
            else:  # IMPROMPTU
                priority = SchedulePriority.LOW

        # 创建日程对象
        schedule = Schedule(
            title=title,
            description=description,
            schedule_type=schedule_type,
            priority=priority,
            start_time=start_time,
            end_time=end_time,
            date=date,
            recurrence_pattern=recurrence_pattern,
            weekday_list=weekday_list,
            recurrence_end_date=recurrence_end_date,
            location=location
        )

        # 检查冲突
        has_conflict, conflicts = self.check_conflict(schedule)

        if has_conflict:
            if auto_resolve_conflicts:
                # 尝试通过优先级解决冲突
                resolved, removed_ids = self.resolve_conflict_by_priority(schedule, conflicts)
                if not resolved:
                    return False, None, f"无法添加日程：与 {len(conflicts)} 个更高优先级的日程冲突"
                
                message = f"已添加日程，删除了 {len(removed_ids)} 个低优先级日程"
            else:
                return False, None, f"日程冲突：与 {len(conflicts)} 个现有日程时间重叠"

        # 保存到数据库
        import json
        try:
            with self.db.get_connection() as conn:
                conn.execute('''
                    INSERT INTO schedules (
                        schedule_id, title, description, schedule_type,
                        priority, start_time, end_time, date,
                        recurrence_pattern, weekday_list, recurrence_end_date,
                        location, created_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    schedule.schedule_id,
                    schedule.title,
                    schedule.description,
                    schedule.schedule_type.value,
                    schedule.priority.value,
                    schedule.start_time,
                    schedule.end_time,
                    schedule.date,
                    schedule.recurrence_pattern.value,
                    json.dumps(schedule.weekday_list),
                    schedule.recurrence_end_date,
                    schedule.location,
                    schedule.created_at,
                    json.dumps(schedule.metadata, ensure_ascii=False)
                ))

            debug_logger.log_info('ScheduleManager', '日程添加成功', {
                'schedule_id': schedule.schedule_id
            })

            message = message if has_conflict else "日程添加成功"
            return True, schedule, message
            
        except Exception as e:
            debug_logger.log_error('ScheduleManager', f'添加日程失败: {str(e)}', e)
            return False, None, f"添加日程失败: {str(e)}"

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        获取指定日程

        Args:
            schedule_id: 日程ID

        Returns:
            日程对象，不存在时返回None
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM schedules WHERE schedule_id = ?',
                (schedule_id,)
            )
            row = cursor.fetchone()

            if row:
                import json
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'date': row[7],
                    'recurrence_pattern': row[8],
                    'weekday_list': json.loads(row[9]) if row[9] else [],
                    'recurrence_end_date': row[10],
                    'location': row[11],
                    'created_at': row[12],
                    'metadata': json.loads(row[14]) if row[14] else {}
                }
                return Schedule.from_dict(data)

        return None

    def get_schedules_by_date(self, target_date: str) -> List[Schedule]:
        """
        获取指定日期的所有日程（包括重复日程）

        Args:
            target_date: 目标日期 YYYY-MM-DD

        Returns:
            日程列表
        """
        schedules = []
        
        with self.db.get_connection() as conn:
            # 获取所有日程
            cursor = conn.execute('SELECT * FROM schedules')
            
            import json
            for row in cursor.fetchall():
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'date': row[7],
                    'recurrence_pattern': row[8],
                    'weekday_list': json.loads(row[9]) if row[9] else [],
                    'recurrence_end_date': row[10],
                    'location': row[11],
                    'created_at': row[12],
                    'metadata': json.loads(row[14]) if row[14] else {}
                }
                schedule = Schedule.from_dict(data)
                
                # 检查日程是否适用于目标日期
                if schedule.applies_to_date(target_date):
                    schedules.append(schedule)

        # 按开始时间和优先级排序
        schedules.sort(key=lambda s: (s.start_time, -s.priority.value))
        return schedules

    def get_schedules_by_type(
        self,
        schedule_type: ScheduleType,
        limit: int = 100
    ) -> List[Schedule]:
        """
        按类型获取日程

        Args:
            schedule_type: 日程类型
            limit: 返回数量限制

        Returns:
            日程列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM schedules 
                WHERE schedule_type = ?
                ORDER BY date ASC, start_time ASC
                LIMIT ?
            ''', (schedule_type.value, limit))

            schedules = []
            import json
            for row in cursor.fetchall():
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'date': row[7],
                    'recurrence_pattern': row[8],
                    'weekday_list': json.loads(row[9]) if row[9] else [],
                    'recurrence_end_date': row[10],
                    'location': row[11],
                    'created_at': row[12],
                    'metadata': json.loads(row[14]) if row[14] else {}
                }
                schedules.append(Schedule.from_dict(data))

        return schedules

    def get_all_schedules(self, limit: int = 100) -> List[Schedule]:
        """
        获取所有日程

        Args:
            limit: 返回数量限制

        Returns:
            日程列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM schedules 
                ORDER BY date ASC, start_time ASC
                LIMIT ?
            ''', (limit,))

            schedules = []
            import json
            for row in cursor.fetchall():
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'date': row[7],
                    'recurrence_pattern': row[8],
                    'weekday_list': json.loads(row[9]) if row[9] else [],
                    'recurrence_end_date': row[10],
                    'location': row[11],
                    'created_at': row[12],
                    'metadata': json.loads(row[14]) if row[14] else {}
                }
                schedules.append(Schedule.from_dict(data))

        return schedules

    def update_schedule(
        self,
        schedule_id: str,
        **kwargs
    ) -> Tuple[bool, str]:
        """
        更新日程

        Args:
            schedule_id: 日程ID
            **kwargs: 要更新的字段

        Returns:
            (是否成功, 消息)
        """
        try:
            # 获取现有日程
            existing = self.get_schedule(schedule_id)
            if not existing:
                return False, "日程不存在"

            # 白名单验证允许更新的列名
            allowed_columns = {
                'title', 'description', 'schedule_type', 'priority',
                'start_time', 'end_time', 'date', 'recurrence_pattern',
                'weekday_list', 'recurrence_end_date', 'location', 'metadata'
            }

            # 过滤只允许白名单中的列名
            safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed_columns}
            if not safe_kwargs:
                return False, "没有有效的字段可更新"

            # 如果更新了时间相关字段，需要检查冲突
            time_fields = {'start_time', 'end_time', 'date'}
            if any(field in safe_kwargs for field in time_fields):
                # 创建临时日程对象用于冲突检测
                temp_schedule = Schedule.from_dict(existing.to_dict())
                for key, value in safe_kwargs.items():
                    setattr(temp_schedule, key, value)

                has_conflict, conflicts = self.check_conflict(
                    temp_schedule,
                    exclude_schedule_id=schedule_id
                )
                
                if has_conflict:
                    return False, f"更新失败：与 {len(conflicts)} 个日程冲突"

            # 处理枚举类型
            import json
            processed_kwargs = {}
            for key, value in safe_kwargs.items():
                if key == 'schedule_type' and isinstance(value, ScheduleType):
                    processed_kwargs[key] = value.value
                elif key == 'priority' and isinstance(value, SchedulePriority):
                    processed_kwargs[key] = value.value
                elif key == 'recurrence_pattern' and isinstance(value, RecurrencePattern):
                    processed_kwargs[key] = value.value
                elif key == 'weekday_list':
                    processed_kwargs[key] = json.dumps(value)
                elif key == 'metadata':
                    processed_kwargs[key] = json.dumps(value, ensure_ascii=False)
                else:
                    processed_kwargs[key] = value

            # 构建更新SQL
            set_clause = ", ".join([f"{k} = ?" for k in processed_kwargs.keys()])
            set_clause += ", updated_at = ?"
            values = list(processed_kwargs.values()) + [datetime.now().isoformat(), schedule_id]

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE schedules 
                    SET {set_clause}
                    WHERE schedule_id = ?
                ''', values)
                
                if cursor.rowcount == 0:
                    return False, "日程不存在"

            debug_logger.log_info('ScheduleManager', '日程更新成功', {
                'schedule_id': schedule_id
            })

            return True, "日程更新成功"

        except Exception as e:
            debug_logger.log_error('ScheduleManager', f'更新日程失败: {str(e)}', e)
            return False, f"更新日程失败: {str(e)}"

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        删除日程

        Args:
            schedule_id: 日程ID

        Returns:
            是否成功
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM schedules WHERE schedule_id = ?',
                    (schedule_id,)
                )
                
                if cursor.rowcount == 0:
                    return False

            debug_logger.log_info('ScheduleManager', '日程删除成功', {
                'schedule_id': schedule_id
            })

            return True

        except Exception as e:
            debug_logger.log_error('ScheduleManager', f'删除日程失败: {str(e)}', e)
            return False

    def get_schedule_summary(self, target_date: str) -> str:
        """
        获取指定日期的日程摘要（用于对话上下文）

        Args:
            target_date: 目标日期 YYYY-MM-DD

        Returns:
            日程摘要文本
        """
        schedules = self.get_schedules_by_date(target_date)
        
        if not schedules:
            return f"{target_date} 没有安排任何日程。"

        # 按时间段分组
        morning = []  # 6:00-12:00
        afternoon = []  # 12:00-18:00
        evening = []  # 18:00-24:00
        night = []  # 0:00-6:00

        for schedule in schedules:
            start_hour = int(schedule.start_time.split(':')[0])
            
            schedule_str = f"{schedule.start_time}-{schedule.end_time} {schedule.title}"
            if schedule.location:
                schedule_str += f"（{schedule.location}）"

            if 6 <= start_hour < 12:
                morning.append(schedule_str)
            elif 12 <= start_hour < 18:
                afternoon.append(schedule_str)
            elif 18 <= start_hour < 24:
                evening.append(schedule_str)
            else:
                night.append(schedule_str)

        # 构建摘要
        summary_parts = [f"{target_date} 的日程安排："]
        
        if morning:
            summary_parts.append(f"上午：{', '.join(morning)}")
        if afternoon:
            summary_parts.append(f"下午：{', '.join(afternoon)}")
        if evening:
            summary_parts.append(f"晚上：{', '.join(evening)}")
        if night:
            summary_parts.append(f"凌晨：{', '.join(night)}")

        return "\n".join(summary_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取日程统计信息

        Returns:
            统计信息字典
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN schedule_type = ? THEN 1 ELSE 0 END) as recurring,
                    SUM(CASE WHEN schedule_type = ? THEN 1 ELSE 0 END) as appointments,
                    SUM(CASE WHEN schedule_type = ? THEN 1 ELSE 0 END) as impromptu,
                    SUM(CASE WHEN priority = ? THEN 1 ELSE 0 END) as urgent,
                    SUM(CASE WHEN priority = ? THEN 1 ELSE 0 END) as high,
                    SUM(CASE WHEN priority = ? THEN 1 ELSE 0 END) as medium,
                    SUM(CASE WHEN priority = ? THEN 1 ELSE 0 END) as low
                FROM schedules
            ''', (
                ScheduleType.RECURRING.value,
                ScheduleType.APPOINTMENT.value,
                ScheduleType.IMPROMPTU.value,
                SchedulePriority.URGENT.value,
                SchedulePriority.HIGH.value,
                SchedulePriority.MEDIUM.value,
                SchedulePriority.LOW.value
            ))

            row = cursor.fetchone()
            return {
                'total_schedules': row[0] or 0,
                'recurring': row[1] or 0,
                'appointments': row[2] or 0,
                'impromptu': row[3] or 0,
                'urgent': row[4] or 0,
                'high': row[5] or 0,
                'medium': row[6] or 0,
                'low': row[7] or 0
            }
