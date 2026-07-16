"""
Database service module.
数据库服务模块 - 包装 DatabaseManager，为 Web 后端提供安全的表查询/删除/统计入口。

Stage A.3: 提供业务表的只读查询 + 基于 uuid 的受控删除。

设计要点：
1. 白名单：只允许访问预定义的业务表（防御任意 SQL 拼接）
2. 懒加载 DatabaseManager：避免 Web 启动时强制 init DB
3. try/except 保护：单表/单行失败不影响其他调用
4. 全局单例：database_service = DatabaseService()
"""

from __future__ import annotations

import json
import os
import sys
import uuid as _uuid
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# 业务表白名单：仅允许查询/删除这些表
ALLOWED_TABLES: frozenset = frozenset({
    'entities',
    'entity_definitions',
    'entity_related_info',
    'short_term_memory',
    'long_term_memory',
    'emotion_history',
    'metadata',
    'environment_descriptions',
    'environment_objects',
    'agent_expressions',
    'user_expression_habits',
    'life_state_daily',
    'dream_records',
    'diary_entries',
    'open_loops',
    'creative_projects',
    'creative_story_bibles',
    'creative_memory_pool',
    'schedules',
    'schedule_entries',
    'schedule_confirmations',
    'vision_tool_logs',
    'events',
})


class DatabaseService:
    """
    数据库服务（Web 后端侧）

    Attributes:
        db_path: SQLite 数据库文件路径（可通过 env CHAT_AGENT_DB 覆盖）
        _db: 懒加载的 DatabaseManager 实例
    """

    DEFAULT_DB_ENV = 'CHAT_AGENT_DB'
    DEFAULT_DB_NAME = 'chat_agent.db'

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        初始化 DatabaseService。

        Args:
            db_path: 可选；为 None 时取 os.getenv('CHAT_AGENT_DB', 'chat_agent.db')
        """
        if db_path is None:
            db_path = os.getenv(self.DEFAULT_DB_ENV, self.DEFAULT_DB_NAME)
        self.db_path: str = db_path
        self._db: Optional[Any] = None

    # ------------------------------------------------------------------
    # 内部：懒加载 DatabaseManager
    # ------------------------------------------------------------------
    def _try_init_db(self) -> Optional[Any]:
        """
        尝试实例化 DatabaseManager，失败时记录 warning 并返回 None。
        """
        if self._db is not None:
            return self._db
        try:
            from src.core.database_manager import DatabaseManager  # type: ignore
            self._db = DatabaseManager(db_path=self.db_path)
            return self._db
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] DatabaseManager 初始化失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            self._db = None
            return None

    # ------------------------------------------------------------------
    # DatabaseManager 句柄
    # ------------------------------------------------------------------
    def get_db(self) -> Any:
        """
        懒加载 DatabaseManager；首次获取时会自动 init database。
        首次获取时尝试执行 PRAGMA journal_mode=WAL（防御性）。

        Returns:
            DatabaseManager 实例；不可用时返回 None。
        """
        db = self._try_init_db()
        if db is None:
            return None
        # 防御性：确保 WAL 模式被启用
        try:
            with db.get_connection() as conn:
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    # 不影响主流程
                    pass
        except Exception:
            # 拿不到连接也不抛出
            pass
        return db

    def _validate_table(self, table: str) -> str:
        """
        验证表名是否在白名单中。
        不在白名单 → raise ValueError。
        """
        if not table or not isinstance(table, str):
            raise ValueError(f"Table {table!r} not allowed")
        if table not in ALLOWED_TABLES:
            raise ValueError(f"Table {table} not allowed")
        return table

    # ------------------------------------------------------------------
    # 表查询
    # ------------------------------------------------------------------
    def get_tables(self) -> List[str]:
        """
        返回白名单中实际存在的业务表（sqlite_master 查询）。
        """
        db = self.get_db()
        if db is None:
            return []

        whitelist = sorted(ALLOWED_TABLES)
        existing: List[str] = []
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                # 限定为白名单表名，避免无关系统表
                placeholders = ','.join('?' for _ in whitelist)
                try:
                    cur.execute(
                        f"SELECT name FROM sqlite_master "
                        f"WHERE type='table' AND name IN ({placeholders})",
                        whitelist,
                    )
                except Exception:
                    # 极端情况：sqlite_master 不可用
                    return whitelist
                rows = cur.fetchall() or []
            for row in rows:
                try:
                    name = row['name'] if isinstance(row, dict) else row[0]
                except (KeyError, IndexError, TypeError):
                    continue
                if name:
                    existing.append(str(name))
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] get_tables 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return whitelist  # 兜底：返回白名单

        return sorted(existing)

    def query_table(
        self,
        table: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        查询表数据。
        表名必须在白名单中；limit/offset 做基本边界检查。
        """
        safe_table = self._validate_table(table)
        # 边界保护
        try:
            limit = max(1, min(int(limit), 1000))
        except (TypeError, ValueError):
            limit = 100
        try:
            offset = max(0, int(offset))
        except (TypeError, ValueError):
            offset = 0

        db = self.get_db()
        if db is None:
            return []

        rows: List[Dict[str, Any]] = []
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM {safe_table} LIMIT ? OFFSET ?",
                    (limit, offset),
                )
                fetched = cur.fetchall() or []
            for row in fetched:
                try:
                    if isinstance(row, dict):
                        rows.append(dict(row))
                    else:
                        rows.append({k: row[k] for k in row.keys()})
                except Exception:
                    # 单行转换失败：尝试 raw 转换
                    try:
                        rows.append(dict(row))
                    except Exception:
                        continue
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] query_table({safe_table}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return []
        return rows

    def delete_record(self, table: str, uuid: str) -> bool:
        """
        按 uuid 删除单条记录。
        表名必须在白名单中；uuid 必须是非空字符串。
        成功删除一条返回 True；否则 False。
        """
        safe_table = self._validate_table(table)
        if not uuid or not isinstance(uuid, str):
            return False

        db = self.get_db()
        if db is None:
            return False

        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"DELETE FROM {safe_table} WHERE uuid = ?",
                    (uuid,),
                )
                affected = cur.rowcount
            return bool(affected and affected > 0)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] delete_record({safe_table}, uuid) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

    # ------------------------------------------------------------------
    # Schedule CRUD（Stage C.2）
    # ------------------------------------------------------------------
    # 实际写入的表（schedule_* 白名单中的第一张能匹配上的；当前后端未在
    # init_database 中创建 schedule_* 表，方法会先检查存在性，缺失时
    # 返回友好错误或空列表，绝不抛 5xx。
    _SCHEDULE_PRIMARY_TABLE = 'schedules'
    _SCHEDULE_ALLOWED_FIELDS = frozenset({
        'title', 'description', 'start_time', 'end_time',
        'priority', 'status', 'schedule_type',
        'is_collaborative', 'collaborator_name', 'collaborator_status',
        'confirmed', 'created_at', 'updated_at',
    })

    def _ensure_schedule_table(self) -> Optional[str]:
        """
        返回当前可用的 schedule 主表名；若 schedule_* 都不存在则返回 None。
        """
        try:
            existing = set(self.get_tables() or [])
        except Exception:
            existing = set()
        for cand in (self._SCHEDULE_PRIMARY_TABLE, 'schedule_entries'):
            if cand in existing:
                return cand
        return None

    def get_schedule_by_date(self, date: str) -> List[Dict[str, Any]]:
        """
        按日期（YYYY-MM-DD）返回日程列表。
        缺失表 → 返回 []；绝不抛 5xx。
        """
        try:
            table = self._ensure_schedule_table()
            if table is None:
                return []
            db = self.get_db()
            if db is None:
                return []
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM {table} "
                    f"WHERE substr(COALESCE(start_time,''),1,10) = ? "
                    f"ORDER BY start_time ASC",
                    (date,),
                )
                rows = cur.fetchall() or []
            out: List[Dict[str, Any]] = []
            for r in rows:
                try:
                    out.append(dict(r) if not isinstance(r, dict) else dict(r))
                except Exception:
                    continue
            return out
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] get_schedule_by_date({date}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return []

    def get_schedule_by_range(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """
        按日期范围 [from_date, to_date] 返回日程列表。
        缺失表 → 返回 []；绝不抛 5xx。
        """
        try:
            table = self._ensure_schedule_table()
            if table is None:
                return []
            db = self.get_db()
            if db is None:
                return []
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM {table} "
                    f"WHERE substr(COALESCE(start_time,''),1,10) >= ? "
                    f"AND substr(COALESCE(start_time,''),1,10) <= ? "
                    f"ORDER BY start_time ASC",
                    (from_date, to_date),
                )
                rows = cur.fetchall() or []
            out: List[Dict[str, Any]] = []
            for r in rows:
                try:
                    out.append(dict(r) if not isinstance(r, dict) else dict(r))
                except Exception:
                    continue
            return out
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] get_schedule_by_range({from_date},{to_date}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return []

    def add_schedule_item(self, item: Dict[str, Any]) -> int:
        """
        插入一条日程记录。
        返回新记录 id（int）；失败时返回 0。
        缺失 schedule_* 表 → 返回 0（不会抛 5xx）。
        """
        try:
            table = self._ensure_schedule_table()
            if table is None:
                return 0
            db = self.get_db()
            if db is None:
                return 0
            safe = {k: v for k, v in (item or {}).items()
                    if k in self._SCHEDULE_ALLOWED_FIELDS}
            if not safe:
                return 0
            cols = list(safe.keys())
            placeholders = ','.join('?' for _ in cols)
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"INSERT INTO {table} ({','.join(cols)}) "
                    f"VALUES ({placeholders})",
                    [safe[c] for c in cols],
                )
                new_id = cur.lastrowid or 0
            return int(new_id) if new_id else 0
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] add_schedule_item 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return 0

    def update_schedule_item(self, item_id: int, updates: Dict[str, Any]) -> bool:
        """
        按 id 更新日程；缺失表 / 不存在 → 返回 False，绝不抛 5xx。
        """
        try:
            table = self._ensure_schedule_table()
            if table is None:
                return False
            safe = {k: v for k, v in (updates or {}).items()
                    if k in self._SCHEDULE_ALLOWED_FIELDS and v is not None}
            if not safe:
                return False
            set_clause = ", ".join(f"{k} = ?" for k in safe.keys())
            db = self.get_db()
            if db is None:
                return False
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"UPDATE {table} SET {set_clause} WHERE id = ?",
                    [*safe.values(), int(item_id)],
                )
                return (cur.rowcount or 0) > 0
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] update_schedule_item({item_id}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

    def delete_schedule_item(self, item_id: int) -> bool:
        """
        按 id 删除日程；缺失表 / 不存在 → 返回 False，绝不抛 5xx。
        """
        try:
            table = self._ensure_schedule_table()
            if table is None:
                return False
            db = self.get_db()
            if db is None:
                return False
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"DELETE FROM {table} WHERE id = ?",
                    (int(item_id),),
                )
                return (cur.rowcount or 0) > 0
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] delete_schedule_item({item_id}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

    def confirm_schedule_item(self, item_id: int, confirmed: bool) -> bool:
        """
        协作日程确认/取消确认：写入 confirmed 字段并把 status 同步。
        缺失表 / 不存在 → 返回 False，绝不抛 5xx。
        """
        try:
            table = self._ensure_schedule_table()
            if table is None:
                return False
            db = self.get_db()
            if db is None:
                return False
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"UPDATE {table} "
                    f"SET confirmed = ?, status = ?, updated_at = ? "
                    f"WHERE id = ?",
                    (
                        1 if confirmed else 0,
                        'confirmed' if confirmed else 'pending',
                        datetime.now().isoformat(),
                        int(item_id),
                    ),
                )
                return (cur.rowcount or 0) > 0
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] confirm_schedule_item({item_id}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

    # ------------------------------------------------------------------
    # Creative Project CRUD（Stage C.6）
    # ------------------------------------------------------------------
    # 长期创作项目的最小可用接口。所有方法都走 try/except 保护：
    # - 缺失表 / DB 不可用 → 返回空值 / False，不抛 5xx
    # - 单行转换失败：跳过该行，不影响整体

    _CREATIVE_PRIMARY_TABLE = 'creative_projects'
    _CREATIVE_BIBLE_TABLE = 'creative_story_bibles'
    _CREATIVE_POOL_TABLE = 'creative_memory_pool'

    def _ensure_creative_table(self) -> Optional[str]:
        """
        返回当前可用的 creative_projects 表名；不存在则返回 None。
        """
        try:
            existing = set(self.get_tables() or [])
        except Exception:
            existing = set()
        if self._CREATIVE_PRIMARY_TABLE in existing:
            return self._CREATIVE_PRIMARY_TABLE
        return None

    def list_creative_projects(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        列出 creative_projects 记录（按 status 过滤可选）。
        - 表缺失 / DB 不可用 → 返回 []
        - status 留空：列出全部
        - limit 做 1..200 边界保护
        """
        try:
            table = self._ensure_creative_table()
            if table is None:
                return []
            db = self.get_db()
            if db is None:
                return []
            try:
                bounded_limit = max(1, min(int(limit), 200))
            except (TypeError, ValueError):
                bounded_limit = 50

            with db.get_connection() as conn:
                cur = conn.cursor()
                if status:
                    cur.execute(
                        f"SELECT * FROM {table} "
                        f"WHERE status = ? "
                        f"ORDER BY created_at DESC LIMIT ?",
                        (str(status), int(bounded_limit)),
                    )
                else:
                    cur.execute(
                        f"SELECT * FROM {table} "
                        f"ORDER BY created_at DESC LIMIT ?",
                        (int(bounded_limit),),
                    )
                rows = cur.fetchall() or []
            out: List[Dict[str, Any]] = []
            for r in rows:
                try:
                    out.append(dict(r) if not isinstance(r, dict) else dict(r))
                except Exception:
                    continue
            return out
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] list_creative_projects 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return []

    def get_creative_project(self, project_uuid: str) -> Optional[Dict[str, Any]]:
        """
        按 uuid 读取单个 creative_projects 记录。
        失败 / 不存在 → 返回 None。
        """
        try:
            if not project_uuid or not isinstance(project_uuid, str):
                return None
            table = self._ensure_creative_table()
            if table is None:
                return None
            db = self.get_db()
            if db is None:
                return None
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM {table} WHERE uuid = ?",
                    (project_uuid,),
                )
                row = cur.fetchone()
            if not row:
                return None
            try:
                return dict(row) if not isinstance(row, dict) else dict(row)
            except Exception:
                return None
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] get_creative_project({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    def create_creative_project(self, project: Dict[str, Any]) -> Optional[str]:
        """
        插入一条 creative_projects 记录；返回新 uuid；失败返回 None。
        - 缺字段会用数据库默认值兜底
        - project['uuid'] 缺省时自动生成
        """
        try:
            table = self._ensure_creative_table()
            if table is None:
                return None
            db = self.get_db()
            if db is None:
                return None

            new_uuid = (project or {}).get('uuid') or str(_uuid.uuid4())
            now_iso = datetime.now().isoformat()
            payload = {
                'uuid': new_uuid,
                'title': (project or {}).get('title') or '未命名',
                'work_type': (project or {}).get('work_type') or '短篇',
                'premise': (project or {}).get('premise', ''),
                'tone': (project or {}).get('tone', ''),
                'point_of_view': (project or {}).get('point_of_view', '第一人称'),
                'target_chars': int((project or {}).get('target_chars', 5000) or 5000),
                'current_chars': int((project or {}).get('current_chars', 0) or 0),
                'status': (project or {}).get('status') or 'drafting',
                'inspiration_source': (project or {}).get('inspiration_source', ''),
                'outline_json': json.dumps((project or {}).get('outline') or [],
                                          ensure_ascii=False),
                'characters_json': json.dumps((project or {}).get('characters') or [],
                                              ensure_ascii=False),
                'draft_chunks_json': json.dumps((project or {}).get('draft_chunks') or [],
                                                ensure_ascii=False),
                'next_advance_at': (project or {}).get('next_advance_at'),
                'last_advanced_at': (project or {}).get('last_advanced_at'),
                'created_at': (project or {}).get('created_at') or now_iso,
                'updated_at': (project or {}).get('updated_at') or now_iso,
            }
            cols = list(payload.keys())
            placeholders = ','.join('?' for _ in cols)
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"INSERT INTO {table} ({','.join(cols)}) "
                    f"VALUES ({placeholders})",
                    [payload[c] for c in cols],
                )
            return new_uuid
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] create_creative_project 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    def update_creative_project(self, project_uuid: str,
                                updates: Dict[str, Any]) -> bool:
        """
        按 uuid 更新 creative_projects 字段；行不存在 / 失败 → 返回 False。
        updates 仅接受安全字段（title / status / current_chars / target_chars /
        next_advance_at / last_advanced_at / premise / tone / point_of_view /
        work_type / inspiration_source / outline / characters / draft_chunks）。
        """
        try:
            if not project_uuid or not isinstance(project_uuid, str):
                return False
            table = self._ensure_creative_table()
            if table is None:
                return False
            safe_scalar = {
                'title', 'work_type', 'premise', 'tone', 'point_of_view',
                'target_chars', 'current_chars', 'status',
                'inspiration_source', 'next_advance_at', 'last_advanced_at',
            }
            safe_json = {
                'outline': 'outline_json',
                'characters': 'characters_json',
                'draft_chunks': 'draft_chunks_json',
            }
            sets: List[str] = []
            values: List[Any] = []
            for k, v in (updates or {}).items():
                if k in safe_scalar:
                    sets.append(f"{k} = ?")
                    values.append(v)
                elif k in safe_json:
                    sets.append(f"{safe_json[k]} = ?")
                    try:
                        values.append(json.dumps(v, ensure_ascii=False))
                    except Exception:
                        values.append(json.dumps([], ensure_ascii=False))
            if not sets:
                return False
            sets.append('updated_at = ?')
            values.append(datetime.now().isoformat())
            values.append(project_uuid)
            db = self.get_db()
            if db is None:
                return False
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"UPDATE {table} SET {', '.join(sets)} WHERE uuid = ?",
                    values,
                )
                return (cur.rowcount or 0) > 0
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] update_creative_project({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

    def get_story_bible(self, project_uuid: str) -> Optional[Dict[str, Any]]:
        """
        读取 project_uuid 对应的 Story Bible（含 JSON 字段反序列化）。
        缺失 / 失败 → 返回 None。
        """
        try:
            if not project_uuid or not isinstance(project_uuid, str):
                return None
            db = self.get_db()
            if db is None:
                return None
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM {self._CREATIVE_BIBLE_TABLE} "
                    f"WHERE project_uuid = ?",
                    (project_uuid,),
                )
                row = cur.fetchone()
            if not row:
                return None
            data: Dict[str, Any]
            try:
                data = dict(row) if not isinstance(row, dict) else dict(row)
            except Exception:
                return None
            for json_k in (
                'active_themes_json', 'unresolved_threads_json',
                'resolved_threads_json', 'important_facts_json',
                'recent_keywords_json',
            ):
                try:
                    data[json_k.replace('_json', '')] = json.loads(
                        data.get(json_k) or '[]'
                    )
                except Exception:
                    data[json_k.replace('_json', '')] = []
            return data
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] get_story_bible({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    def upsert_story_bible(self, project_uuid: str,
                            bible: Dict[str, Any]) -> bool:
        """
        插入/替换 Story Bible；失败 → 返回 False。
        """
        try:
            if not project_uuid or not isinstance(project_uuid, str):
                return False
            db = self.get_db()
            if db is None:
                return False
            now_iso = datetime.now().isoformat()
            payload = {
                'project_uuid': project_uuid,
                'mainline_direction': (bible or {}).get('mainline_direction', ''),
                'active_themes_json': json.dumps(
                    (bible or {}).get('active_themes') or [],
                    ensure_ascii=False),
                'unresolved_threads_json': json.dumps(
                    (bible or {}).get('unresolved_threads') or [],
                    ensure_ascii=False),
                'resolved_threads_json': json.dumps(
                    (bible or {}).get('resolved_threads') or [],
                    ensure_ascii=False),
                'important_facts_json': json.dumps(
                    (bible or {}).get('important_facts') or [],
                    ensure_ascii=False),
                'next_direction': (bible or {}).get('next_direction', ''),
                'recent_keywords_json': json.dumps(
                    (bible or {}).get('recent_keywords') or [],
                    ensure_ascii=False),
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            cols = list(payload.keys())
            placeholders = ','.join('?' for _ in cols)
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"INSERT OR REPLACE INTO {self._CREATIVE_BIBLE_TABLE} "
                    f"({','.join(cols)}) VALUES ({placeholders})",
                    [payload[c] for c in cols],
                )
            return True
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] upsert_story_bible({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False

    def get_creative_memory_pool(
        self,
        project_uuid: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        读取 project_uuid 对应的 creative_memory_pool 记录。
        缺失 / 失败 → 返回 []。
        """
        try:
            if not project_uuid or not isinstance(project_uuid, str):
                return []
            db = self.get_db()
            if db is None:
                return []
            try:
                bounded_limit = max(1, min(int(limit), 200))
            except (TypeError, ValueError):
                bounded_limit = 50
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT * FROM {self._CREATIVE_POOL_TABLE} "
                    f"WHERE project_uuid = ? "
                    f"ORDER BY importance DESC, created_at DESC "
                    f"LIMIT ?",
                    (project_uuid, int(bounded_limit)),
                )
                rows = cur.fetchall() or []
            out: List[Dict[str, Any]] = []
            for r in rows:
                try:
                    out.append(dict(r) if not isinstance(r, dict) else dict(r))
                except Exception:
                    continue
            return out
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[DatabaseService] get_creative_memory_pool({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return []

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------
    def get_stats(self) -> Dict[str, Any]:
        """
        返回 db_path / tables_count / db_size_bytes 等只读统计信息。
        """
        stats: Dict[str, Any] = {
            'db_path': self.db_path,
            'tables_count': 0,
            'db_size_bytes': 0,
        }
        # tables count
        try:
            stats['tables_count'] = len(self.get_tables())
        except Exception:
            stats['tables_count'] = 0
        # db file size
        try:
            if self.db_path and os.path.exists(self.db_path):
                stats['db_size_bytes'] = int(os.path.getsize(self.db_path))
        except Exception:
            stats['db_size_bytes'] = 0
        return stats


# 全局单例
database_service = DatabaseService()


__all__ = [
    "DatabaseService",
    "database_service",
    "ALLOWED_TABLES",
]
