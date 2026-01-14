"""
智能体日程管理模块
实现日程的创建、管理、冲突检测和优先级控制
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class ScheduleType(Enum):
    """日程类型枚举"""
    RECURRING = "recurring"  # 周期日程（如课程表）
    APPOINTMENT = "appointment"  # 预约日程（用户提及或意图识别）
    TEMPORARY = "temporary"  # 临时日程（LLM自动生成）


class SchedulePriority(Enum):
    """日程优先级枚举"""
    LOW = 1  # 低优先级（临时日程）
    MEDIUM = 2  # 中等优先级（一般预约）
    HIGH = 3  # 高优先级（重要预约）
    CRITICAL = 4  # 关键优先级（周期日程如课程）


class CollaborationStatus(Enum):
    """协作确认状态枚举"""
    NOT_REQUIRED = "not_required"  # 不需要协作
    PENDING = "pending"  # 待确认
    CONFIRMED = "confirmed"  # 已确认
    REJECTED = "rejected"  # 已拒绝


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
        start_time: str = None,
        end_time: str = None,
        created_at: str = None,
        is_active: bool = True,
        collaboration_status: CollaborationStatus = CollaborationStatus.NOT_REQUIRED,
        is_queryable: bool = True,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化日程

        Args:
            schedule_id: 日程唯一标识符
            title: 日程标题
            description: 日程描述
            schedule_type: 日程类型
            priority: 日程优先级
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            created_at: 创建时间
            is_active: 是否激活
            collaboration_status: 协作确认状态
            is_queryable: 是否可被查询
            metadata: 附加元数据
        """
        self.schedule_id = schedule_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.schedule_type = schedule_type
        self.priority = priority
        self.start_time = start_time
        self.end_time = end_time
        self.created_at = created_at or datetime.now().isoformat()
        self.is_active = is_active
        self.collaboration_status = collaboration_status
        self.is_queryable = is_queryable
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
            'created_at': self.created_at,
            'is_active': self.is_active,
            'collaboration_status': self.collaboration_status.value,
            'is_queryable': self.is_queryable,
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
            created_at=data.get('created_at'),
            is_active=data.get('is_active', True),
            collaboration_status=CollaborationStatus(data.get('collaboration_status', 'not_required')),
            is_queryable=data.get('is_queryable', True),
            metadata=data.get('metadata', {})
        )


class RecurringSchedule(Schedule):
    """
    周期日程
    支持每周重复的固定日程，如课程表
    """

    def __init__(
        self,
        weekday: int = None,  # 0-6 表示周一到周日
        recurrence_pattern: str = "",  # 重复模式描述
        **kwargs
    ):
        """
        初始化周期日程

        Args:
            weekday: 星期几（0-6，0=周一）
            recurrence_pattern: 重复模式（如 "每周一、三、五"）
            **kwargs: 其他日程参数
        """
        # 设置默认优先级，如果kwargs中没有指定
        if 'priority' not in kwargs:
            kwargs['priority'] = SchedulePriority.CRITICAL
        super().__init__(
            schedule_type=ScheduleType.RECURRING,
            **kwargs
        )
        self.metadata['weekday'] = weekday
        self.metadata['recurrence_pattern'] = recurrence_pattern


class AppointmentSchedule(Schedule):
    """
    预约日程
    用户主动提及或通过意图识别创建的日程
    """

    def __init__(
        self,
        source: str = "user",  # 来源：user（用户提及）或intent（意图识别）
        confirmed_by_agent: bool = False,  # 智能体是否已确认
        **kwargs
    ):
        """
        初始化预约日程

        Args:
            source: 日程来源
            confirmed_by_agent: 智能体是否已确认
            **kwargs: 其他日程参数
        """
        super().__init__(
            schedule_type=ScheduleType.APPOINTMENT,
            **kwargs
        )
        self.metadata['source'] = source
        self.metadata['confirmed_by_agent'] = confirmed_by_agent


class TemporarySchedule(Schedule):
    """
    临时日程
    LLM在空闲时段自动生成的补充日程
    """

    def __init__(
        self,
        generated_reason: str = "",  # 生成原因
        involves_user: bool = False,  # 是否涉及用户参与
        **kwargs
    ):
        """
        初始化临时日程

        Args:
            generated_reason: 生成原因
            involves_user: 是否涉及用户参与
            **kwargs: 其他日程参数
        """
        # 如果涉及用户，需要协作确认且默认不可查询
        if involves_user:
            kwargs['collaboration_status'] = CollaborationStatus.PENDING
            kwargs['is_queryable'] = False
        
        # 设置默认优先级，如果kwargs中没有指定
        if 'priority' not in kwargs:
            kwargs['priority'] = SchedulePriority.LOW
        
        super().__init__(
            schedule_type=ScheduleType.TEMPORARY,
            **kwargs
        )
        self.metadata['generated_reason'] = generated_reason
        self.metadata['involves_user'] = involves_user


class ScheduleManager:
    """
    日程管理器
    负责日程的创建、查询、冲突检测和优先级管理
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
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    collaboration_status TEXT NOT NULL,
                    is_queryable INTEGER DEFAULT 1,
                    metadata TEXT
                )
            ''')
            
            # 创建索引以提高查询性能
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_type ON schedules(schedule_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_time ON schedules(start_time, end_time)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_active ON schedules(is_active)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_schedules_queryable ON schedules(is_queryable)')
        
        debug_logger.log_info('ScheduleManager', '数据库表初始化完成')

    def create_schedule(
        self,
        title: str,
        description: str,
        schedule_type: ScheduleType,
        start_time: str,
        end_time: str,
        priority: SchedulePriority = None,
        check_conflict: bool = True,
        **kwargs
    ) -> Tuple[bool, Optional[Schedule], str]:
        """
        创建新日程

        Args:
            title: 日程标题
            description: 日程描述
            schedule_type: 日程类型
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            priority: 日程优先级（如果未指定，根据类型自动设置）
            check_conflict: 是否检查冲突
            **kwargs: 其他参数

        Returns:
            (是否成功, 日程对象或None, 消息)
        """
        debug_logger.log_module('ScheduleManager', '创建新日程', {
            'title': title,
            'type': schedule_type.value,
            'start': start_time,
            'end': end_time
        })

        # 如果未指定优先级，根据类型设置默认优先级
        if priority is None:
            if schedule_type == ScheduleType.RECURRING:
                priority = SchedulePriority.CRITICAL
            elif schedule_type == ScheduleType.APPOINTMENT:
                priority = SchedulePriority.MEDIUM
            else:  # TEMPORARY
                priority = SchedulePriority.LOW

        # 检查日程冲突
        if check_conflict:
            has_conflict, conflict_schedule = self.check_conflict(start_time, end_time, priority)
            if has_conflict:
                message = f"日程冲突：时间段 {start_time} 到 {end_time} 已有优先级更高或相同的日程 '{conflict_schedule.title}'"
                debug_logger.log_info('ScheduleManager', message)
                return False, None, message

        # 创建对应类型的日程对象
        if schedule_type == ScheduleType.RECURRING:
            schedule = RecurringSchedule(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                priority=priority,
                **kwargs
            )
        elif schedule_type == ScheduleType.APPOINTMENT:
            schedule = AppointmentSchedule(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                priority=priority,
                **kwargs
            )
        else:  # TEMPORARY
            schedule = TemporarySchedule(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                priority=priority,
                **kwargs
            )

        # 保存到数据库
        import json
        try:
            with self.db.get_connection() as conn:
                conn.execute('''
                    INSERT INTO schedules (
                        schedule_id, title, description, schedule_type, 
                        priority, start_time, end_time, created_at,
                        is_active, collaboration_status, is_queryable, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    schedule.schedule_id,
                    schedule.title,
                    schedule.description,
                    schedule.schedule_type.value,
                    schedule.priority.value,
                    schedule.start_time,
                    schedule.end_time,
                    schedule.created_at,
                    1 if schedule.is_active else 0,
                    schedule.collaboration_status.value,
                    1 if schedule.is_queryable else 0,
                    json.dumps(schedule.metadata, ensure_ascii=False)
                ))

            message = f"日程创建成功：{title}"
            debug_logger.log_info('ScheduleManager', message, {
                'schedule_id': schedule.schedule_id
            })

            return True, schedule, message
            
        except Exception as e:
            message = f"创建日程失败: {str(e)}"
            debug_logger.log_error('ScheduleManager', message, e)
            return False, None, message

    def check_conflict(
        self,
        start_time: str,
        end_time: str,
        new_priority: SchedulePriority,
        exclude_schedule_id: str = None
    ) -> Tuple[bool, Optional[Schedule]]:
        """
        检查时间段是否与现有日程冲突
        高优先级日程可以覆盖低优先级日程

        Args:
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            new_priority: 新日程的优先级
            exclude_schedule_id: 排除的日程ID（用于更新时）

        Returns:
            (是否冲突, 冲突的日程对象或None)
        """
        import json
        
        with self.db.get_connection() as conn:
            # 查询时间段内的所有激活日程
            query = '''
                SELECT * FROM schedules 
                WHERE is_active = 1
                AND (
                    (start_time < ? AND end_time > ?)
                    OR (start_time >= ? AND start_time < ?)
                    OR (end_time > ? AND end_time <= ?)
                )
            '''
            params = [end_time, start_time, start_time, end_time, start_time, end_time]
            
            if exclude_schedule_id:
                query += ' AND schedule_id != ?'
                params.append(exclude_schedule_id)
            
            cursor = conn.execute(query, params)
            
            for row in cursor.fetchall():
                existing_priority = SchedulePriority(row[4])  # priority字段
                
                # 如果现有日程的优先级 >= 新日程的优先级，则冲突
                if existing_priority.value >= new_priority.value:
                    data = {
                        'schedule_id': row[0],
                        'title': row[1],
                        'description': row[2],
                        'schedule_type': row[3],
                        'priority': row[4],
                        'start_time': row[5],
                        'end_time': row[6],
                        'created_at': row[7],
                        'is_active': row[9] == 1,
                        'collaboration_status': row[10],
                        'is_queryable': row[11] == 1,
                        'metadata': json.loads(row[12]) if row[12] else {}
                    }
                    conflicting_schedule = Schedule.from_dict(data)
                    return True, conflicting_schedule
        
        return False, None

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        获取指定日程

        Args:
            schedule_id: 日程ID

        Returns:
            日程对象，不存在时返回None
        """
        import json
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM schedules WHERE schedule_id = ?',
                (schedule_id,)
            )
            row = cursor.fetchone()

            if row:
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'created_at': row[7],
                    'is_active': row[9] == 1,
                    'collaboration_status': row[10],
                    'is_queryable': row[11] == 1,
                    'metadata': json.loads(row[12]) if row[12] else {}
                }
                return Schedule.from_dict(data)

        return None

    def get_schedules_by_time_range(
        self,
        start_time: str,
        end_time: str,
        queryable_only: bool = True,
        active_only: bool = True
    ) -> List[Schedule]:
        """
        获取时间范围内的所有日程

        Args:
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            queryable_only: 是否只返回可查询的日程
            active_only: 是否只返回激活的日程

        Returns:
            日程列表
        """
        import json
        
        query = '''
            SELECT * FROM schedules 
            WHERE (
                (start_time < ? AND end_time > ?)
                OR (start_time >= ? AND start_time < ?)
            )
        '''
        params = [end_time, start_time, start_time, end_time]
        
        if queryable_only:
            query += ' AND is_queryable = 1'
        
        if active_only:
            query += ' AND is_active = 1'
        
        query += ' ORDER BY start_time ASC'
        
        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)
            
            schedules = []
            for row in cursor.fetchall():
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'created_at': row[7],
                    'is_active': row[9] == 1,
                    'collaboration_status': row[10],
                    'is_queryable': row[11] == 1,
                    'metadata': json.loads(row[12]) if row[12] else {}
                }
                schedules.append(Schedule.from_dict(data))
        
        return schedules

    def get_pending_collaboration_schedules(self) -> List[Schedule]:
        """
        获取待确认的协作日程

        Returns:
            待确认的日程列表
        """
        import json
        
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM schedules 
                WHERE collaboration_status = ?
                AND is_active = 1
                ORDER BY created_at ASC
            ''', (CollaborationStatus.PENDING.value,))
            
            schedules = []
            for row in cursor.fetchall():
                data = {
                    'schedule_id': row[0],
                    'title': row[1],
                    'description': row[2],
                    'schedule_type': row[3],
                    'priority': row[4],
                    'start_time': row[5],
                    'end_time': row[6],
                    'created_at': row[7],
                    'is_active': row[9] == 1,
                    'collaboration_status': row[10],
                    'is_queryable': row[11] == 1,
                    'metadata': json.loads(row[12]) if row[12] else {}
                }
                schedules.append(Schedule.from_dict(data))
        
        return schedules

    def confirm_collaboration(self, schedule_id: str, confirmed: bool) -> bool:
        """
        确认或拒绝协作日程

        Args:
            schedule_id: 日程ID
            confirmed: 是否确认

        Returns:
            是否操作成功
        """
        try:
            new_status = CollaborationStatus.CONFIRMED if confirmed else CollaborationStatus.REJECTED
            
            with self.db.get_connection() as conn:
                # 更新协作状态
                conn.execute('''
                    UPDATE schedules 
                    SET collaboration_status = ?,
                        is_queryable = ?,
                        updated_at = ?
                    WHERE schedule_id = ?
                ''', (
                    new_status.value,
                    1 if confirmed else 0,  # 确认后可查询，拒绝后不可查询
                    datetime.now().isoformat(),
                    schedule_id
                ))
            
            debug_logger.log_info('ScheduleManager', '协作日程状态更新', {
                'schedule_id': schedule_id,
                'confirmed': confirmed
            })
            
            return True
            
        except Exception as e:
            debug_logger.log_error('ScheduleManager', f'更新协作状态失败: {str(e)}', e)
            return False

    def update_schedule(
        self,
        schedule_id: str,
        **kwargs
    ) -> bool:
        """
        更新日程信息

        Args:
            schedule_id: 日程ID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        # 白名单验证允许更新的列名
        allowed_columns = {
            'title', 'description', 'start_time', 'end_time',
            'priority', 'is_active', 'collaboration_status', 'is_queryable'
        }
        
        try:
            if not kwargs:
                return False

            # 过滤只允许白名单中的列名
            safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed_columns}
            if not safe_kwargs:
                print(f"⚠ 没有有效的字段可更新")
                return False

            set_clause = ", ".join([f"{k} = ?" for k in safe_kwargs.keys()])
            set_clause += ", updated_at = ?"
            values = list(safe_kwargs.values()) + [datetime.now().isoformat(), schedule_id]

            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE schedules 
                    SET {set_clause}
                    WHERE schedule_id = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新日程时出错: {e}")
            return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        删除日程（软删除，设置为非激活状态）

        Args:
            schedule_id: 日程ID

        Returns:
            是否删除成功
        """
        try:
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE schedules 
                    SET is_active = 0, updated_at = ?
                    WHERE schedule_id = ?
                ''', (datetime.now().isoformat(), schedule_id))

            debug_logger.log_info('ScheduleManager', '日程删除成功', {
                'schedule_id': schedule_id
            })

            return True

        except Exception as e:
            debug_logger.log_error('ScheduleManager', f'删除日程失败: {str(e)}', e)
            return False

    def get_free_time_slots(
        self,
        date: str,
        slot_duration_minutes: int = 60
    ) -> List[Tuple[str, str]]:
        """
        获取指定日期的空闲时间段

        Args:
            date: 日期（ISO格式，如 "2024-01-15"）
            slot_duration_minutes: 最小时间段长度（分钟）

        Returns:
            空闲时间段列表 [(start_time, end_time), ...]
        """
        # 获取当天的所有日程
        start_of_day = f"{date}T00:00:00"
        end_of_day = f"{date}T23:59:59"
        
        schedules = self.get_schedules_by_time_range(start_of_day, end_of_day)
        
        # 按开始时间排序
        schedules.sort(key=lambda s: s.start_time)
        
        # 计算空闲时间段
        free_slots = []
        current_time = datetime.fromisoformat(start_of_day)
        end_time = datetime.fromisoformat(end_of_day)
        
        for schedule in schedules:
            schedule_start = datetime.fromisoformat(schedule.start_time)
            schedule_end = datetime.fromisoformat(schedule.end_time)
            
            # 如果当前时间到日程开始时间之间有足够的空隙
            if (schedule_start - current_time).total_seconds() / 60 >= slot_duration_minutes:
                free_slots.append((
                    current_time.isoformat(),
                    schedule_start.isoformat()
                ))
            
            # 更新当前时间到日程结束时间
            if schedule_end > current_time:
                current_time = schedule_end
        
        # 检查最后一个日程到当天结束是否有空闲时间
        if (end_time - current_time).total_seconds() / 60 >= slot_duration_minutes:
            free_slots.append((
                current_time.isoformat(),
                end_time.isoformat()
            ))
        
        return free_slots

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取日程统计信息

        Returns:
            统计信息字典
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN schedule_type = ? THEN 1 ELSE 0 END) as recurring,
                    SUM(CASE WHEN schedule_type = ? THEN 1 ELSE 0 END) as appointments,
                    SUM(CASE WHEN schedule_type = ? THEN 1 ELSE 0 END) as temporary,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN collaboration_status = ? THEN 1 ELSE 0 END) as pending_collaboration
                FROM schedules
            ''', (
                ScheduleType.RECURRING.value,
                ScheduleType.APPOINTMENT.value,
                ScheduleType.TEMPORARY.value,
                CollaborationStatus.PENDING.value
            ))

            row = cursor.fetchone()
            return {
                'total_schedules': row[0] or 0,
                'recurring': row[1] or 0,
                'appointments': row[2] or 0,
                'temporary': row[3] or 0,
                'active': row[4] or 0,
                'pending_collaboration': row[5] or 0
            }
