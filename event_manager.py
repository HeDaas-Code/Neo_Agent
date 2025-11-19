"""
事件管理模块
为智能体提供事件驱动功能，支持通知型和任务型事件
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class EventType(Enum):
    """事件类型枚举"""
    NOTIFICATION = "notification"  # 通知型事件
    TASK = "task"  # 任务型事件


class EventPriority(Enum):
    """事件优先级枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class EventStatus(Enum):
    """事件状态枚举"""
    PENDING = "pending"  # 待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class Event:
    """
    事件基类
    """

    def __init__(
        self,
        event_id: str = None,
        title: str = "",
        description: str = "",
        event_type: EventType = EventType.NOTIFICATION,
        priority: EventPriority = EventPriority.MEDIUM,
        created_at: str = None,
        status: EventStatus = EventStatus.PENDING,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化事件

        Args:
            event_id: 事件唯一标识符
            title: 事件标题
            description: 事件描述
            event_type: 事件类型
            priority: 事件优先级
            created_at: 创建时间
            status: 事件状态
            metadata: 附加元数据
        """
        self.event_id = event_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.event_type = event_type
        self.priority = priority
        self.created_at = created_at or datetime.now().isoformat()
        self.status = status
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        将事件转换为字典

        Returns:
            事件字典表示
        """
        return {
            'event_id': self.event_id,
            'title': self.title,
            'description': self.description,
            'event_type': self.event_type.value,
            'priority': self.priority.value,
            'created_at': self.created_at,
            'status': self.status.value,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """
        从字典创建事件

        Args:
            data: 事件字典数据

        Returns:
            事件对象
        """
        return cls(
            event_id=data.get('event_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            event_type=EventType(data.get('event_type', 'notification')),
            priority=EventPriority(data.get('priority', 2)),
            created_at=data.get('created_at'),
            status=EventStatus(data.get('status', 'pending')),
            metadata=data.get('metadata', {})
        )


class NotificationEvent(Event):
    """
    通知型事件
    智能体需要立即理解并向用户说明的外部信息
    """

    def __init__(self, **kwargs):
        """初始化通知型事件"""
        super().__init__(event_type=EventType.NOTIFICATION, **kwargs)


class TaskEvent(Event):
    """
    任务型事件
    智能体需要理解任务要求、规划并完成任务
    """

    def __init__(
        self,
        task_requirements: str = "",
        completion_criteria: str = "",
        **kwargs
    ):
        """
        初始化任务型事件

        Args:
            task_requirements: 任务要求描述
            completion_criteria: 任务完成标准
            **kwargs: 其他事件参数
        """
        super().__init__(event_type=EventType.TASK, **kwargs)
        self.metadata['task_requirements'] = task_requirements
        self.metadata['completion_criteria'] = completion_criteria
        self.metadata['subtasks'] = []  # 子任务列表
        self.metadata['progress'] = []  # 进度记录


class EventManager:
    """
    事件管理器
    负责事件的创建、存储、检索和处理
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化事件管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager or DatabaseManager()
        self._initialize_database()
        
        debug_logger.log_module('EventManager', '事件管理器初始化完成')

    def _initialize_database(self):
        """初始化数据库表"""
        # 创建事件表
        self.db.conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                event_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                completed_at TEXT,
                metadata TEXT
            )
        ''')
        
        # 创建事件处理日志表
        self.db.conn.execute('''
            CREATE TABLE IF NOT EXISTS event_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                log_type TEXT NOT NULL,
                log_content TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events(event_id)
            )
        ''')
        
        self.db.conn.commit()
        debug_logger.log_info('EventManager', '数据库表初始化完成')

    def create_event(
        self,
        title: str,
        description: str,
        event_type: EventType,
        priority: EventPriority = EventPriority.MEDIUM,
        task_requirements: str = "",
        completion_criteria: str = ""
    ) -> Event:
        """
        创建新事件

        Args:
            title: 事件标题
            description: 事件描述
            event_type: 事件类型
            priority: 事件优先级
            task_requirements: 任务要求（仅任务型事件）
            completion_criteria: 完成标准（仅任务型事件）

        Returns:
            创建的事件对象
        """
        debug_logger.log_module('EventManager', '创建新事件', {
            'title': title,
            'type': event_type.value
        })

        if event_type == EventType.TASK:
            event = TaskEvent(
                title=title,
                description=description,
                priority=priority,
                task_requirements=task_requirements,
                completion_criteria=completion_criteria
            )
        else:
            event = NotificationEvent(
                title=title,
                description=description,
                priority=priority
            )

        # 保存到数据库
        import json
        self.db.conn.execute('''
            INSERT INTO events (
                event_id, title, description, event_type, 
                priority, status, created_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.event_id,
            event.title,
            event.description,
            event.event_type.value,
            event.priority.value,
            event.status.value,
            event.created_at,
            json.dumps(event.metadata, ensure_ascii=False)
        ))
        self.db.conn.commit()

        debug_logger.log_info('EventManager', '事件创建成功', {
            'event_id': event.event_id
        })

        return event

    def get_event(self, event_id: str) -> Optional[Event]:
        """
        获取指定事件

        Args:
            event_id: 事件ID

        Returns:
            事件对象，不存在时返回None
        """
        cursor = self.db.conn.execute(
            'SELECT * FROM events WHERE event_id = ?',
            (event_id,)
        )
        row = cursor.fetchone()

        if row:
            import json
            data = {
                'event_id': row[0],
                'title': row[1],
                'description': row[2],
                'event_type': row[3],
                'priority': row[4],
                'status': row[5],
                'created_at': row[6],
                'metadata': json.loads(row[9]) if row[9] else {}
            }
            return Event.from_dict(data)

        return None

    def get_pending_events(self, limit: int = 10) -> List[Event]:
        """
        获取待处理的事件列表（按优先级和创建时间排序）

        Args:
            limit: 返回数量限制

        Returns:
            事件列表
        """
        cursor = self.db.conn.execute('''
            SELECT * FROM events 
            WHERE status = ?
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        ''', (EventStatus.PENDING.value, limit))

        events = []
        import json
        for row in cursor.fetchall():
            data = {
                'event_id': row[0],
                'title': row[1],
                'description': row[2],
                'event_type': row[3],
                'priority': row[4],
                'status': row[5],
                'created_at': row[6],
                'metadata': json.loads(row[9]) if row[9] else {}
            }
            events.append(Event.from_dict(data))

        return events

    def get_all_events(
        self,
        status: Optional[EventStatus] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """
        获取所有事件（可选过滤）

        Args:
            status: 状态过滤
            event_type: 类型过滤
            limit: 返回数量限制

        Returns:
            事件列表
        """
        query = 'SELECT * FROM events WHERE 1=1'
        params = []

        if status:
            query += ' AND status = ?'
            params.append(status.value)

        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type.value)

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor = self.db.conn.execute(query, params)

        events = []
        import json
        for row in cursor.fetchall():
            data = {
                'event_id': row[0],
                'title': row[1],
                'description': row[2],
                'event_type': row[3],
                'priority': row[4],
                'status': row[5],
                'created_at': row[6],
                'metadata': json.loads(row[9]) if row[9] else {}
            }
            events.append(Event.from_dict(data))

        return events

    def update_event_status(
        self,
        event_id: str,
        status: EventStatus,
        log_message: str = ""
    ) -> bool:
        """
        更新事件状态

        Args:
            event_id: 事件ID
            status: 新状态
            log_message: 日志消息

        Returns:
            是否成功
        """
        try:
            now = datetime.now().isoformat()
            
            # 更新事件状态
            self.db.conn.execute('''
                UPDATE events 
                SET status = ?, updated_at = ?
                WHERE event_id = ?
            ''', (status.value, now, event_id))

            # 如果是完成状态，记录完成时间
            if status == EventStatus.COMPLETED:
                self.db.conn.execute('''
                    UPDATE events 
                    SET completed_at = ?
                    WHERE event_id = ?
                ''', (now, event_id))

            self.db.conn.commit()

            # 添加日志
            if log_message:
                self.add_event_log(event_id, 'status_change', log_message)

            debug_logger.log_info('EventManager', '事件状态更新', {
                'event_id': event_id,
                'new_status': status.value
            })

            return True

        except Exception as e:
            debug_logger.log_error('EventManager', f'更新事件状态失败: {str(e)}', e)
            return False

    def add_event_log(
        self,
        event_id: str,
        log_type: str,
        log_content: str
    ):
        """
        添加事件处理日志

        Args:
            event_id: 事件ID
            log_type: 日志类型
            log_content: 日志内容
        """
        self.db.conn.execute('''
            INSERT INTO event_logs (event_id, log_type, log_content, created_at)
            VALUES (?, ?, ?, ?)
        ''', (event_id, log_type, log_content, datetime.now().isoformat()))
        self.db.conn.commit()

    def get_event_logs(self, event_id: str) -> List[Dict[str, Any]]:
        """
        获取事件处理日志

        Args:
            event_id: 事件ID

        Returns:
            日志列表
        """
        cursor = self.db.conn.execute('''
            SELECT log_type, log_content, created_at
            FROM event_logs
            WHERE event_id = ?
            ORDER BY created_at ASC
        ''', (event_id,))

        logs = []
        for row in cursor.fetchall():
            logs.append({
                'log_type': row[0],
                'log_content': row[1],
                'created_at': row[2]
            })

        return logs

    def delete_event(self, event_id: str) -> bool:
        """
        删除事件

        Args:
            event_id: 事件ID

        Returns:
            是否成功
        """
        try:
            # 删除事件日志
            self.db.conn.execute(
                'DELETE FROM event_logs WHERE event_id = ?',
                (event_id,)
            )
            
            # 删除事件
            self.db.conn.execute(
                'DELETE FROM events WHERE event_id = ?',
                (event_id,)
            )
            
            self.db.conn.commit()

            debug_logger.log_info('EventManager', '事件删除成功', {
                'event_id': event_id
            })

            return True

        except Exception as e:
            debug_logger.log_error('EventManager', f'删除事件失败: {str(e)}', e)
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取事件统计信息

        Returns:
            统计信息字典
        """
        cursor = self.db.conn.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as processing,
                SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN event_type = ? THEN 1 ELSE 0 END) as notifications,
                SUM(CASE WHEN event_type = ? THEN 1 ELSE 0 END) as tasks
            FROM events
        ''', (
            EventStatus.PENDING.value,
            EventStatus.PROCESSING.value,
            EventStatus.COMPLETED.value,
            EventType.NOTIFICATION.value,
            EventType.TASK.value
        ))

        row = cursor.fetchone()
        return {
            'total_events': row[0] or 0,
            'pending': row[1] or 0,
            'processing': row[2] or 0,
            'completed': row[3] or 0,
            'notifications': row[4] or 0,
            'tasks': row[5] or 0
        }
