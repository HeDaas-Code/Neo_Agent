"""
数据库管理模块
使用SQLite替代JSON文件存储，统一管理所有数据
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager

global INIT_Database_PreParation_Complete
INIT_Database_PreParation_Complete = False

class DatabaseManager:
    """
    数据库管理器
    管理所有数据表的创建、查询、更新和删除操作
    """

    def __init__(self, db_path: str = "chat_agent.db", debug: bool = False):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
            debug: 是否启用调试模式
        """
        self.db_path = db_path
        self.debug = debug
        self._query_count = 0  # 查询计数器
        self._operation_log = []  # 操作日志

        if self.debug:
            print(f"🐛 [DEBUG] 数据库管理器初始化 - 路径: {db_path}")

        self.init_database()

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器
        """
        if self.debug:
            print(f"🐛 [DEBUG] 打开数据库连接: {self.db_path}")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以像字典一样访问

        try:
            yield conn
            conn.commit()

            if self.debug:
                print(f"🐛 [DEBUG] 数据库事务提交成功")

        except Exception as e:
            conn.rollback()

            if self.debug:
                print(f"🐛 [DEBUG] 数据库事务回滚 - 错误: {e}")

            raise e
        finally:
            conn.close()

            if self.debug:
                print(f"🐛 [DEBUG] 数据库连接已关闭")

    def init_database(self):
        """
        初始化数据库，创建所有必要的表
        """
        global INIT_Database_PreParation_Complete
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. 基础知识表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS base_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_name TEXT UNIQUE NOT NULL,
                    normalized_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT '通用',
                    description TEXT,
                    immutable INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 100,
                    confidence REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            ''')

            # 2. 实体表（知识库主体）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    uuid TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 3. 实体定义表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entity_definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_uuid TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT DEFAULT '定义',
                    source TEXT,
                    confidence REAL DEFAULT 1.0,
                    priority INTEGER DEFAULT 50,
                    is_base_knowledge INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (entity_uuid) REFERENCES entities(uuid) ON DELETE CASCADE
                )
            ''')

            # 4. 实体相关信息表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entity_related_info (
                    uuid TEXT PRIMARY KEY,
                    entity_uuid TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT DEFAULT '其他',
                    source TEXT,
                    confidence REAL DEFAULT 0.7,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (entity_uuid) REFERENCES entities(uuid) ON DELETE CASCADE
                )
            ''')

            # 5. 短期记忆表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')

            # 6. 长期记忆概括表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    uuid TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    rounds INTEGER,
                    message_count INTEGER,
                    created_at TEXT NOT NULL,
                    ended_at TEXT NOT NULL
                )
            ''')

            # 7. 情感分析历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS emotion_history (
                    uuid TEXT PRIMARY KEY,
                    relationship_type TEXT,
                    emotional_tone TEXT,
                    overall_score INTEGER,
                    intimacy INTEGER,
                    trust INTEGER,
                    pleasure INTEGER,
                    resonance INTEGER,
                    dependence INTEGER,
                    analysis_summary TEXT,
                    created_at TEXT NOT NULL
                )
            ''')

            # 8. 元数据表（存储各种统计和配置信息）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 9. 环境描述表（用于智能体伪视觉）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS environment_descriptions (
                    uuid TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    overall_description TEXT NOT NULL,
                    atmosphere TEXT,
                    lighting TEXT,
                    sounds TEXT,
                    smells TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 10. 环境物体表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS environment_objects (
                    uuid TEXT PRIMARY KEY,
                    environment_uuid TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    position TEXT,
                    properties TEXT,
                    interaction_hints TEXT,
                    priority INTEGER DEFAULT 50,
                    is_visible INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (environment_uuid) REFERENCES environment_descriptions(uuid) ON DELETE CASCADE
                )
            ''')

            # 11. 视觉工具使用记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vision_tool_logs (
                    uuid TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    environment_uuid TEXT,
                    objects_viewed TEXT,
                    context_provided TEXT,
                    triggered_by TEXT DEFAULT 'auto',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (environment_uuid) REFERENCES environment_descriptions(uuid) ON DELETE SET NULL
                )
            ''')

            # 12. 环境连接关系表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS environment_connections (
                    uuid TEXT PRIMARY KEY,
                    from_environment_uuid TEXT NOT NULL,
                    to_environment_uuid TEXT NOT NULL,
                    connection_type TEXT DEFAULT 'normal',
                    direction TEXT DEFAULT 'bidirectional',
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (from_environment_uuid) REFERENCES environment_descriptions(uuid) ON DELETE CASCADE,
                    FOREIGN KEY (to_environment_uuid) REFERENCES environment_descriptions(uuid) ON DELETE CASCADE,
                    UNIQUE(from_environment_uuid, to_environment_uuid)
                )
            ''')

            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_entities_normalized ON entities(normalized_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_base_knowledge_normalized ON base_knowledge(normalized_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_short_term_timestamp ON short_term_memory(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_long_term_created ON long_term_memory(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_environment_active ON environment_descriptions(is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_objects_environment ON environment_objects(environment_uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vision_logs_created ON vision_tool_logs(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_connections_from ON environment_connections(from_environment_uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_connections_to ON environment_connections(to_environment_uuid)')

            conn.commit()
        if INIT_Database_PreParation_Complete == False:
            print("✓ 数据库初始化完成")
            INIT_Database_PreParation_Complete = True


    # ==================== 基础知识相关方法 ====================

    def add_base_fact(self, entity_name: str, content: str, category: str = "通用",
                      description: str = "", immutable: bool = True) -> bool:
        """
        添加基础事实

        Args:
            entity_name: 实体名称
            content: 事实内容
            category: 分类
            description: 描述
            immutable: 是否不可变

        Returns:
            是否添加成功
        """
        try:
            if self.debug:
                print(f"🐛 [DEBUG] 添加基础事实: {entity_name} | 分类: {category}")

            normalized_name = entity_name.strip().lower()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO base_knowledge 
                    (entity_name, normalized_name, content, category, description, immutable, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (entity_name, normalized_name, content, category, description,
                      1 if immutable else 0, datetime.now().isoformat()))

                if self.debug:
                    print(f"🐛 [DEBUG] ✓ 基础事实添加成功: {entity_name}")

                return True
        except sqlite3.IntegrityError:
            if self.debug:
                print(f"🐛 [DEBUG] ⚠ 基础事实已存在: {entity_name}")
            print(f"⚠ 基础事实已存在: {entity_name}")
            return False
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ 添加基础事实时出错: {e}")
            print(f"✗ 添加基础事实时出错: {e}")
            return False

    def get_base_fact(self, entity_name: str) -> Optional[Dict[str, Any]]:
        """
        获取基础事实

        Args:
            entity_name: 实体名称

        Returns:
            基础事实字典或None
        """
        normalized_name = entity_name.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM base_knowledge 
                WHERE normalized_name = ? OR entity_name = ?
            ''', (normalized_name, entity_name))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_base_facts(self) -> List[Dict[str, Any]]:
        """
        获取所有基础事实

        Returns:
            基础事实列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM base_knowledge ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def update_base_fact(self, entity_name: str, **kwargs) -> bool:
        """
        更新基础事实

        Args:
            entity_name: 实体名称
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        try:
            # 检查是否不可变
            existing = self.get_base_fact(entity_name)
            if existing and existing.get('immutable'):
                print(f"⚠ 该基础事实不可变: {entity_name}")
                return False

            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            set_clause += ", updated_at = ?"
            values = list(kwargs.values()) + [datetime.now().isoformat(), entity_name]

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE base_knowledge 
                    SET {set_clause}
                    WHERE entity_name = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新基础事实时出错: {e}")
            return False

    def delete_base_fact(self, entity_name: str) -> bool:
        """
        删除基础事实

        Args:
            entity_name: 实体名称

        Returns:
            是否删除成功
        """
        try:
            # 检查是否不可变
            existing = self.get_base_fact(entity_name)
            if existing and existing.get('immutable'):
                print(f"⚠ 该基础事实不可变，不能删除: {entity_name}")
                return False

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM base_knowledge WHERE entity_name = ?', (entity_name,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除基础事实时出错: {e}")
            return False

    # ==================== 实体相关方法 ====================

    def create_entity(self, name: str) -> str:
        """
        创建新实体

        Args:
            name: 实体名称

        Returns:
            实体UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 创建实体: {name}")

        normalized_name = name.strip().lower()
        entity_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO entities (uuid, name, normalized_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (entity_uuid, name, normalized_name, now, now))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 实体创建成功: {name} | UUID: {entity_uuid}")

        return entity_uuid

    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        通过名称获取实体

        Args:
            name: 实体名称

        Returns:
            实体字典或None
        """
        normalized_name = name.strip().lower()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entities WHERE normalized_name = ?', (normalized_name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_entity_by_uuid(self, entity_uuid: str) -> Optional[Dict[str, Any]]:
        """
        通过UUID获取实体

        Args:
            entity_uuid: 实体UUID

        Returns:
            实体字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entities WHERE uuid = ?', (entity_uuid,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_entities(self) -> List[Dict[str, Any]]:
        """
        获取所有实体

        Returns:
            实体列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entities ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def find_or_create_entity(self, name: str) -> str:
        """
        查找或创建实体

        Args:
            name: 实体名称

        Returns:
            实体UUID
        """
        entity = self.get_entity_by_name(name)
        if entity:
            return entity['uuid']
        return self.create_entity(name)

    # ==================== 实体定义相关方法 ====================

    def set_entity_definition(self, entity_uuid: str, content: str, type_: str = "定义",
                             source: str = "", confidence: float = 1.0, priority: int = 50,
                             is_base_knowledge: bool = False) -> bool:
        """
        设置实体定义（会覆盖旧定义）

        Args:
            entity_uuid: 实体UUID
            content: 定义内容
            type_: 类型
            source: 来源
            confidence: 置信度
            priority: 优先级
            is_base_knowledge: 是否来自基础知识

        Returns:
            是否设置成功
        """
        try:
            if self.debug:
                print(f"🐛 [DEBUG] 设置实体定义: {entity_uuid[:8]}... | 类型: {type_}")

            now = datetime.now().isoformat()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 先删除旧定义
                cursor.execute('DELETE FROM entity_definitions WHERE entity_uuid = ?', (entity_uuid,))
                # 插入新定义
                cursor.execute('''
                    INSERT INTO entity_definitions 
                    (entity_uuid, content, type, source, confidence, priority, is_base_knowledge, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entity_uuid, content, type_, source, confidence, priority,
                      1 if is_base_knowledge else 0, now, now))
                # 更新实体的updated_at
                cursor.execute('UPDATE entities SET updated_at = ? WHERE uuid = ?', (now, entity_uuid))

                if self.debug:
                    print(f"🐛 [DEBUG] ✓ 实体定义设置成功")

                return True
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ 设置实体定义时出错: {e}")
            print(f"✗ 设置实体定义时出错: {e}")
            return False

    def get_entity_definition(self, entity_uuid: str) -> Optional[Dict[str, Any]]:
        """
        获取实体定义

        Args:
            entity_uuid: 实体UUID

        Returns:
            定���字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM entity_definitions WHERE entity_uuid = ?', (entity_uuid,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # ==================== 实体相关信息方法 ====================

    def add_entity_related_info(self, entity_uuid: str, content: str, type_: str = "其他",
                                source: str = "", confidence: float = 0.7) -> str:
        """
        添加实体相关信息

        Args:
            entity_uuid: 实体UUID
            content: 信息内容
            type_: 类型
            source: 来源
            confidence: 置信度

        Returns:
            信息UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 添加实体相关信息: {entity_uuid[:8]}... | 类型: {type_}")

        info_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO entity_related_info 
                (uuid, entity_uuid, content, type, source, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (info_uuid, entity_uuid, content, type_, source, confidence, now))
            # 更新实体的updated_at
            cursor.execute('UPDATE entities SET updated_at = ? WHERE uuid = ?', (now, entity_uuid))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 相关信息添加成功: {info_uuid[:8]}...")

        return info_uuid

    def get_entity_related_info(self, entity_uuid: str) -> List[Dict[str, Any]]:
        """
        获取实体的所有相关信息

        Args:
            entity_uuid: 实体UUID

        Returns:
            相关信息列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM entity_related_info 
                WHERE entity_uuid = ? 
                ORDER BY created_at DESC
            ''', (entity_uuid,))
            return [dict(row) for row in cursor.fetchall()]

    def delete_entity_related_info(self, info_uuid: str) -> bool:
        """
        删除实体相关信息

        Args:
            info_uuid: 信息UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM entity_related_info WHERE uuid = ?', (info_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除相关信息时出错: {e}")
            return False

    # ==================== 短期记忆相关方法 ====================

    def add_short_term_message(self, role: str, content: str) -> int:
        """
        添加短期记忆消息

        Args:
            role: 角色
            content: 内容

        Returns:
            消息ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO short_term_memory (role, content, timestamp)
                VALUES (?, ?, ?)
            ''', (role, content, datetime.now().isoformat()))
            return cursor.lastrowid

    def get_short_term_messages(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取短期记忆消息

        Args:
            limit: 限制数量

        Returns:
            消息列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT * FROM short_term_memory 
                    ORDER BY id DESC LIMIT ?
                ''', (limit,))
                # 反转以保持时间顺序
                return [dict(row) for row in reversed(cursor.fetchall())]
            else:
                cursor.execute('SELECT * FROM short_term_memory ORDER BY id ASC')
                return [dict(row) for row in cursor.fetchall()]

    def delete_short_term_messages(self, message_ids: List[int]) -> bool:
        """
        删除短期记忆消息

        Args:
            message_ids: 消息ID列表

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                placeholders = ','.join('?' * len(message_ids))
                cursor.execute(f'DELETE FROM short_term_memory WHERE id IN ({placeholders})', message_ids)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除短期记忆时出错: {e}")
            return False

    def clear_short_term_memory(self) -> bool:
        """
        清空所有短期记忆

        Returns:
            是否清空成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM short_term_memory')
                return True
        except Exception as e:
            print(f"✗ 清空短期记忆时出错: {e}")
            return False

    # ==================== 长期记忆相关方法 ====================

    def add_long_term_summary(self, summary: str, rounds: int, message_count: int,
                             created_at: str, ended_at: str) -> str:
        """
        添加长期记忆概括

        Args:
            summary: 概括内容
            rounds: 轮数
            message_count: 消息数量
            created_at: 开始时间
            ended_at: 结束时间

        Returns:
            概括UUID
        """
        summary_uuid = str(uuid.uuid4())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO long_term_memory (uuid, summary, rounds, message_count, created_at, ended_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (summary_uuid, summary, rounds, message_count, created_at, ended_at))
        return summary_uuid

    def get_long_term_summaries(self) -> List[Dict[str, Any]]:
        """
        获取所有长期记忆概括

        Returns:
            概括列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM long_term_memory ORDER BY created_at ASC')
            return [dict(row) for row in cursor.fetchall()]

    def clear_long_term_memory(self) -> bool:
        """
        清空所有长期记忆

        Returns:
            是否清空成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM long_term_memory')
                return True
        except Exception as e:
            print(f"✗ 清空长期记忆时出错: {e}")
            return False

    # ==================== 情感分析相关方法 ====================

    def add_emotion_analysis(self, relationship_type: str, emotional_tone: str,
                            overall_score: int, intimacy: int, trust: int,
                            pleasure: int, resonance: int, dependence: int,
                            analysis_summary: str) -> str:
        """
        添加情感分析记录

        Args:
            relationship_type: 关系类型
            emotional_tone: 情感基调
            overall_score: 总体评分
            intimacy: 亲密度
            trust: 信任度
            pleasure: 愉悦度
            resonance: 共鸣度
            dependence: 依赖度
            analysis_summary: 分析摘要

        Returns:
            分析UUID
        """
        analysis_uuid = str(uuid.uuid4())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO emotion_history 
                (uuid, relationship_type, emotional_tone, overall_score, intimacy, trust, 
                 pleasure, resonance, dependence, analysis_summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (analysis_uuid, relationship_type, emotional_tone, overall_score,
                  intimacy, trust, pleasure, resonance, dependence, analysis_summary,
                  datetime.now().isoformat()))
        return analysis_uuid

    def get_emotion_history(self) -> List[Dict[str, Any]]:
        """
        获取情感分析历史

        Returns:
            情感分析列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emotion_history ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def get_latest_emotion(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的情感分析

        Returns:
            最新的情感分析字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM emotion_history ORDER BY created_at DESC LIMIT 1')
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    # ==================== 元数据相关方法 ====================

    def set_metadata(self, key: str, value: Any) -> bool:
        """
        设置元数据

        Args:
            key: 键
            value: 值（会被转换为JSON字符串）

        Returns:
            是否设置成功
        """
        try:
            value_str = json.dumps(value, ensure_ascii=False)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO metadata (key, value, updated_at)
                    VALUES (?, ?, ?)
                ''', (key, value_str, datetime.now().isoformat()))
                return True
        except Exception as e:
            print(f"✗ 设置元数据时出错: {e}")
            return False

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据

        Args:
            key: 键
            default: 默认值

        Returns:
            元数据值
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM metadata WHERE key = ?', (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row['value'])
                return default
        except Exception as e:
            print(f"✗ 获取元数据时出错: {e}")
            return default

    # ==================== 数据迁移相关方法 ====================

    def migrate_from_json(self, json_file_path: str, data_type: str) -> bool:
        """
        从JSON文件迁移数据到数据库

        Args:
            json_file_path: JSON文件路径
            data_type: 数据类型 ('base_knowledge', 'knowledge_base', 'short_term', 'long_term')

        Returns:
            是否迁移成功
        """
        try:
            import os
            if not os.path.exists(json_file_path):
                print(f"○ JSON文件不存在: {json_file_path}")
                return False

            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data_type == 'base_knowledge':
                return self._migrate_base_knowledge(data)
            elif data_type == 'knowledge_base':
                return self._migrate_knowledge_base(data)
            elif data_type == 'short_term':
                return self._migrate_short_term(data)
            elif data_type == 'long_term':
                return self._migrate_long_term(data)
            else:
                print(f"✗ 未知的数据类型: {data_type}")
                return False
        except Exception as e:
            print(f"✗ 迁移数据时出错: {e}")
            return False

    def _migrate_base_knowledge(self, data: Dict) -> bool:
        """迁移基础知识数据"""
        base_facts = data.get('base_facts', {})
        count = 0
        for entity_name, fact in base_facts.items():
            if self.add_base_fact(
                entity_name=fact.get('entity_name', entity_name),
                content=fact.get('content', ''),
                category=fact.get('category', '通用'),
                description=fact.get('description', ''),
                immutable=fact.get('immutable', True)
            ):
                count += 1
        print(f"✓ 迁移基础知识: {count}/{len(base_facts)} 条")
        return True

    def _migrate_knowledge_base(self, data: Dict) -> bool:
        """迁移知识库数据"""
        entities = data.get('entities', {})
        count = 0
        for entity_uuid, entity_data in entities.items():
            # 创建实体
            name = entity_data.get('name', '未知')
            new_uuid = self.create_entity(name)

            # 迁移定义
            definition = entity_data.get('definition')
            if definition:
                self.set_entity_definition(
                    entity_uuid=new_uuid,
                    content=definition.get('content', ''),
                    type_=definition.get('type', '定义'),
                    source=definition.get('source', ''),
                    confidence=definition.get('confidence', 1.0),
                    priority=definition.get('priority', 50),
                    is_base_knowledge=definition.get('is_base_knowledge', False)
                )

            # 迁移相关信息
            related_info = entity_data.get('related_info', [])
            for info in related_info:
                self.add_entity_related_info(
                    entity_uuid=new_uuid,
                    content=info.get('content', ''),
                    type_=info.get('type', '其他'),
                    source=info.get('source', ''),
                    confidence=info.get('confidence', 0.7)
                )
            count += 1
        print(f"✓ 迁移知识库: {count}/{len(entities)} 个实体")
        return True

    def _migrate_short_term(self, data: Dict) -> bool:
        """迁移短期记忆数据"""
        messages = data.get('messages', [])
        count = 0
        for msg in messages:
            self.add_short_term_message(
                role=msg.get('role', 'user'),
                content=msg.get('content', '')
            )
            count += 1
        print(f"✓ 迁移短期记忆: {count}/{len(messages)} 条")
        return True

    def _migrate_long_term(self, data: Dict) -> bool:
        """迁移长期记忆数据"""
        summaries = data.get('summaries', [])
        count = 0
        for summary in summaries:
            self.add_long_term_summary(
                summary=summary.get('summary', ''),
                rounds=summary.get('rounds', 0),
                message_count=summary.get('message_count', 0),
                created_at=summary.get('created_at', datetime.now().isoformat()),
                ended_at=summary.get('ended_at', datetime.now().isoformat())
            )
            count += 1
        print(f"✓ 迁移长期记忆: {count}/{len(summaries)} 条")
        return True

    # ==================== 统计和查询方法 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # 基础知识统计
            cursor.execute('SELECT COUNT(*) as count FROM base_knowledge')
            stats['base_knowledge_count'] = cursor.fetchone()['count']

            # 实体统计
            cursor.execute('SELECT COUNT(*) as count FROM entities')
            stats['entities_count'] = cursor.fetchone()['count']

            # 短期记忆统计
            cursor.execute('SELECT COUNT(*) as count FROM short_term_memory')
            stats['short_term_count'] = cursor.fetchone()['count']

            # 长期记忆统计
            cursor.execute('SELECT COUNT(*) as count FROM long_term_memory')
            stats['long_term_count'] = cursor.fetchone()['count']

            # 情感分析统计
            cursor.execute('SELECT COUNT(*) as count FROM emotion_history')
            stats['emotion_count'] = cursor.fetchone()['count']

            # 数据库文件大小
            import os
            if os.path.exists(self.db_path):
                stats['db_size_kb'] = os.path.getsize(self.db_path) / 1024

            return stats

    def search_entities(self, keyword: str) -> List[Dict[str, Any]]:
        """
        搜索实体

        Args:
            keyword: 关键词

        Returns:
            匹配的实体列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM entities 
                WHERE name LIKE ? OR normalized_name LIKE ?
                ORDER BY created_at DESC
            ''', (f'%{keyword}%', f'%{keyword}%'))
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 环境描述相关方法（智能体伪视觉） ====================

    def create_environment(self, name: str, overall_description: str,
                          atmosphere: str = "", lighting: str = "",
                          sounds: str = "", smells: str = "") -> str:
        """
        创建新环境描述

        Args:
            name: 环境名称
            overall_description: 整体描述
            atmosphere: 氛围
            lighting: 光照
            sounds: 声音
            smells: 气味

        Returns:
            环境UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 创建环境: {name}")

        env_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO environment_descriptions 
                (uuid, name, overall_description, atmosphere, lighting, sounds, smells, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (env_uuid, name, overall_description, atmosphere, lighting, sounds, smells, now, now))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 环境创建成功: {name} | UUID: {env_uuid[:8]}...")

        return env_uuid

    def get_environment(self, env_uuid: str) -> Optional[Dict[str, Any]]:
        """
        获取环境描述

        Args:
            env_uuid: 环境UUID

        Returns:
            环境描述字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_descriptions WHERE uuid = ?', (env_uuid,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_active_environment(self) -> Optional[Dict[str, Any]]:
        """
        获取当前激活的环境

        Returns:
            环境描述字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM environment_descriptions 
                WHERE is_active = 1 
                ORDER BY updated_at DESC 
                LIMIT 1
            ''')
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_environments(self) -> List[Dict[str, Any]]:
        """
        获取所有环境描述

        Returns:
            环境描述列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_descriptions ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def update_environment(self, env_uuid: str, **kwargs) -> bool:
        """
        更新环境描述

        Args:
            env_uuid: 环境UUID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        try:
            if not kwargs:
                return False

            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            set_clause += ", updated_at = ?"
            values = list(kwargs.values()) + [datetime.now().isoformat(), env_uuid]

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE environment_descriptions 
                    SET {set_clause}
                    WHERE uuid = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新环境时出错: {e}")
            return False

    def set_active_environment(self, env_uuid: str) -> bool:
        """
        设置激活的环境（会将其他环境设为非激活）

        Args:
            env_uuid: 环境UUID

        Returns:
            是否设置成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 先将所有环境设为非激活
                cursor.execute('UPDATE environment_descriptions SET is_active = 0')
                # 再激活指定环境
                cursor.execute('UPDATE environment_descriptions SET is_active = 1 WHERE uuid = ?', (env_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 设置激活环境时出错: {e}")
            return False

    def delete_environment(self, env_uuid: str) -> bool:
        """
        删除环境描述（会级联删除相关物体）

        Args:
            env_uuid: 环境UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM environment_descriptions WHERE uuid = ?', (env_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除环境时出错: {e}")
            return False

    def add_environment_object(self, environment_uuid: str, name: str, description: str,
                              position: str = "", properties: str = "",
                              interaction_hints: str = "", priority: int = 50) -> str:
        """
        添加环境物体

        Args:
            environment_uuid: 环境UUID
            name: 物体名称
            description: 物体描述
            position: 位置
            properties: 属性（JSON字符串）
            interaction_hints: 交互提示
            priority: 优先级（越高越重要）

        Returns:
            物体UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 添加环境物体: {name} 到环境 {environment_uuid[:8]}...")

        obj_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO environment_objects 
                (uuid, environment_uuid, name, description, position, properties, 
                 interaction_hints, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (obj_uuid, environment_uuid, name, description, position, properties,
                  interaction_hints, priority, now, now))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 物体添加成功: {name} | UUID: {obj_uuid[:8]}...")

        return obj_uuid

    def get_environment_objects(self, environment_uuid: str, visible_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取环境中的所有物体

        Args:
            environment_uuid: 环境UUID
            visible_only: 是否只返回可见物体

        Returns:
            物体列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if visible_only:
                cursor.execute('''
                    SELECT * FROM environment_objects 
                    WHERE environment_uuid = ? AND is_visible = 1 
                    ORDER BY priority DESC, name ASC
                ''', (environment_uuid,))
            else:
                cursor.execute('''
                    SELECT * FROM environment_objects 
                    WHERE environment_uuid = ? 
                    ORDER BY priority DESC, name ASC
                ''', (environment_uuid,))
            return [dict(row) for row in cursor.fetchall()]

    def get_object(self, obj_uuid: str) -> Optional[Dict[str, Any]]:
        """
        获取物体信息

        Args:
            obj_uuid: 物体UUID

        Returns:
            物体字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_objects WHERE uuid = ?', (obj_uuid,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def update_object(self, obj_uuid: str, **kwargs) -> bool:
        """
        更新物体信息

        Args:
            obj_uuid: 物体UUID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        try:
            if not kwargs:
                return False

            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            set_clause += ", updated_at = ?"
            values = list(kwargs.values()) + [datetime.now().isoformat(), obj_uuid]

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE environment_objects 
                    SET {set_clause}
                    WHERE uuid = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新物体时出错: {e}")
            return False

    def delete_object(self, obj_uuid: str) -> bool:
        """
        删除物体

        Args:
            obj_uuid: 物体UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM environment_objects WHERE uuid = ?', (obj_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除物体时出错: {e}")
            return False

    def log_vision_tool_usage(self, query: str, environment_uuid: Optional[str] = None,
                             objects_viewed: str = "", context_provided: str = "",
                             triggered_by: str = "auto") -> str:
        """
        记录视觉工具使用

        Args:
            query: 用户查询
            environment_uuid: 环境UUID
            objects_viewed: 查看的物体（逗号分隔）
            context_provided: 提供的上下文
            triggered_by: 触发方式（auto/manual）

        Returns:
            日志UUID
        """
        log_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO vision_tool_logs 
                (uuid, query, environment_uuid, objects_viewed, context_provided, triggered_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (log_uuid, query, environment_uuid, objects_viewed, context_provided, triggered_by, now))

        if self.debug:
            print(f"🐛 [DEBUG] 视觉工具使用已记录: {log_uuid[:8]}...")

        return log_uuid

    def get_vision_tool_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取视觉工具使用日志

        Args:
            limit: 返回的日志条数限制

        Returns:
            日志列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM vision_tool_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    # ==================== 环境连接关系方法 ====================

    def create_environment_connection(self, from_env_uuid: str, to_env_uuid: str,
                                     connection_type: str = "normal",
                                     direction: str = "bidirectional",
                                     description: str = "") -> str:
        """
        创建环境之间的连接关系

        Args:
            from_env_uuid: 起始环境UUID
            to_env_uuid: 目标环境UUID
            connection_type: 连接类型 (normal, door, portal, stairs, etc.)
            direction: 连接方向 (bidirectional, one_way)
            description: 连接描述

        Returns:
            连接UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 创建环境连接: {from_env_uuid[:8]}... -> {to_env_uuid[:8]}...")

        # 检查两个环境是否相同
        if from_env_uuid == to_env_uuid:
            raise ValueError("不能创建环境到自身的连接")

        conn_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO environment_connections 
                    (uuid, from_environment_uuid, to_environment_uuid, connection_type, direction, description, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (conn_uuid, from_env_uuid, to_env_uuid, connection_type, direction, description, now, now))

                if self.debug:
                    print(f"🐛 [DEBUG] ✓ 环境连接创建成功: {conn_uuid[:8]}...")

                return conn_uuid
        except sqlite3.IntegrityError:
            if self.debug:
                print(f"🐛 [DEBUG] ⚠ 环境连接已存在")
            raise ValueError("该环境连接已存在")

    def get_environment_connections(self, env_uuid: str, direction: str = "both") -> List[Dict[str, Any]]:
        """
        获取环境的所有连接

        Args:
            env_uuid: 环境UUID
            direction: 查询方向 ("from" - 从此环境出发, "to" - 到达此环境, "both" - 双向)

        Returns:
            连接列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if direction == "from":
                cursor.execute('''
                    SELECT * FROM environment_connections 
                    WHERE from_environment_uuid = ?
                    ORDER BY created_at DESC
                ''', (env_uuid,))
            elif direction == "to":
                cursor.execute('''
                    SELECT * FROM environment_connections 
                    WHERE to_environment_uuid = ?
                    ORDER BY created_at DESC
                ''', (env_uuid,))
            else:  # both
                cursor.execute('''
                    SELECT * FROM environment_connections 
                    WHERE from_environment_uuid = ? OR to_environment_uuid = ?
                    ORDER BY created_at DESC
                ''', (env_uuid, env_uuid))
            return [dict(row) for row in cursor.fetchall()]

    def get_connected_environments(self, env_uuid: str) -> List[Dict[str, Any]]:
        """
        获取与指定环境连通的所有环境

        Args:
            env_uuid: 环境UUID

        Returns:
            连通的环境列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 查找所有连接（双向或单向）
            cursor.execute('''
                SELECT DISTINCT
                    CASE 
                        WHEN from_environment_uuid = ? THEN to_environment_uuid
                        WHEN to_environment_uuid = ? AND direction = 'bidirectional' THEN from_environment_uuid
                    END as connected_uuid
                FROM environment_connections
                WHERE (from_environment_uuid = ? OR (to_environment_uuid = ? AND direction = 'bidirectional'))
            ''', (env_uuid, env_uuid, env_uuid, env_uuid))
            
            connected_uuids = [row['connected_uuid'] for row in cursor.fetchall() if row['connected_uuid']]
            
            # 获取这些环境的详细信息
            if not connected_uuids:
                return []
            
            placeholders = ','.join('?' * len(connected_uuids))
            cursor.execute(f'''
                SELECT * FROM environment_descriptions 
                WHERE uuid IN ({placeholders})
            ''', connected_uuids)
            
            return [dict(row) for row in cursor.fetchall()]

    def can_move_to_environment(self, from_env_uuid: str, to_env_uuid: str) -> bool:
        """
        检查是否可以从一个环境移动到另一个环境

        Args:
            from_env_uuid: 起始环境UUID
            to_env_uuid: 目标环境UUID

        Returns:
            是否可以移动
        """
        if from_env_uuid == to_env_uuid:
            return True  # 同一个环境，总是可以的

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否存在直接连接
            cursor.execute('''
                SELECT COUNT(*) as count FROM environment_connections
                WHERE from_environment_uuid = ? AND to_environment_uuid = ?
                   OR (to_environment_uuid = ? AND from_environment_uuid = ? AND direction = 'bidirectional')
            ''', (from_env_uuid, to_env_uuid, from_env_uuid, to_env_uuid))
            
            result = cursor.fetchone()
            return result['count'] > 0

    def delete_environment_connection(self, conn_uuid: str) -> bool:
        """
        删除环境连接

        Args:
            conn_uuid: 连接UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM environment_connections WHERE uuid = ?', (conn_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除环境连接时出错: {e}")
            return False

    def get_all_environment_connections(self) -> List[Dict[str, Any]]:
        """
        获取所有环境连接

        Returns:
            所有连接列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_connections ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    # ==================== Debug辅助方法 ====================

    def enable_debug(self):
        """启用调试模式"""
        self.debug = True
        print("🐛 [DEBUG] 调试模式已启用")

    def disable_debug(self):
        """禁用调试模式"""
        self.debug = False
        print("✓ 调试模式已禁用")

    def log_operation(self, operation: str, details: str = ""):
        """
        记录操作日志

        Args:
            operation: 操作类型
            details: 操作详情
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'operation': operation,
            'details': details
        }
        self._operation_log.append(log_entry)

        if self.debug:
            print(f"🐛 [DEBUG] [{timestamp}] {operation}: {details}")

    def get_operation_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取操作日志

        Args:
            limit: 返回的日志条数限制

        Returns:
            操作日志列表
        """
        return self._operation_log[-limit:]

    def clear_operation_log(self):
        """清空操作日志"""
        self._operation_log.clear()
        if self.debug:
            print("🐛 [DEBUG] 操作日志已清空")

    def get_debug_info(self) -> Dict[str, Any]:
        """
        获取调试信息

        Returns:
            包含调试信息的字典
        """
        stats = self.get_statistics()

        debug_info = {
            'debug_enabled': self.debug,
            'db_path': self.db_path,
            'query_count': self._query_count,
            'operation_log_count': len(self._operation_log),
            'statistics': stats
        }

        if self.debug:
            print("🐛 [DEBUG] 调试信息:")
            for key, value in debug_info.items():
                print(f"  {key}: {value}")

        return debug_info

    def execute_query(self, query: str, params: tuple = None) -> None:
        """
        执行SQL查询（用于INSERT/UPDATE/DELETE）

        Args:
            query: SQL查询语句
            params: 查询参数
        """
        with self.get_connection() as conn:
            if params:
                conn.execute(query, params)
            else:
                conn.execute(query)

    def fetch_one(self, query: str, params: tuple = None) -> Optional[tuple]:
        """
        查询单条记录

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果行或None
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params) if params else conn.execute(query)
            return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple = None) -> List[tuple]:
        """
        查询多条记录

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params) if params else conn.execute(query)
            return cursor.fetchall()


if __name__ == '__main__':
    print("=" * 60)
    print("数据库管理器测试")
    print("=" * 60)

    # 创建数据库管理器实例
    db = DatabaseManager("test_chat_agent.db")

    # 测试添加基础知识
    print("\n测试添加基础知识:")
    db.add_base_fact("HeDaas", "HeDaas是一个高校", "机构类型", "HeDaas的基本定义")

    # 测试获取统计信息
    print("\n数据库统计:")
    stats = db.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 测试创建实体
    print("\n测试创建实体:")
    entity_uuid = db.find_or_create_entity("测试实体")
    print(f"  实体UUID: {entity_uuid}")

    # 测试设置定义
    print("\n测试设置实体定义:")
    db.set_entity_definition(entity_uuid, "这是一个测试实体", "定义", "测试")

    # 测试添加相关信息
    print("\n测试添加相关信息:")
    db.add_entity_related_info(entity_uuid, "相关信息1", "其他", "测试")
    db.add_entity_related_info(entity_uuid, "相关信息2", "其他", "测试")

    # 获取完整实体信息
    print("\n获取完整实体信息:")
    entity = db.get_entity_by_uuid(entity_uuid)
    definition = db.get_entity_definition(entity_uuid)
    related_info = db.get_entity_related_info(entity_uuid)
    print(f"  实体: {entity}")
    print(f"  定义: {definition}")
    print(f"  相关信息数量: {len(related_info)}")

    print("\n✓ 测试完成")

