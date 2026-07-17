"""
事件管理模块
为智能体提供事件驱动功能，支持通知型和任务型事件
"""

import json
import uuid
import asyncio
import inspect
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from src.core.database_manager import DatabaseManager
from src.tools.debug_logger import get_debug_logger

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
        # 进程内监听器：用于把事件转发到 WebSocket / GUI 订阅者
        # Listeners registry: key=event_type(str), value=List[Callable]
        self._listeners: Dict[str, List[Callable]] = {}
        self._initialize_database()

        debug_logger.log_module('EventManager', '事件管理器初始化完成')

    def _initialize_database(self):
        """初始化数据库表"""
        with self.db.get_connection() as conn:
            # 创建事件表
            conn.execute('''
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
            conn.execute('''
                CREATE TABLE IF NOT EXISTS event_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    log_type TEXT NOT NULL,
                    log_content TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES events(event_id)
                )
            ''')

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
        try:
            with self.db.get_connection() as conn:
                conn.execute('''
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

            debug_logger.log_info('EventManager', '事件创建成功', {
                'event_id': event.event_id
            })

            return event

        except Exception as e:
            debug_logger.log_error('EventManager', f'创建事件失败: {str(e)}', e)
            raise RuntimeError(f"Failed to create event: {str(e)}") from e

    def add_event(self, **kwargs) -> Event:
        """
        事件添加的便捷入口（与 create_event 等价，供神经系统 channel 使用）。

        Returns:
            创建的事件对象
        """
        return self.create_event(**kwargs)

    def get_event(self, event_id: str) -> Optional[Event]:
        """
        获取指定事件

        Args:
            event_id: 事件ID

        Returns:
            事件对象，不存在时返回None
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM events WHERE event_id = ?',
                (event_id,)
            )
            row = cursor.fetchone()

            if row:
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
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM events
                WHERE status = ?
                ORDER BY priority DESC, created_at ASC
                LIMIT ?
            ''', (EventStatus.PENDING.value, limit))

            events = []
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

        with self.db.get_connection() as conn:
            cursor = conn.execute(query, params)

            events = []
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

    def get_events(
        self,
        status: Optional[EventStatus] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        列出事件（v4.0 神经系统入口）。

        Returns:
            事件列表
        """
        return self.get_all_events(status=status, event_type=event_type, limit=limit)

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

            with self.db.get_connection() as conn:
                # 更新事件状态
                conn.execute('''
                    UPDATE events
                    SET status = ?, updated_at = ?
                    WHERE event_id = ?
                ''', (status.value, now, event_id))

                # 如果是完成状态，记录完成时间
                if status == EventStatus.COMPLETED:
                    conn.execute('''
                        UPDATE events
                        SET completed_at = ?
                        WHERE event_id = ?
                    ''', (now, event_id))

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
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT INTO event_logs (event_id, log_type, log_content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (event_id, log_type, log_content, datetime.now().isoformat()))

    def get_event_logs(self, event_id: str) -> List[Dict[str, Any]]:
        """
        获取事件处理日志

        Args:
            event_id: 事件ID

        Returns:
            日志列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
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
            with self.db.get_connection() as conn:
                # 删除事件日志
                conn.execute(
                    'DELETE FROM event_logs WHERE event_id = ?',
                    (event_id,)
                )

                # 删除事件
                conn.execute(
                    'DELETE FROM events WHERE event_id = ?',
                    (event_id,)
                )

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
        with self.db.get_connection() as conn:
            cursor = conn.execute('''
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

    # =====================================================================
    # Stage D.1 / D.2 集成：进程内事件发布与订阅
    # 用于把 scheduler / proactive 等内部事件转发到 Web 后端 WebSocket 客户端
    # =====================================================================

    def subscribe(self, event_type: str, callback: Callable) -> Callable:
        """
        注册事件订阅者（按 event_type 字符串匹配）。
        Register an in-process listener for a given event type.

        Args:
            event_type: 事件类型字符串，例如 "scheduler_tick" / "proactive_message"
            callback: 回调函数，签名 callback(event_type: str, payload: dict)
                      可以是同步函数或 async 协程函数。

        Returns:
            取消订阅的函数 unsubscribe()，方便调用方做清理。
        """
        try:
            key = str(event_type or '').strip() or '*'
            self._listeners.setdefault(key, []).append(callback)

            def _unsubscribe() -> None:
                self.unsubscribe(event_type, callback)

            return _unsubscribe
        except Exception as e:
            debug_logger.log_error('EventManager', f'订阅事件失败({event_type}): {e}', e)
            return lambda: None

    def unsubscribe(self, event_type: str, callback: Callable) -> bool:
        """
        取消事件订阅。
        """
        try:
            key = str(event_type or '').strip() or '*'
            listeners = self._listeners.get(key)
            if not listeners:
                return False
            try:
                listeners.remove(callback)
            except ValueError:
                return False
            if not listeners:
                self._listeners.pop(key, None)
            return True
        except Exception as e:
            debug_logger.log_error('EventManager', f'取消订阅失败({event_type}): {e}', e)
            return False

    def publish(self, event_or_type: Union[str, 'Event', Any],
                payload: Optional[Dict[str, Any]] = None) -> None:
        """
        发布事件到所有匹配的订阅者（不阻塞）。
        Publish an event to all matching listeners without blocking.

        支持两种签名（保持向后兼容）：
        1) publish(event_type: str, payload: dict)
           - 用于 BackgroundScheduler / ProactiveEngine 等内部模块
        2) publish(event: Event)
           - 兼容未来 / 现有以 Event 对象发布的调用方

        异常保护：单个 listener 抛错不会影响其他 listener。
        """
        try:
            # 解析 event_type 与 payload
            event_type: str
            if isinstance(event_or_type, str):
                event_type = event_or_type
                payload_dict: Dict[str, Any] = dict(payload or {})
            else:
                # 视为 Event 对象
                event = event_or_type
                event_type = (
                    getattr(event, 'event_type', None).value
                    if hasattr(getattr(event, 'event_type', None), 'value')
                    else str(getattr(event, 'event_type', 'event'))
                )
                payload_dict = {
                    'event_id': getattr(event, 'event_id', None),
                    'title': getattr(event, 'title', ''),
                    'description': getattr(event, 'description', ''),
                    'content': (
                        getattr(event, 'content', '')
                        or (event.metadata.get('content') if getattr(event, 'metadata', None) else '')
                    ),
                    'priority': getattr(event, 'priority', None).value
                    if hasattr(getattr(event, 'priority', None), 'value')
                    else getattr(event, 'priority', None),
                    'metadata': dict(getattr(event, 'metadata', {}) or {}),
                    'created_at': getattr(event, 'created_at', None),
                }
                # 注入显式 payload（如果传入）
                if payload:
                    payload_dict.update(payload)

            # 合并时间戳（仅在缺失时填充）
            if 'timestamp' not in payload_dict:
                payload_dict['timestamp'] = datetime.now().isoformat()

            # 调度同步 listener；async listener 走 asyncio 事件循环
            listeners = list(self._listeners.get(event_type, [])) + \
                        list(self._listeners.get('*', []))
            for cb in listeners:
                self._dispatch_listener(cb, event_type, payload_dict)
        except Exception as e:
            debug_logger.log_error('EventManager', f'发布事件失败: {e}', e)

    @staticmethod
    def _dispatch_listener(cb: Callable, event_type: str,
                            payload: Dict[str, Any]) -> None:
        """
        分发事件到单个 listener。同步函数直接调用，async 协程尝试调度到事件循环。
        """
        try:
            if inspect.iscoroutinefunction(cb):
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 当前已有运行中的事件循环，调度为 task
                        loop.create_task(cb(event_type, payload))
                    else:
                        # 没有运行中的循环，直接同步等待
                        loop.run_until_complete(cb(event_type, payload))
                except RuntimeError:
                    # 没有事件循环时降级：run_until_complete 兜底
                    try:
                        asyncio.run(cb(event_type, payload))
                    except Exception as inner_e:
                        debug_logger.log_error(
                            'EventManager',
                            f'async listener 执行失败({event_type}): {inner_e}',
                            inner_e,
                        )
            else:
                cb(event_type, payload)
        except Exception as e:
            debug_logger.log_error('EventManager', f'listener 执行失败({event_type}): {e}', e)


# 进程内单例（供 BackgroundScheduler / ProactiveEngine 等模块无依赖访问）
_global_event_manager: Optional[EventManager] = None
_global_event_manager_lock = None


def get_event_manager() -> EventManager:
    """
    获取全局 EventManager 单例（线程安全）。
    """
    global _global_event_manager
    try:
        import threading as _threading
        global _global_event_manager_lock
        if _global_event_manager_lock is None:
            _global_event_manager_lock = _threading.Lock()
        with _global_event_manager_lock:
            if _global_event_manager is None:
                _global_event_manager = EventManager()
    except Exception as e:
        debug_logger.log_error('EventManager', f'获取全局 EventManager 失败: {e}', e)
        if _global_event_manager is None:
            _global_event_manager = EventManager()
    return _global_event_manager
