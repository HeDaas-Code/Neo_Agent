"""
计划管理模块
提供长期计划的创建、跟踪和管理功能
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class PlanStatus(Enum):
    """计划状态"""
    NOT_STARTED = "not_started"  # 未开始
    IN_PROGRESS = "in_progress"  # 进行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class TaskStatus(Enum):
    """任务状态"""
    TODO = "todo"  # 待办
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成


class Task:
    """任务条目"""

    def __init__(
        self,
        task_id: str = None,
        title: str = "",
        description: str = "",
        status: TaskStatus = TaskStatus.TODO,
        completed_at: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化任务

        Args:
            task_id: 任务ID
            title: 标题
            description: 描述
            status: 状态
            completed_at: 完成时间
            metadata: 附加元数据
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.status = status
        self.completed_at = completed_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """从字典创建任务"""
        completed_at = data.get('completed_at')
        return cls(
            task_id=data.get('task_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            status=TaskStatus(data.get('status', TaskStatus.TODO.value)),
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            metadata=data.get('metadata', {})
        )

    def mark_completed(self):
        """标记为已完成"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()


class Plan:
    """计划条目"""

    def __init__(
        self,
        plan_id: str = None,
        title: str = "",
        description: str = "",
        goal: str = "",
        start_date: datetime = None,
        target_date: datetime = None,
        status: PlanStatus = PlanStatus.NOT_STARTED,
        tasks: List[Task] = None,
        progress: float = 0.0,
        created_at: datetime = None,
        updated_at: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化计划

        Args:
            plan_id: 计划ID
            title: 标题
            description: 描述
            goal: 目标
            start_date: 开始日期
            target_date: 目标完成日期
            status: 状态
            tasks: 任务列表
            progress: 进度（0-1）
            created_at: 创建时间
            updated_at: 更新时间
            metadata: 附加元数据
        """
        self.plan_id = plan_id or str(uuid.uuid4())
        self.title = title
        self.description = description
        self.goal = goal
        self.start_date = start_date or datetime.now()
        self.target_date = target_date
        self.status = status
        self.tasks = tasks or []
        self.progress = progress
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'plan_id': self.plan_id,
            'title': self.title,
            'description': self.description,
            'goal': self.goal,
            'start_date': self.start_date.isoformat(),
            'target_date': self.target_date.isoformat() if self.target_date else None,
            'status': self.status.value,
            'tasks': [task.to_dict() for task in self.tasks],
            'progress': self.progress,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        """从字典创建计划"""
        target_date = data.get('target_date')
        return cls(
            plan_id=data.get('plan_id'),
            title=data.get('title', ''),
            description=data.get('description', ''),
            goal=data.get('goal', ''),
            start_date=datetime.fromisoformat(data.get('start_date', datetime.now().isoformat())),
            target_date=datetime.fromisoformat(target_date) if target_date else None,
            status=PlanStatus(data.get('status', PlanStatus.NOT_STARTED.value)),
            tasks=[Task.from_dict(t) for t in data.get('tasks', [])],
            progress=data.get('progress', 0.0),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )

    def add_task(self, task: Task):
        """添加任务"""
        self.tasks.append(task)
        self.update_progress()

    def remove_task(self, task_id: str):
        """移除任务"""
        self.tasks = [t for t in self.tasks if t.task_id != task_id]
        self.update_progress()

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None

    def update_progress(self):
        """更新进度"""
        if not self.tasks:
            self.progress = 0.0
            return

        completed = len([t for t in self.tasks if t.status == TaskStatus.COMPLETED])
        self.progress = completed / len(self.tasks)
        self.updated_at = datetime.now()

        # 如果所有任务完成，更新计划状态
        if self.progress >= 1.0 and self.status != PlanStatus.COMPLETED:
            self.status = PlanStatus.COMPLETED


class PlanManager:
    """
    计划管理器
    负责计划的创建、查询、更新和删除
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化计划管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager or DatabaseManager()
        self._init_database()

        debug_logger.log_info('PlanManager', '初始化计划管理器')

    def _init_database(self):
        """初始化数据库表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS plans (
            plan_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            goal TEXT,
            start_date TEXT,
            target_date TEXT,
            status TEXT,
            tasks TEXT,
            progress REAL,
            created_at TEXT,
            updated_at TEXT,
            metadata TEXT
        )
        """
        self.db_manager.execute_query(create_table_sql)
        debug_logger.log_info('PlanManager', '数据库表初始化完成')

    def add_plan(self, plan: Plan) -> bool:
        """
        添加计划

        Args:
            plan: 计划对象

        Returns:
            是否添加成功
        """
        try:
            insert_sql = """
            INSERT INTO plans 
            (plan_id, title, description, goal, start_date, target_date, status, 
             tasks, progress, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_query(
                insert_sql,
                (
                    plan.plan_id,
                    plan.title,
                    plan.description,
                    plan.goal,
                    plan.start_date.isoformat(),
                    plan.target_date.isoformat() if plan.target_date else None,
                    plan.status.value,
                    json.dumps([t.to_dict() for t in plan.tasks], ensure_ascii=False),
                    plan.progress,
                    plan.created_at.isoformat(),
                    plan.updated_at.isoformat(),
                    json.dumps(plan.metadata, ensure_ascii=False)
                )
            )

            debug_logger.log_info('PlanManager', '添加计划成功', {
                'plan_id': plan.plan_id,
                'title': plan.title
            })
            return True

        except Exception as e:
            debug_logger.log_error('PlanManager', '添加计划失败', e)
            return False

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """
        获取指定计划

        Args:
            plan_id: 计划ID

        Returns:
            计划对象或None
        """
        try:
            query_sql = "SELECT * FROM plans WHERE plan_id = ?"
            result = self.db_manager.fetch_one(query_sql, (plan_id,))

            if result:
                return self._row_to_plan(result)
            return None

        except Exception as e:
            debug_logger.log_error('PlanManager', '获取计划失败', e)
            return None

    def get_all_plans(self, status: PlanStatus = None) -> List[Plan]:
        """
        获取所有计划

        Args:
            status: 可选的状态筛选

        Returns:
            计划列表
        """
        try:
            if status:
                query_sql = "SELECT * FROM plans WHERE status = ? ORDER BY updated_at DESC"
                results = self.db_manager.fetch_all(query_sql, (status.value,))
            else:
                query_sql = "SELECT * FROM plans ORDER BY updated_at DESC"
                results = self.db_manager.fetch_all(query_sql)

            return [self._row_to_plan(row) for row in results]

        except Exception as e:
            debug_logger.log_error('PlanManager', '获取计划列表失败', e)
            return []

    def get_active_plans(self) -> List[Plan]:
        """获取活跃的计划（进行中或未开始）"""
        try:
            query_sql = """
            SELECT * FROM plans 
            WHERE status IN (?, ?)
            ORDER BY updated_at DESC
            """
            results = self.db_manager.fetch_all(
                query_sql,
                (PlanStatus.IN_PROGRESS.value, PlanStatus.NOT_STARTED.value)
            )

            return [self._row_to_plan(row) for row in results]

        except Exception as e:
            debug_logger.log_error('PlanManager', '获取活跃计划失败', e)
            return []

    def update_plan(self, plan: Plan) -> bool:
        """
        更新计划

        Args:
            plan: 计划对象

        Returns:
            是否更新成功
        """
        try:
            # 自动更新更新时间
            plan.updated_at = datetime.now()

            update_sql = """
            UPDATE plans 
            SET title = ?, description = ?, goal = ?, start_date = ?, target_date = ?,
                status = ?, tasks = ?, progress = ?, updated_at = ?, metadata = ?
            WHERE plan_id = ?
            """
            self.db_manager.execute_query(
                update_sql,
                (
                    plan.title,
                    plan.description,
                    plan.goal,
                    plan.start_date.isoformat(),
                    plan.target_date.isoformat() if plan.target_date else None,
                    plan.status.value,
                    json.dumps([t.to_dict() for t in plan.tasks], ensure_ascii=False),
                    plan.progress,
                    plan.updated_at.isoformat(),
                    json.dumps(plan.metadata, ensure_ascii=False),
                    plan.plan_id
                )
            )

            debug_logger.log_info('PlanManager', '更新计划成功', {
                'plan_id': plan.plan_id
            })
            return True

        except Exception as e:
            debug_logger.log_error('PlanManager', '更新计划失败', e)
            return False

    def delete_plan(self, plan_id: str) -> bool:
        """
        删除计划

        Args:
            plan_id: 计划ID

        Returns:
            是否删除成功
        """
        try:
            delete_sql = "DELETE FROM plans WHERE plan_id = ?"
            self.db_manager.execute_query(delete_sql, (plan_id,))

            debug_logger.log_info('PlanManager', '删除计划成功', {
                'plan_id': plan_id
            })
            return True

        except Exception as e:
            debug_logger.log_error('PlanManager', '删除计划失败', e)
            return False

    def _row_to_plan(self, row: tuple) -> Plan:
        """
        将数据库行转换为Plan对象

        Args:
            row: 数据库查询结果行

        Returns:
            Plan对象
        """
        tasks_data = json.loads(row[7]) if row[7] else []
        tasks = [Task.from_dict(t) for t in tasks_data]

        target_date = row[5]

        return Plan(
            plan_id=row[0],
            title=row[1],
            description=row[2],
            goal=row[3],
            start_date=datetime.fromisoformat(row[4]),
            target_date=datetime.fromisoformat(target_date) if target_date else None,
            status=PlanStatus(row[6]),
            tasks=tasks,
            progress=row[8],
            created_at=datetime.fromisoformat(row[9]),
            updated_at=datetime.fromisoformat(row[10]),
            metadata=json.loads(row[11]) if row[11] else {}
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取计划统计信息

        Returns:
            统计信息字典
        """
        all_plans = self.get_all_plans()

        stats = {
            'total': len(all_plans),
            'not_started': len([p for p in all_plans if p.status == PlanStatus.NOT_STARTED]),
            'in_progress': len([p for p in all_plans if p.status == PlanStatus.IN_PROGRESS]),
            'completed': len([p for p in all_plans if p.status == PlanStatus.COMPLETED]),
            'paused': len([p for p in all_plans if p.status == PlanStatus.PAUSED]),
            'average_progress': sum(p.progress for p in all_plans) / len(all_plans) if all_plans else 0,
            'total_tasks': sum(len(p.tasks) for p in all_plans),
            'completed_tasks': sum(
                len([t for t in p.tasks if t.status == TaskStatus.COMPLETED])
                for p in all_plans
            )
        }

        return stats
