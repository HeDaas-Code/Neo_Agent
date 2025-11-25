"""
导演模式模块
为智能体提供预设时间线进行角色扮演功能
"""

import uuid
import json
import threading
import time as time_module
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from enum import Enum
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class ScenarioType(Enum):
    """场景类型枚举"""
    ENVIRONMENT = "environment"  # 环境变化场景
    DIALOGUE = "dialogue"  # 对话提示场景
    EVENT = "event"  # 事件触发场景
    EMOTION = "emotion"  # 情感变化场景
    ACTION = "action"  # 动作描述场景


class TriggerType(Enum):
    """触发类型枚举"""
    TIME = "time"  # 时间触发（基于时间线开始后的相对时间）
    CONDITION = "condition"  # 条件触发（基于特定条件）
    MANUAL = "manual"  # 手动触发
    SEQUENCE = "sequence"  # 顺序触发（上一个场景完成后触发）


class ScenarioStatus(Enum):
    """场景状态枚举"""
    PENDING = "pending"  # 待触发
    ACTIVE = "active"  # 激活中
    COMPLETED = "completed"  # 已完成
    SKIPPED = "skipped"  # 已跳过


class Scenario:
    """
    场景类
    表示时间线中的单个场景节点
    """

    def __init__(
        self,
        scenario_id: str = None,
        name: str = "",
        description: str = "",
        scenario_type: ScenarioType = ScenarioType.DIALOGUE,
        trigger_type: TriggerType = TriggerType.TIME,
        trigger_time: int = 0,  # 触发时间（秒，相对于时间线开始）
        trigger_condition: str = "",  # 触发条件（用于条件触发）
        content: Dict[str, Any] = None,  # 场景内容
        duration: int = 0,  # 持续时间（秒），0表示无限期
        auto_advance: bool = True,  # 是否自动进入下一场景
        environment_uuid: str = None,  # 关联的环境UUID
        status: ScenarioStatus = ScenarioStatus.PENDING,
        metadata: Dict[str, Any] = None,
        created_at: str = None
    ):
        """
        初始化场景

        Args:
            scenario_id: 场景唯一标识符
            name: 场景名称
            description: 场景描述
            scenario_type: 场景类型
            trigger_type: 触发类型
            trigger_time: 触发时间（秒）
            trigger_condition: 触发条件
            content: 场景内容
            duration: 持续时间（秒）
            auto_advance: 是否自动进入下一场景
            environment_uuid: 关联的环境UUID
            status: 场景状态
            metadata: 附加元数据
            created_at: 创建时间
        """
        self.scenario_id = scenario_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.scenario_type = scenario_type
        self.trigger_type = trigger_type
        self.trigger_time = trigger_time
        self.trigger_condition = trigger_condition
        self.content = content or {}
        self.duration = duration
        self.auto_advance = auto_advance
        self.environment_uuid = environment_uuid
        self.status = status
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        将场景转换为字典

        Returns:
            场景字典表示
        """
        return {
            'scenario_id': self.scenario_id,
            'name': self.name,
            'description': self.description,
            'scenario_type': self.scenario_type.value,
            'trigger_type': self.trigger_type.value,
            'trigger_time': self.trigger_time,
            'trigger_condition': self.trigger_condition,
            'content': self.content,
            'duration': self.duration,
            'auto_advance': self.auto_advance,
            'environment_uuid': self.environment_uuid,
            'status': self.status.value,
            'metadata': self.metadata,
            'created_at': self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Scenario':
        """
        从字典创建场景

        Args:
            data: 场景字典数据

        Returns:
            场景对象
        """
        return cls(
            scenario_id=data.get('scenario_id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            scenario_type=ScenarioType(data.get('scenario_type', 'dialogue')),
            trigger_type=TriggerType(data.get('trigger_type', 'time')),
            trigger_time=data.get('trigger_time', 0),
            trigger_condition=data.get('trigger_condition', ''),
            content=data.get('content', {}),
            duration=data.get('duration', 0),
            auto_advance=data.get('auto_advance', True),
            environment_uuid=data.get('environment_uuid'),
            status=ScenarioStatus(data.get('status', 'pending')),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at')
        )


class Timeline:
    """
    时间线类
    管理一系列场景的集合
    """

    def __init__(
        self,
        timeline_id: str = None,
        name: str = "",
        description: str = "",
        scenarios: List[Scenario] = None,
        is_active: bool = False,
        is_paused: bool = False,
        start_time: str = None,
        current_scenario_index: int = -1,
        elapsed_time: int = 0,  # 已经过的时间（秒）
        metadata: Dict[str, Any] = None,
        created_at: str = None,
        updated_at: str = None
    ):
        """
        初始化时间线

        Args:
            timeline_id: 时间线唯一标识符
            name: 时间线名称
            description: 时间线描述
            scenarios: 场景列表
            is_active: 是否激活
            is_paused: 是否暂停
            start_time: 开始时间
            current_scenario_index: 当前场景索引
            elapsed_time: 已经过的时间（秒）
            metadata: 附加元数据
            created_at: 创建时间
            updated_at: 更新时间
        """
        self.timeline_id = timeline_id or str(uuid.uuid4())
        self.name = name
        self.description = description
        self.scenarios = scenarios or []
        self.is_active = is_active
        self.is_paused = is_paused
        self.start_time = start_time
        self.current_scenario_index = current_scenario_index
        self.elapsed_time = elapsed_time
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()

    def add_scenario(self, scenario: Scenario):
        """
        添加场景到时间线

        Args:
            scenario: 场景对象
        """
        self.scenarios.append(scenario)
        # 按触发时间排序
        self.scenarios.sort(key=lambda s: s.trigger_time)
        self.updated_at = datetime.now().isoformat()

    def remove_scenario(self, scenario_id: str) -> bool:
        """
        从时间线中移除场景

        Args:
            scenario_id: 场景ID

        Returns:
            是否成功移除
        """
        for i, scenario in enumerate(self.scenarios):
            if scenario.scenario_id == scenario_id:
                self.scenarios.pop(i)
                self.updated_at = datetime.now().isoformat()
                return True
        return False

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """
        获取指定场景

        Args:
            scenario_id: 场景ID

        Returns:
            场景对象或None
        """
        for scenario in self.scenarios:
            if scenario.scenario_id == scenario_id:
                return scenario
        return None

    def get_current_scenario(self) -> Optional[Scenario]:
        """
        获取当前场景

        Returns:
            当前场景对象或None
        """
        if 0 <= self.current_scenario_index < len(self.scenarios):
            return self.scenarios[self.current_scenario_index]
        return None

    def get_next_scenario(self) -> Optional[Scenario]:
        """
        获取下一个场景

        Returns:
            下一个场景对象或None
        """
        next_index = self.current_scenario_index + 1
        if 0 <= next_index < len(self.scenarios):
            return self.scenarios[next_index]
        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        将时间线转换为字典

        Returns:
            时间线字典表示
        """
        return {
            'timeline_id': self.timeline_id,
            'name': self.name,
            'description': self.description,
            'scenarios': [s.to_dict() for s in self.scenarios],
            'is_active': self.is_active,
            'is_paused': self.is_paused,
            'start_time': self.start_time,
            'current_scenario_index': self.current_scenario_index,
            'elapsed_time': self.elapsed_time,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timeline':
        """
        从字典创建时间线

        Args:
            data: 时间线字典数据

        Returns:
            时间线对象
        """
        scenarios = [Scenario.from_dict(s) for s in data.get('scenarios', [])]
        return cls(
            timeline_id=data.get('timeline_id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            scenarios=scenarios,
            is_active=data.get('is_active', False),
            is_paused=data.get('is_paused', False),
            start_time=data.get('start_time'),
            current_scenario_index=data.get('current_scenario_index', -1),
            elapsed_time=data.get('elapsed_time', 0),
            metadata=data.get('metadata', {}),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )


class DirectorMode:
    """
    导演模式管理器
    负责时间线的创建、管理、执行和控制
    """

    def __init__(
        self,
        db_manager: DatabaseManager = None,
        scenario_callback: Optional[Callable[[Scenario, 'DirectorMode'], None]] = None,
        narration_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化导演模式管理器

        Args:
            db_manager: 数据库管理器实例
            scenario_callback: 场景触发时的回调函数
            narration_callback: 旁白输出的回调函数
        """
        self.db = db_manager or DatabaseManager()
        self.scenario_callback = scenario_callback
        self.narration_callback = narration_callback

        # 当前活动的时间线
        self._active_timeline: Optional[Timeline] = None

        # 时间线执行线程
        self._executor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 初始化数据库表
        self._initialize_database()

        debug_logger.log_module('DirectorMode', '导演模式管理器初始化完成')

    def _initialize_database(self):
        """初始化导演模式相关的数据库表"""
        with self.db.get_connection() as conn:
            # 创建时间线表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS director_timelines (
                    timeline_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 0,
                    is_paused INTEGER DEFAULT 0,
                    start_time TEXT,
                    current_scenario_index INTEGER DEFAULT -1,
                    elapsed_time INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 创建场景表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS director_scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    timeline_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    scenario_type TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_time INTEGER DEFAULT 0,
                    trigger_condition TEXT,
                    content TEXT,
                    duration INTEGER DEFAULT 0,
                    auto_advance INTEGER DEFAULT 1,
                    environment_uuid TEXT,
                    status TEXT DEFAULT 'pending',
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    sort_order INTEGER DEFAULT 0,
                    FOREIGN KEY (timeline_id) REFERENCES director_timelines(timeline_id) ON DELETE CASCADE
                )
            ''')

            # 创建场景执行日志表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS director_scenario_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id TEXT NOT NULL,
                    timeline_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scenario_id) REFERENCES director_scenarios(scenario_id) ON DELETE CASCADE
                )
            ''')

            # 创建索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_scenarios_timeline ON director_scenarios(timeline_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_scenarios_sort ON director_scenarios(sort_order)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_logs_scenario ON director_scenario_logs(scenario_id)')

        debug_logger.log_info('DirectorMode', '数据库表初始化完成')

    def emit_narration(self, message: str):
        """
        输出旁白提示

        Args:
            message: 旁白消息
        """
        narration = f"🎬 [导演模式] {message}"
        print(narration)

        if self.narration_callback:
            self.narration_callback(narration)

        debug_logger.log_info('DirectorMode', '旁白输出', {'message': message})

    # ==================== 时间线管理方法 ====================

    def create_timeline(
        self,
        name: str,
        description: str = "",
        metadata: Dict[str, Any] = None
    ) -> Timeline:
        """
        创建新的时间线

        Args:
            name: 时间线名称
            description: 时间线描述
            metadata: 附加元数据

        Returns:
            创建的时间线对象
        """
        debug_logger.log_module('DirectorMode', '创建新时间线', {'name': name})

        timeline = Timeline(
            name=name,
            description=description,
            metadata=metadata or {}
        )

        # 保存到数据库
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT INTO director_timelines
                (timeline_id, name, description, is_active, is_paused, 
                 current_scenario_index, elapsed_time, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timeline.timeline_id,
                timeline.name,
                timeline.description,
                1 if timeline.is_active else 0,
                1 if timeline.is_paused else 0,
                timeline.current_scenario_index,
                timeline.elapsed_time,
                json.dumps(timeline.metadata, ensure_ascii=False),
                timeline.created_at,
                timeline.updated_at
            ))

        debug_logger.log_info('DirectorMode', '时间线创建成功', {
            'timeline_id': timeline.timeline_id
        })

        return timeline

    def get_timeline(self, timeline_id: str) -> Optional[Timeline]:
        """
        获取指定时间线

        Args:
            timeline_id: 时间线ID

        Returns:
            时间线对象或None
        """
        with self.db.get_connection() as conn:
            # 获取时间线基本信息
            cursor = conn.execute(
                'SELECT * FROM director_timelines WHERE timeline_id = ?',
                (timeline_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            # 获取时间线的场景列表
            scenarios_cursor = conn.execute('''
                SELECT * FROM director_scenarios
                WHERE timeline_id = ?
                ORDER BY sort_order ASC, trigger_time ASC
            ''', (timeline_id,))

            scenarios = []
            for scenario_row in scenarios_cursor.fetchall():
                scenario = Scenario(
                    scenario_id=scenario_row[0],
                    name=scenario_row[2],
                    description=scenario_row[3],
                    scenario_type=ScenarioType(scenario_row[4]),
                    trigger_type=TriggerType(scenario_row[5]),
                    trigger_time=scenario_row[6],
                    trigger_condition=scenario_row[7],
                    content=json.loads(scenario_row[8]) if scenario_row[8] else {},
                    duration=scenario_row[9],
                    auto_advance=bool(scenario_row[10]),
                    environment_uuid=scenario_row[11],
                    status=ScenarioStatus(scenario_row[12]),
                    metadata=json.loads(scenario_row[13]) if scenario_row[13] else {},
                    created_at=scenario_row[14]
                )
                scenarios.append(scenario)

            # 构建时间线对象
            timeline = Timeline(
                timeline_id=row[0],
                name=row[1],
                description=row[2],
                is_active=bool(row[3]),
                is_paused=bool(row[4]),
                start_time=row[5],
                current_scenario_index=row[6],
                elapsed_time=row[7],
                metadata=json.loads(row[8]) if row[8] else {},
                created_at=row[9],
                updated_at=row[10],
                scenarios=scenarios
            )

            return timeline

    def get_all_timelines(self) -> List[Timeline]:
        """
        获取所有时间线

        Returns:
            时间线列表
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT timeline_id FROM director_timelines ORDER BY created_at DESC'
            )
            timeline_ids = [row[0] for row in cursor.fetchall()]

        timelines = []
        for timeline_id in timeline_ids:
            timeline = self.get_timeline(timeline_id)
            if timeline:
                timelines.append(timeline)

        return timelines

    def update_timeline(self, timeline: Timeline) -> bool:
        """
        更新时间线

        Args:
            timeline: 时间线对象

        Returns:
            是否成功更新
        """
        try:
            timeline.updated_at = datetime.now().isoformat()

            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE director_timelines
                    SET name = ?, description = ?, is_active = ?, is_paused = ?,
                        start_time = ?, current_scenario_index = ?, elapsed_time = ?,
                        metadata = ?, updated_at = ?
                    WHERE timeline_id = ?
                ''', (
                    timeline.name,
                    timeline.description,
                    1 if timeline.is_active else 0,
                    1 if timeline.is_paused else 0,
                    timeline.start_time,
                    timeline.current_scenario_index,
                    timeline.elapsed_time,
                    json.dumps(timeline.metadata, ensure_ascii=False),
                    timeline.updated_at,
                    timeline.timeline_id
                ))

            debug_logger.log_info('DirectorMode', '时间线更新成功', {
                'timeline_id': timeline.timeline_id
            })

            return True
        except Exception as e:
            debug_logger.log_error('DirectorMode', f'更新时间线失败: {str(e)}', e)
            return False

    def delete_timeline(self, timeline_id: str) -> bool:
        """
        删除时间线

        Args:
            timeline_id: 时间线ID

        Returns:
            是否成功删除
        """
        try:
            # 如果是活动的时间线，先停止
            if self._active_timeline and self._active_timeline.timeline_id == timeline_id:
                self.stop_timeline()

            with self.db.get_connection() as conn:
                # 删除场景日志
                conn.execute(
                    'DELETE FROM director_scenario_logs WHERE timeline_id = ?',
                    (timeline_id,)
                )
                # 删除场景
                conn.execute(
                    'DELETE FROM director_scenarios WHERE timeline_id = ?',
                    (timeline_id,)
                )
                # 删除时间线
                conn.execute(
                    'DELETE FROM director_timelines WHERE timeline_id = ?',
                    (timeline_id,)
                )

            debug_logger.log_info('DirectorMode', '时间线删除成功', {
                'timeline_id': timeline_id
            })

            return True
        except Exception as e:
            debug_logger.log_error('DirectorMode', f'删除时间线失败: {str(e)}', e)
            return False

    # ==================== 场景管理方法 ====================

    def add_scenario_to_timeline(
        self,
        timeline_id: str,
        name: str,
        description: str = "",
        scenario_type: ScenarioType = ScenarioType.DIALOGUE,
        trigger_type: TriggerType = TriggerType.TIME,
        trigger_time: int = 0,
        trigger_condition: str = "",
        content: Dict[str, Any] = None,
        duration: int = 0,
        auto_advance: bool = True,
        environment_uuid: str = None,
        metadata: Dict[str, Any] = None
    ) -> Scenario:
        """
        向时间线添加场景

        Args:
            timeline_id: 时间线ID
            name: 场景名称
            description: 场景描述
            scenario_type: 场景类型
            trigger_type: 触发类型
            trigger_time: 触发时间（秒）
            trigger_condition: 触发条件
            content: 场景内容
            duration: 持续时间（秒）
            auto_advance: 是否自动进入下一场景
            environment_uuid: 关联的环境UUID
            metadata: 附加元数据

        Returns:
            创建的场景对象
        """
        debug_logger.log_module('DirectorMode', '添加场景到时间线', {
            'timeline_id': timeline_id,
            'name': name
        })

        scenario = Scenario(
            name=name,
            description=description,
            scenario_type=scenario_type,
            trigger_type=trigger_type,
            trigger_time=trigger_time,
            trigger_condition=trigger_condition,
            content=content or {},
            duration=duration,
            auto_advance=auto_advance,
            environment_uuid=environment_uuid,
            metadata=metadata or {}
        )

        # 获取当前场景数量作为排序顺序
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM director_scenarios WHERE timeline_id = ?',
                (timeline_id,)
            )
            sort_order = cursor.fetchone()[0]

            # 保存到数据库
            conn.execute('''
                INSERT INTO director_scenarios
                (scenario_id, timeline_id, name, description, scenario_type, trigger_type,
                 trigger_time, trigger_condition, content, duration, auto_advance,
                 environment_uuid, status, metadata, created_at, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                scenario.scenario_id,
                timeline_id,
                scenario.name,
                scenario.description,
                scenario.scenario_type.value,
                scenario.trigger_type.value,
                scenario.trigger_time,
                scenario.trigger_condition,
                json.dumps(scenario.content, ensure_ascii=False),
                scenario.duration,
                1 if scenario.auto_advance else 0,
                scenario.environment_uuid,
                scenario.status.value,
                json.dumps(scenario.metadata, ensure_ascii=False),
                scenario.created_at,
                sort_order
            ))

            # 更新时间线的updated_at
            conn.execute('''
                UPDATE director_timelines
                SET updated_at = ?
                WHERE timeline_id = ?
            ''', (datetime.now().isoformat(), timeline_id))

        debug_logger.log_info('DirectorMode', '场景添加成功', {
            'scenario_id': scenario.scenario_id
        })

        return scenario

    def update_scenario(self, scenario: Scenario, timeline_id: str) -> bool:
        """
        更新场景

        Args:
            scenario: 场景对象
            timeline_id: 时间线ID

        Returns:
            是否成功更新
        """
        try:
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE director_scenarios
                    SET name = ?, description = ?, scenario_type = ?, trigger_type = ?,
                        trigger_time = ?, trigger_condition = ?, content = ?, duration = ?,
                        auto_advance = ?, environment_uuid = ?, status = ?, metadata = ?
                    WHERE scenario_id = ?
                ''', (
                    scenario.name,
                    scenario.description,
                    scenario.scenario_type.value,
                    scenario.trigger_type.value,
                    scenario.trigger_time,
                    scenario.trigger_condition,
                    json.dumps(scenario.content, ensure_ascii=False),
                    scenario.duration,
                    1 if scenario.auto_advance else 0,
                    scenario.environment_uuid,
                    scenario.status.value,
                    json.dumps(scenario.metadata, ensure_ascii=False),
                    scenario.scenario_id
                ))

                # 更新时间线的updated_at
                conn.execute('''
                    UPDATE director_timelines
                    SET updated_at = ?
                    WHERE timeline_id = ?
                ''', (datetime.now().isoformat(), timeline_id))

            debug_logger.log_info('DirectorMode', '场景更新成功', {
                'scenario_id': scenario.scenario_id
            })

            return True
        except Exception as e:
            debug_logger.log_error('DirectorMode', f'更新场景失败: {str(e)}', e)
            return False

    def delete_scenario(self, scenario_id: str) -> bool:
        """
        删除场景

        Args:
            scenario_id: 场景ID

        Returns:
            是否成功删除
        """
        try:
            with self.db.get_connection() as conn:
                # 删除场景日志
                conn.execute(
                    'DELETE FROM director_scenario_logs WHERE scenario_id = ?',
                    (scenario_id,)
                )
                # 删除场景
                conn.execute(
                    'DELETE FROM director_scenarios WHERE scenario_id = ?',
                    (scenario_id,)
                )

            debug_logger.log_info('DirectorMode', '场景删除成功', {
                'scenario_id': scenario_id
            })

            return True
        except Exception as e:
            debug_logger.log_error('DirectorMode', f'删除场景失败: {str(e)}', e)
            return False

    def log_scenario_action(self, scenario_id: str, timeline_id: str, action: str, details: str = ""):
        """
        记录场景执行日志

        Args:
            scenario_id: 场景ID
            timeline_id: 时间线ID
            action: 动作类型
            details: 详细信息
        """
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT INTO director_scenario_logs
                (scenario_id, timeline_id, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (scenario_id, timeline_id, action, details, datetime.now().isoformat()))

    # ==================== 时间线控制方法 ====================

    def start_timeline(self, timeline_id: str) -> bool:
        """
        启动时间线

        Args:
            timeline_id: 时间线ID

        Returns:
            是否成功启动
        """
        debug_logger.log_module('DirectorMode', '启动时间线', {'timeline_id': timeline_id})

        # 获取时间线
        timeline = self.get_timeline(timeline_id)
        if not timeline:
            debug_logger.log_error('DirectorMode', '时间线不存在')
            return False

        if len(timeline.scenarios) == 0:
            debug_logger.log_error('DirectorMode', '时间线没有场景')
            return False

        # 停止当前正在运行的时间线
        if self._active_timeline:
            self.stop_timeline()

        # 设置时间线为激活状态
        timeline.is_active = True
        timeline.is_paused = False
        timeline.start_time = datetime.now().isoformat()
        timeline.current_scenario_index = -1
        timeline.elapsed_time = 0

        # 重置所有场景状态
        for scenario in timeline.scenarios:
            scenario.status = ScenarioStatus.PENDING

        self.update_timeline(timeline)

        # 设置为活动时间线
        self._active_timeline = timeline

        # 启动执行线程
        self._stop_event.clear()
        self._executor_thread = threading.Thread(target=self._timeline_executor, daemon=True)
        self._executor_thread.start()

        self.emit_narration(f"时间线「{timeline.name}」开始执行")

        debug_logger.log_info('DirectorMode', '时间线启动成功', {
            'timeline_id': timeline_id,
            'scenario_count': len(timeline.scenarios)
        })

        return True

    def pause_timeline(self) -> bool:
        """
        暂停当前时间线

        Returns:
            是否成功暂停
        """
        if not self._active_timeline:
            return False

        self._active_timeline.is_paused = True
        self.update_timeline(self._active_timeline)

        self.emit_narration(f"时间线「{self._active_timeline.name}」已暂停")

        debug_logger.log_info('DirectorMode', '时间线暂停', {
            'timeline_id': self._active_timeline.timeline_id
        })

        return True

    def resume_timeline(self) -> bool:
        """
        恢复当前时间线

        Returns:
            是否成功恢复
        """
        if not self._active_timeline:
            return False

        self._active_timeline.is_paused = False
        self.update_timeline(self._active_timeline)

        self.emit_narration(f"时间线「{self._active_timeline.name}」已恢复")

        debug_logger.log_info('DirectorMode', '时间线恢复', {
            'timeline_id': self._active_timeline.timeline_id
        })

        return True

    def stop_timeline(self) -> bool:
        """
        停止当前时间线

        Returns:
            是否成功停止
        """
        if not self._active_timeline:
            return False

        # 停止执行线程（使用较短的超时时间以提高响应速度）
        self._stop_event.set()
        if self._executor_thread:
            self._executor_thread.join(timeout=2)
            self._executor_thread = None

        # 更新时间线状态
        self._active_timeline.is_active = False
        self._active_timeline.is_paused = False
        self.update_timeline(self._active_timeline)

        self.emit_narration(f"时间线「{self._active_timeline.name}」已停止")

        debug_logger.log_info('DirectorMode', '时间线停止', {
            'timeline_id': self._active_timeline.timeline_id
        })

        self._active_timeline = None

        return True

    def skip_to_scenario(self, scenario_id: str) -> bool:
        """
        跳转到指定场景

        Args:
            scenario_id: 场景ID

        Returns:
            是否成功跳转
        """
        if not self._active_timeline:
            return False

        for i, scenario in enumerate(self._active_timeline.scenarios):
            if scenario.scenario_id == scenario_id:
                # 将之前的场景标记为跳过
                for j in range(self._active_timeline.current_scenario_index + 1, i):
                    self._active_timeline.scenarios[j].status = ScenarioStatus.SKIPPED

                self._active_timeline.current_scenario_index = i - 1  # 执行器会自动+1
                self.update_timeline(self._active_timeline)

                self.emit_narration(f"跳转到场景「{scenario.name}」")

                return True

        return False

    def advance_to_next_scenario(self) -> bool:
        """
        手动推进到下一个场景

        Returns:
            是否成功推进
        """
        if not self._active_timeline:
            return False

        current = self._active_timeline.get_current_scenario()
        if current:
            current.status = ScenarioStatus.COMPLETED
            self.update_scenario(current, self._active_timeline.timeline_id)

        next_scenario = self._active_timeline.get_next_scenario()
        if next_scenario:
            self._active_timeline.current_scenario_index += 1
            self.update_timeline(self._active_timeline)
            self._trigger_scenario(next_scenario)
            return True

        return False

    def _timeline_executor(self):
        """
        时间线执行线程
        负责按时间触发场景
        """
        debug_logger.log_info('DirectorMode', '时间线执行器启动')

        last_check_time = time_module.time()

        while not self._stop_event.is_set():
            # 检查间隔1秒
            time_module.sleep(1)

            if not self._active_timeline or self._active_timeline.is_paused:
                continue

            # 更新已经过时间
            current_time = time_module.time()
            elapsed = current_time - last_check_time
            last_check_time = current_time

            self._active_timeline.elapsed_time += int(elapsed)

            # 检查是否有场景需要触发
            for i, scenario in enumerate(self._active_timeline.scenarios):
                if scenario.status != ScenarioStatus.PENDING:
                    continue

                should_trigger = False

                # 检查触发条件
                if scenario.trigger_type == TriggerType.TIME:
                    if self._active_timeline.elapsed_time >= scenario.trigger_time:
                        should_trigger = True

                elif scenario.trigger_type == TriggerType.SEQUENCE:
                    # 顺序触发：检查前一个场景是否完成
                    if i > 0:
                        prev_scenario = self._active_timeline.scenarios[i - 1]
                        if prev_scenario.status == ScenarioStatus.COMPLETED:
                            should_trigger = True
                    else:
                        # 第一个场景直接触发
                        should_trigger = True

                if should_trigger:
                    self._active_timeline.current_scenario_index = i
                    self._trigger_scenario(scenario)
                    break  # 一次只触发一个场景

            # 检查是否所有场景都已完成
            all_completed = all(
                s.status in [ScenarioStatus.COMPLETED, ScenarioStatus.SKIPPED]
                for s in self._active_timeline.scenarios
            )

            if all_completed:
                self.emit_narration(f"时间线「{self._active_timeline.name}」执行完成")
                self.stop_timeline()
                break

        debug_logger.log_info('DirectorMode', '时间线执行器停止')

    def _trigger_scenario(self, scenario: Scenario):
        """
        触发场景

        Args:
            scenario: 要触发的场景
        """
        debug_logger.log_module('DirectorMode', '触发场景', {
            'scenario_id': scenario.scenario_id,
            'name': scenario.name
        })

        scenario.status = ScenarioStatus.ACTIVE

        # 记录日志
        if self._active_timeline:
            self.log_scenario_action(
                scenario.scenario_id,
                self._active_timeline.timeline_id,
                'trigger',
                f'场景「{scenario.name}」被触发'
            )

        self.emit_narration(f"场景「{scenario.name}」: {scenario.description}")

        # 调用回调函数
        if self.scenario_callback:
            try:
                self.scenario_callback(scenario, self)
            except Exception as e:
                debug_logger.log_error('DirectorMode', f'场景回调执行失败: {str(e)}', e)

        # 如果设置了持续时间，启动定时器自动完成
        if scenario.duration > 0 and scenario.auto_advance:
            def auto_complete():
                time_module.sleep(scenario.duration)
                if scenario.status == ScenarioStatus.ACTIVE:
                    self._complete_scenario(scenario)

            threading.Thread(target=auto_complete, daemon=True).start()
        elif scenario.auto_advance and scenario.duration == 0:
            # 立即完成
            self._complete_scenario(scenario)

    def _complete_scenario(self, scenario: Scenario):
        """
        完成场景

        Args:
            scenario: 要完成的场景
        """
        scenario.status = ScenarioStatus.COMPLETED

        if self._active_timeline:
            self.update_scenario(scenario, self._active_timeline.timeline_id)
            self.log_scenario_action(
                scenario.scenario_id,
                self._active_timeline.timeline_id,
                'complete',
                f'场景「{scenario.name}」已完成'
            )

        debug_logger.log_info('DirectorMode', '场景完成', {
            'scenario_id': scenario.scenario_id,
            'name': scenario.name
        })

    def complete_current_scenario(self) -> bool:
        """
        手动完成当前场景

        Returns:
            是否成功完成
        """
        if not self._active_timeline:
            return False

        current = self._active_timeline.get_current_scenario()
        if current and current.status == ScenarioStatus.ACTIVE:
            self._complete_scenario(current)
            return True

        return False

    # ==================== 状态查询方法 ====================

    def get_active_timeline(self) -> Optional[Timeline]:
        """
        获取当前活动的时间线

        Returns:
            活动的时间线对象或None
        """
        return self._active_timeline

    def is_running(self) -> bool:
        """
        检查是否有时间线正在运行

        Returns:
            是否有时间线正在运行
        """
        return self._active_timeline is not None and self._active_timeline.is_active

    def is_paused(self) -> bool:
        """
        检查时间线是否暂停

        Returns:
            是否暂停
        """
        return self._active_timeline is not None and self._active_timeline.is_paused

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取导演模式统计信息

        Returns:
            统计信息字典
        """
        with self.db.get_connection() as conn:
            # 时间线数量
            cursor = conn.execute('SELECT COUNT(*) FROM director_timelines')
            timeline_count = cursor.fetchone()[0]

            # 场景数量
            cursor = conn.execute('SELECT COUNT(*) FROM director_scenarios')
            scenario_count = cursor.fetchone()[0]

            # 活动时间线
            active_timeline_id = None
            active_timeline_name = None
            current_scenario_name = None

            if self._active_timeline:
                active_timeline_id = self._active_timeline.timeline_id
                active_timeline_name = self._active_timeline.name
                current = self._active_timeline.get_current_scenario()
                if current:
                    current_scenario_name = current.name

        return {
            'total_timelines': timeline_count,
            'total_scenarios': scenario_count,
            'is_running': self.is_running(),
            'is_paused': self.is_paused(),
            'active_timeline_id': active_timeline_id,
            'active_timeline_name': active_timeline_name,
            'current_scenario': current_scenario_name,
            'elapsed_time': self._active_timeline.elapsed_time if self._active_timeline else 0
        }

    # ==================== 预设模板方法 ====================

    def create_sample_timeline(self) -> Timeline:
        """
        创建示例时间线

        Returns:
            创建的时间线对象
        """
        debug_logger.log_module('DirectorMode', '创建示例时间线')

        # 创建时间线
        timeline = self.create_timeline(
            name="示例：一天的开始",
            description="这是一个示例时间线，演示智能体一天生活的开始场景",
            metadata={'template': 'daily_start'}
        )

        # 添加场景
        self.add_scenario_to_timeline(
            timeline_id=timeline.timeline_id,
            name="早晨醒来",
            description="阳光透过窗帘照进房间，新的一天开始了",
            scenario_type=ScenarioType.ENVIRONMENT,
            trigger_type=TriggerType.TIME,
            trigger_time=0,
            content={
                'time_of_day': '早晨',
                'mood': '舒适',
                'environment_hints': ['阳光', '窗帘', '床铺']
            },
            duration=10,
            auto_advance=True
        )

        self.add_scenario_to_timeline(
            timeline_id=timeline.timeline_id,
            name="日常问候",
            description="用户可能会和智能体打招呼",
            scenario_type=ScenarioType.DIALOGUE,
            trigger_type=TriggerType.SEQUENCE,
            content={
                'dialogue_hints': ['早安', '你睡得好吗', '今天有什么计划'],
                'expected_response_style': '友好、亲切'
            },
            duration=30,
            auto_advance=False
        )

        self.add_scenario_to_timeline(
            timeline_id=timeline.timeline_id,
            name="情绪变化",
            description="智能体表现出期待新一天的积极情绪",
            scenario_type=ScenarioType.EMOTION,
            trigger_type=TriggerType.SEQUENCE,
            content={
                'emotion': 'happy',
                'intensity': 0.7,
                'reason': '新的一天充满希望'
            },
            duration=5,
            auto_advance=True
        )

        debug_logger.log_info('DirectorMode', '示例时间线创建成功', {
            'timeline_id': timeline.timeline_id
        })

        return timeline
