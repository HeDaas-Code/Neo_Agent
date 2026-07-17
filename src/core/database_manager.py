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
    
    # 知识状态常量
    STATUS_SUSPECTED = "疑似"  # 疑似状态：首次提及，需要进一步确认
    STATUS_CONFIRMED = "确认"  # 确认状态：多次提及，高可信度
    
    # 知识状态升级阈值：当提及次数达到此值时，状态从"疑似"升级为"确认"
    KNOWLEDGE_CONFIRMATION_THRESHOLD = 3

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
        # v4.0: 为内存数据库复用同一连接，避免 ':memory:' 每次新连接都是空库
        self._memory_conn = None

        if self.debug:
            print(f"🐛 [DEBUG] 数据库管理器初始化 - 路径: {db_path}")

        self.init_database()

    @staticmethod
    def _truncate_uuid(uuid_str: str, length: int = 8) -> str:
        """
        安全截取UUID用于显示
        
        Args:
            uuid_str: UUID字符串
            length: 截取长度
            
        Returns:
            截取后的UUID字符串
        """
        if not uuid_str:
            return ""
        return (uuid_str[:length] + '...') if len(uuid_str) > length else uuid_str

    def _open_connection(self):
        """打开并配置一个新的 SQLite 连接。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以像字典一样访问

        # Stage D.1: 启用 SQLite WAL 模式（提升并发读性能，让 Web/Scheduler/Tkinter 多端共存）
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except Exception as pragma_err:
            # WAL 启用失败不应阻塞主流程
            if self.debug:
                print(f"🐛 [DEBUG] 启用 WAL 失败: {pragma_err}")

        # v3.1.0: 启用外键约束（chat_messages.session_id ON DELETE CASCADE 需要）
        try:
            conn.execute("PRAGMA foreign_keys=ON")
        except Exception as pragma_err:
            if self.debug:
                print(f"🐛 [DEBUG] 启用 foreign_keys 失败: {pragma_err}")

        return conn

    @contextmanager
    def get_connection(self):
        """
        获取数据库连接的上下文管理器。

        对 ':memory:' 数据库复用同一连接，避免每次新连接都是空库；
        文件数据库仍按原有方式每次打开/关闭连接。
        """
        if self.debug:
            print(f"🐛 [DEBUG] 打开数据库连接: {self.db_path}")

        is_memory = self.db_path == ":memory:"
        if is_memory:
            if self._memory_conn is None:
                self._memory_conn = self._open_connection()
            conn = self._memory_conn
        else:
            conn = self._open_connection()

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
            if not is_memory:
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
                    status TEXT DEFAULT '疑似',
                    mention_count INTEGER DEFAULT 1,
                    last_mentioned_at TEXT,
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

            # 13. 智能体个性化表达表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS agent_expressions (
                    uuid TEXT PRIMARY KEY,
                    expression TEXT NOT NULL,
                    meaning TEXT NOT NULL,
                    category TEXT DEFAULT '通用',
                    usage_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 14. 用户表达习惯学习表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_expression_habits (
                    uuid TEXT PRIMARY KEY,
                    expression_pattern TEXT NOT NULL,
                    meaning TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0.8,
                    learned_from_rounds TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 15. 环境域表（环境集合的概念）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS environment_domains (
                    uuid TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    default_environment_uuid TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (default_environment_uuid) REFERENCES environment_descriptions(uuid) ON DELETE SET NULL
                )
            ''')

            # 16. 域环境关联表（域包含的环境）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS domain_environments (
                    uuid TEXT PRIMARY KEY,
                    domain_uuid TEXT NOT NULL,
                    environment_uuid TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (domain_uuid) REFERENCES environment_domains(uuid) ON DELETE CASCADE,
                    FOREIGN KEY (environment_uuid) REFERENCES environment_descriptions(uuid) ON DELETE CASCADE,
                    UNIQUE(domain_uuid, environment_uuid)
                )
            ''')

            # 17. 生活状态日快照表（P1：LifeStateManager）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS life_state_daily (
                    date TEXT PRIMARY KEY,
                    energy REAL DEFAULT 0.7,
                    mood TEXT DEFAULT '平静',
                    state_title TEXT DEFAULT '常态',
                    health TEXT DEFAULT '健康',
                    conditions_json TEXT,
                    transition_options_json TEXT,
                    energy_delta REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 18. 梦境记录表（P1：DreamDiaryManager）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dream_records (
                    uuid TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    dream_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    afterglow TEXT,
                    label TEXT,
                    mood TEXT,
                    energy_delta REAL DEFAULT 0.0,
                    duration_hours REAL DEFAULT 7.0,
                    weather_json TEXT,
                    created_at TEXT NOT NULL
                )
            ''')

            # 19. 日记条目表（P1：DreamDiaryManager）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS diary_entries (
                    uuid TEXT PRIMARY KEY,
                    date TEXT NOT NULL,
                    title TEXT,
                    body TEXT NOT NULL,
                    mood TEXT,
                    tags_json TEXT,
                    related_entities_json TEXT,
                    word_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            ''')

            # 20. 未完话题表（P2：OpenLoopTracker）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS open_loops (
                    uuid TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    raised_at TEXT NOT NULL,
                    resolved_at TEXT,
                    related_keywords_json TEXT,
                    context TEXT,
                    mention_count INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 21. 创作项目表（P3：CreativeProjectManager）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creative_projects (
                    uuid TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    work_type TEXT NOT NULL,
                    premise TEXT,
                    tone TEXT,
                    point_of_view TEXT,
                    target_chars INTEGER DEFAULT 5000,
                    current_chars INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'drafting',
                    inspiration_source TEXT,
                    outline_json TEXT,
                    characters_json TEXT,
                    draft_chunks_json TEXT,
                    next_advance_at TEXT,
                    last_advanced_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # 22. Story Bible 表（P3：项目级线索状态机）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creative_story_bibles (
                    project_uuid TEXT PRIMARY KEY,
                    mainline_direction TEXT,
                    active_themes_json TEXT,
                    unresolved_threads_json TEXT,
                    resolved_threads_json TEXT,
                    important_facts_json TEXT,
                    next_direction TEXT,
                    recent_keywords_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (project_uuid) REFERENCES creative_projects(uuid) ON DELETE CASCADE
                )
            ''')

            # 23. 创作记忆池（P3：碎片化上下文）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS creative_memory_pool (
                    uuid TEXT PRIMARY KEY,
                    project_uuid TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_uuid) REFERENCES creative_projects(uuid) ON DELETE CASCADE
                )
            ''')

            # 24. 聊天会话表（v3.1.0：会话持久化）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '新会话',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    message_count INTEGER DEFAULT 0
                )
            ''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at DESC)''')

            # 25. 聊天消息表（v3.1.0：会话持久化）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    emotion_json TEXT,
                    conn_id TEXT,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id)''')
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at)''')

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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_agent_expressions_active ON agent_expressions(is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_expressions_confidence ON user_expression_habits(confidence)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain_environments_domain ON domain_environments(domain_uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_domain_environments_env ON domain_environments(environment_uuid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_life_state_date ON life_state_daily(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_dream_records_date ON dream_records(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_diary_entries_date ON diary_entries(date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_open_loops_status ON open_loops(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_open_loops_raised_at ON open_loops(raised_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_creative_projects_status ON creative_projects(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_creative_projects_next_advance ON creative_projects(next_advance_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_creative_pool_project ON creative_memory_pool(project_uuid)')

            conn.commit()
        if INIT_Database_PreParation_Complete == False:
            print("✓ 数据库初始化完成")
            INIT_Database_PreParation_Complete = True
        
        # 执行数据库迁移
        self._migrate_database()

    def _migrate_database(self):
        """
        执行数据库迁移，添加新字段到已存在的表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查 entity_related_info 表是否有新字段
            cursor.execute("PRAGMA table_info(entity_related_info)")
            columns = [row[1] for row in cursor.fetchall()]
            
            migrations_needed = []
            if 'status' not in columns:
                migrations_needed.append(('status', f"ALTER TABLE entity_related_info ADD COLUMN status TEXT DEFAULT '{self.STATUS_SUSPECTED}'"))
            if 'mention_count' not in columns:
                migrations_needed.append(('mention_count', "ALTER TABLE entity_related_info ADD COLUMN mention_count INTEGER DEFAULT 1"))
            if 'last_mentioned_at' not in columns:
                migrations_needed.append(('last_mentioned_at', "ALTER TABLE entity_related_info ADD COLUMN last_mentioned_at TEXT"))
            
            if migrations_needed:
                print(f"○ 检测到数据库需要迁移，正在添加新字段...")
                for field_name, sql in migrations_needed:
                    try:
                        cursor.execute(sql)
                        print(f"  ✓ 已添加字段: {field_name}")
                    except Exception as e:
                        if self.debug:
                            print(f"  ⚠ 字段 {field_name} 可能已存在: {e}")
                conn.commit()
                print("✓ 数据库迁移完成")


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

    def get_all_entities(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取所有实体

        Args:
            limit: 可选；返回的最大条数（None 表示不限制）

        Returns:
            实体列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if limit is not None:
                try:
                    safe_limit = max(1, min(int(limit), 1000))
                except (TypeError, ValueError):
                    safe_limit = 100
                cursor.execute(
                    'SELECT * FROM entities ORDER BY created_at DESC LIMIT ?',
                    (safe_limit,),
                )
            else:
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

    # ==================== Stage C.1: Knowledge CRUD 包装 ====================
    # 上述低阶方法（create_entity / set_entity_definition / add_entity_related_info
    # / get_entity_by_uuid / get_entity_by_name ...）粒度较细；为 Web 后端
    # 暴露更"业务"的方法，使其与 schema 字段 (entity_name / category /
    # description / related_info) 对齐。注意：以下方法不修改既有方法签名。

    def search_knowledge(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        按关键词搜索实体（Stage C.1）。

        匹配范围：entities.name / entities.normalized_name。
        返回的每条记录会附带 ``category`` / ``description`` 字段（如果有定义），
        便于 Web 前端直接渲染。

        Args:
            query: 搜索关键词（空串返回空列表）
            limit: 返回条数上限（默认 20，最大 200）

        Returns:
            实体列表
        """
        try:
            safe_limit = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            safe_limit = 20

        q = (query or "").strip()
        if not q:
            return []

        like = f"%{q}%"
        results: List[Dict[str, Any]] = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT * FROM entities
                WHERE name LIKE ? OR normalized_name LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                ''',
                (like, like, safe_limit),
            )
            rows = [dict(row) for row in cursor.fetchall()]

        for row in rows:
            entity_uuid = row.get("uuid")
            definition = None
            if entity_uuid:
                try:
                    definition = self.get_entity_definition(entity_uuid)
                except Exception:
                    definition = None
            if definition:
                row["category"] = definition.get("type", "通用")
                row["description"] = definition.get("content", "")
            else:
                row.setdefault("category", "通用")
                row.setdefault("description", "")
            results.append(row)
        return results

    def add_entity(
        self,
        entity_name: str,
        category: Optional[str] = None,
        description: Optional[str] = None,
        related_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        新增一个实体（Stage C.1）。

        行为：
        1. 在 ``entities`` 表创建记录。
        2. 若 ``description`` 非空，在 ``entity_definitions`` 写入定义
           （``type`` 优先用 ``category``，否则 "定义"）。
        3. 若 ``related_info`` 是 dict，按 ``key -> value`` 写入
           ``entity_related_info``（type=key，content=str(value)）。

        Args:
            entity_name: 实体名称（必填）
            category: 分类（可选，映射到定义 type）
            description: 描述（可选，映射到定义 content）
            related_info: 相关信息字典（可选）

        Returns:
            新实体的 uuid
        """
        if not entity_name or not isinstance(entity_name, str):
            raise ValueError("entity_name 必须是非空字符串")

        name = entity_name.strip()
        if not name:
            raise ValueError("entity_name 不能为空")

        # 1) 创建实体（find_or_create_entity 避免重名冲突）
        entity_uuid = self.find_or_create_entity(name)

        # 2) 写入定义（如有）
        if description is not None and str(description).strip():
            try:
                self.set_entity_definition(
                    entity_uuid=entity_uuid,
                    content=str(description),
                    type_=(category or "定义"),
                    source="web_crud",
                    confidence=1.0,
                    priority=50,
                    is_base_knowledge=False,
                )
            except Exception:
                # 定义写入失败不影响主流程
                pass

        # 3) 写入 related_info（如有）
        if isinstance(related_info, dict) and related_info:
            for k, v in related_info.items():
                try:
                    self.add_entity_related_info(
                        entity_uuid=entity_uuid,
                        content=str(v),
                        type_=str(k)[:64] or "其他",
                        source="web_crud",
                        confidence=0.7,
                        status="疑似",
                        mention_count=1,
                    )
                except Exception:
                    # 单条 related_info 失败不影响其他条目
                    continue

        return entity_uuid

    def update_entity(
        self,
        entity_uuid: str,
        entity_name: Optional[str] = None,
        category: Optional[str] = None,
        description: Optional[str] = None,
        related_info: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新实体（Stage C.1）。

        - ``entity_name`` 非空 → 改 entities.name + 重新计算 normalized_name。
        - ``description`` 非空 → 覆盖 entity_definitions。
        - ``category`` 非空 → 作为新定义的 type。
        - ``related_info`` 是 dict → 整体替换（先删后插）该实体的 related_info。

        Returns:
            是否至少有一个字段被更新
        """
        if not entity_uuid or not isinstance(entity_uuid, str):
            raise ValueError("entity_uuid 必须是非空字符串")

        existing = self.get_entity_by_uuid(entity_uuid)
        if not existing:
            return False

        updated = False

        # 1) 改名
        if entity_name is not None and str(entity_name).strip():
            new_name = str(entity_name).strip()
            if new_name != existing.get("name"):
                new_norm = new_name.lower()
                now_iso = datetime.now().isoformat()
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        '''
                        UPDATE entities
                        SET name = ?, normalized_name = ?, updated_at = ?
                        WHERE uuid = ?
                        ''',
                        (new_name, new_norm, now_iso, entity_uuid),
                    )
                updated = True

        # 2) 更新定义（description 触发；category 影响 type）
        if description is not None and str(description).strip():
            try:
                self.set_entity_definition(
                    entity_uuid=entity_uuid,
                    content=str(description),
                    type_=(category or "定义"),
                    source="web_crud",
                    confidence=1.0,
                    priority=50,
                    is_base_knowledge=False,
                )
                updated = True
            except Exception:
                pass

        # 3) 替换 related_info（如提供）
        if isinstance(related_info, dict):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM entity_related_info WHERE entity_uuid = ?",
                        (entity_uuid,),
                    )
                for k, v in related_info.items():
                    try:
                        self.add_entity_related_info(
                            entity_uuid=entity_uuid,
                            content=str(v),
                            type_=str(k)[:64] or "其他",
                            source="web_crud",
                            confidence=0.7,
                            status="疑似",
                            mention_count=1,
                        )
                    except Exception:
                        continue
                updated = True
            except Exception:
                pass

        return updated

    def delete_entity(self, entity_uuid: str) -> bool:
        """
        删除实体（Stage C.1）。

        会先级联删除 ``entity_definitions`` / ``entity_related_info``，
        再删 ``entities``。不存在的 uuid 返回 False。

        Returns:
            是否成功删除
        """
        if not entity_uuid or not isinstance(entity_uuid, str):
            return False

        existing = self.get_entity_by_uuid(entity_uuid)
        if not existing:
            return False

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # 先清掉子表（避免 FK 约束问题）
                try:
                    cursor.execute(
                        "DELETE FROM entity_definitions WHERE entity_uuid = ?",
                        (entity_uuid,),
                    )
                except Exception:
                    pass
                try:
                    cursor.execute(
                        "DELETE FROM entity_related_info WHERE entity_uuid = ?",
                        (entity_uuid,),
                    )
                except Exception:
                    pass
                cursor.execute(
                    "DELETE FROM entities WHERE uuid = ?",
                    (entity_uuid,),
                )
                return cursor.rowcount > 0
        except Exception:
            return False

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
                                source: str = "", confidence: float = 0.7, 
                                status: str = "疑似", mention_count: int = 1) -> str:
        """
        添加实体相关信息，如果相似信息已存在，则增加mention_count并可能升级状态

        Args:
            entity_uuid: 实体UUID
            content: 信息内容
            type_: 类型
            source: 来源
            confidence: 置信度
            status: 状态（疑似/确认）
            mention_count: 提及次数

        Returns:
            信息UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 添加实体相关信息: {entity_uuid[:8]}... | 类型: {type_}")

        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在相似的信息
            cursor.execute('''
                SELECT uuid, mention_count, status FROM entity_related_info 
                WHERE entity_uuid = ? AND content = ? AND type = ?
            ''', (entity_uuid, content, type_))
            existing = cursor.fetchone()
            
            if existing:
                # 如果已存在相同信息，增加mention_count
                existing_uuid, existing_mention_count, existing_status = existing[0], existing[1], existing[2]
                new_mention_count = existing_mention_count + 1
                # 如果提及次数达到阈值，状态升级为"确认"
                new_status = self.STATUS_CONFIRMED if new_mention_count >= self.KNOWLEDGE_CONFIRMATION_THRESHOLD else existing_status
                
                cursor.execute('''
                    UPDATE entity_related_info 
                    SET mention_count = ?, status = ?, last_mentioned_at = ?
                    WHERE uuid = ?
                ''', (new_mention_count, new_status, now, existing_uuid))
                
                # 更新实体的updated_at
                cursor.execute('UPDATE entities SET updated_at = ? WHERE uuid = ?', (now, entity_uuid))
                
                if self.debug:
                    print(f"🐛 [DEBUG] ✓ 信息已存在，更新mention_count: {new_mention_count}, 状态: {new_status}")
                
                return existing_uuid
            else:
                # 添加新信息
                info_uuid = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO entity_related_info 
                    (uuid, entity_uuid, content, type, source, confidence, status, mention_count, last_mentioned_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (info_uuid, entity_uuid, content, type_, source, confidence, status, mention_count, now, now))
                
                # 更新实体的updated_at
                cursor.execute('UPDATE entities SET updated_at = ? WHERE uuid = ?', (now, entity_uuid))

                if self.debug:
                    print(f"🐛 [DEBUG] ✓ 新相关信息添加成功: {info_uuid[:8]}..., 状态: {status}")

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

    def list_metadata_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        列出元数据键（可选前缀过滤）。
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if prefix:
                    cursor.execute(
                        "SELECT key FROM metadata WHERE key LIKE ? ORDER BY key",
                        (prefix + '%',)
                    )
                else:
                    cursor.execute("SELECT key FROM metadata ORDER BY key")
                return [row['key'] for row in cursor.fetchall()]
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ list_metadata_keys 出错: {e}")
            return []

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

    # ==================== 智能体个性化表达相关方法 ====================

    def add_agent_expression(self, expression: str, meaning: str, category: str = "通用") -> str:
        """
        添加智能体个性化表达

        Args:
            expression: 表达方式（如 'wc'）
            meaning: 含义（如 '表示对突发事情的感叹'）
            category: 分类

        Returns:
            表达UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 添加智能体表达: {expression} => {meaning}")

        expr_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_expressions 
                (uuid, expression, meaning, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (expr_uuid, expression, meaning, category, now, now))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 智能体表达添加成功: {expr_uuid[:8]}...")

        return expr_uuid

    def get_all_agent_expressions(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有智能体个性化表达

        Args:
            active_only: 是否只获取激活的表达

        Returns:
            表达列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if active_only:
                cursor.execute('''
                    SELECT * FROM agent_expressions 
                    WHERE is_active = 1 
                    ORDER BY usage_count DESC, created_at DESC
                ''')
            else:
                cursor.execute('''
                    SELECT * FROM agent_expressions 
                    ORDER BY usage_count DESC, created_at DESC
                ''')
            return [dict(row) for row in cursor.fetchall()]

    def update_agent_expression(self, expr_uuid: str, **kwargs) -> bool:
        """
        更新智能体表达

        Args:
            expr_uuid: 表达UUID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        # 白名单验证允许更新的列名
        allowed_columns = {'expression', 'meaning', 'category', 'usage_count', 'is_active'}
        
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
            values = list(safe_kwargs.values()) + [datetime.now().isoformat(), expr_uuid]

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE agent_expressions 
                    SET {set_clause}
                    WHERE uuid = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新智能体表达时出错: {e}")
            return False

    def increment_expression_usage(self, expr_uuid: str) -> bool:
        """
        增加表达使用次数

        Args:
            expr_uuid: 表达UUID

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE agent_expressions 
                    SET usage_count = usage_count + 1, updated_at = ?
                    WHERE uuid = ?
                ''', (datetime.now().isoformat(), expr_uuid))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 增加表达使用次数时出错: {e}")
            return False

    def delete_agent_expression(self, expr_uuid: str) -> bool:
        """
        删除智能体表达

        Args:
            expr_uuid: 表达UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM agent_expressions WHERE uuid = ?', (expr_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除智能体表达时出错: {e}")
            return False

    # ==================== 用户表达习惯学习相关方法 ====================

    def add_user_expression_habit(self, expression_pattern: str, meaning: str,
                                  confidence: float = 0.8, learned_from_rounds: str = "") -> str:
        """
        添加用户表达习惯

        Args:
            expression_pattern: 表达模式
            meaning: 含义
            confidence: 置信度
            learned_from_rounds: 学习来源的对话轮次

        Returns:
            习惯UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 添加用户表达习惯: {expression_pattern} => {meaning}")

        habit_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_expression_habits 
                (uuid, expression_pattern, meaning, confidence, learned_from_rounds, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (habit_uuid, expression_pattern, meaning, confidence, learned_from_rounds, now, now))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 用户表达习惯添加成功: {habit_uuid[:8]}...")

        return habit_uuid

    def get_all_user_expression_habits(self, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        获取所有用户表达习惯

        Args:
            min_confidence: 最低置信度

        Returns:
            习惯列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM user_expression_habits 
                WHERE confidence >= ?
                ORDER BY frequency DESC, confidence DESC, created_at DESC
            ''', (min_confidence,))
            return [dict(row) for row in cursor.fetchall()]

    def update_user_expression_habit(self, habit_uuid: str, **kwargs) -> bool:
        """
        更新用户表达习惯

        Args:
            habit_uuid: 习惯UUID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        # 白名单验证允许更新的列名
        allowed_columns = {'expression_pattern', 'meaning', 'frequency', 'confidence', 'learned_from_rounds'}
        
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
            values = list(safe_kwargs.values()) + [datetime.now().isoformat(), habit_uuid]

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE user_expression_habits 
                    SET {set_clause}
                    WHERE uuid = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新用户表达习惯时出错: {e}")
            return False

    def increment_habit_frequency(self, habit_uuid: str) -> bool:
        """
        增加习惯出现频率

        Args:
            habit_uuid: 习惯UUID

        Returns:
            是否成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_expression_habits 
                    SET frequency = frequency + 1, updated_at = ?
                    WHERE uuid = ?
                ''', (datetime.now().isoformat(), habit_uuid))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 增加习惯频率时出错: {e}")
            return False

    def find_user_expression_habit(self, expression_pattern: str) -> Optional[Dict[str, Any]]:
        """
        查找用户表达习惯

        Args:
            expression_pattern: 表达模式

        Returns:
            习惯字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM user_expression_habits 
                WHERE expression_pattern = ?
            ''', (expression_pattern,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def delete_user_expression_habit(self, habit_uuid: str) -> bool:
        """
        删除用户表达习惯

        Args:
            habit_uuid: 习惯UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_expression_habits WHERE uuid = ?', (habit_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除用户表达习惯时出错: {e}")
            return False

    def clear_user_expression_habits(self) -> bool:
        """
        清空所有用户表达习惯

        Returns:
            是否清空成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_expression_habits')
                return True
        except Exception as e:
            print(f"✗ 清空用户表达习惯时出错: {e}")
            return False

    # ==================== 环境域相关方法 ====================

    def create_domain(self, name: str, description: str = "", 
                      default_environment_uuid: str = None) -> str:
        """
        创建环境域（环境集合）

        Args:
            name: 域名称（如"小可家"）
            description: 域描述
            default_environment_uuid: 默认环境UUID（域间切换时的默认到达位置）

        Returns:
            域UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 创建环境域: {name}")

        domain_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO environment_domains 
                (uuid, name, description, default_environment_uuid, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (domain_uuid, name, description, default_environment_uuid, now, now))

        if self.debug:
            print(f"🐛 [DEBUG] ✓ 环境域创建成功: {name} | UUID: {self._truncate_uuid(domain_uuid)}")

        return domain_uuid

    def get_domain(self, domain_uuid: str) -> Optional[Dict[str, Any]]:
        """
        获取域信息

        Args:
            domain_uuid: 域UUID

        Returns:
            域信息字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_domains WHERE uuid = ?', (domain_uuid,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_domain_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称获取域

        Args:
            name: 域名称

        Returns:
            域信息字典或None
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_domains WHERE name = ?', (name,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_domains(self) -> List[Dict[str, Any]]:
        """
        获取所有域

        Returns:
            域列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM environment_domains ORDER BY created_at DESC')
            return [dict(row) for row in cursor.fetchall()]

    def update_domain(self, domain_uuid: str, **kwargs) -> bool:
        """
        更新域信息

        Args:
            domain_uuid: 域UUID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        # 白名单验证允许更新的列名
        allowed_columns = {'name', 'description', 'default_environment_uuid'}
        
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
            values = list(safe_kwargs.values()) + [datetime.now().isoformat(), domain_uuid]

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE environment_domains 
                    SET {set_clause}
                    WHERE uuid = ?
                ''', values)
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 更新域时出错: {e}")
            return False

    def delete_domain(self, domain_uuid: str) -> bool:
        """
        删除域（会级联删除域环境关联）

        Args:
            domain_uuid: 域UUID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM environment_domains WHERE uuid = ?', (domain_uuid,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 删除域时出错: {e}")
            return False

    def add_environment_to_domain(self, domain_uuid: str, environment_uuid: str) -> str:
        """
        将环境添加到域

        Args:
            domain_uuid: 域UUID
            environment_uuid: 环境UUID

        Returns:
            关联UUID
        """
        if self.debug:
            print(f"🐛 [DEBUG] 添加环境到域")

        relation_uuid = str(uuid.uuid4())
        now = datetime.now().isoformat()

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO domain_environments 
                    (uuid, domain_uuid, environment_uuid, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (relation_uuid, domain_uuid, environment_uuid, now))

            if self.debug:
                print(f"🐛 [DEBUG] ✓ 环境添加到域成功")

            return relation_uuid
        except sqlite3.IntegrityError:
            # 如果已存在关联，返回空字符串
            if self.debug:
                print(f"🐛 [DEBUG] 环境已在域中")
            return ""

    def remove_environment_from_domain(self, domain_uuid: str, environment_uuid: str) -> bool:
        """
        从域中移除环境

        Args:
            domain_uuid: 域UUID
            environment_uuid: 环境UUID

        Returns:
            是否移除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM domain_environments 
                    WHERE domain_uuid = ? AND environment_uuid = ?
                ''', (domain_uuid, environment_uuid))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"✗ 从域中移除环境时出错: {e}")
            return False

    def get_domain_environments(self, domain_uuid: str) -> List[Dict[str, Any]]:
        """
        获取域中的所有环境

        Args:
            domain_uuid: 域UUID

        Returns:
            环境列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.* FROM environment_descriptions e
                INNER JOIN domain_environments de ON e.uuid = de.environment_uuid
                WHERE de.domain_uuid = ?
                ORDER BY e.name
            ''', (domain_uuid,))
            return [dict(row) for row in cursor.fetchall()]

    def get_environment_domains(self, environment_uuid: str) -> List[Dict[str, Any]]:
        """
        获取环境所属的所有域

        Args:
            environment_uuid: 环境UUID

        Returns:
            域列表
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT d.* FROM environment_domains d
                INNER JOIN domain_environments de ON d.uuid = de.domain_uuid
                WHERE de.environment_uuid = ?
                ORDER BY d.name
            ''', (environment_uuid,))
            return [dict(row) for row in cursor.fetchall()]

    def is_environment_in_domain(self, environment_uuid: str, domain_uuid: str) -> bool:
        """
        检查环境是否在域中

        Args:
            environment_uuid: 环境UUID
            domain_uuid: 域UUID

        Returns:
            是否在域中
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM domain_environments
                WHERE domain_uuid = ? AND environment_uuid = ?
            ''', (domain_uuid, environment_uuid))
            result = cursor.fetchone()
            return result['count'] > 0

    # ==================== 生活状态日快照方法（P1：LifeStateManager）====================

    def upsert_life_state_daily(self, date: str, energy: float, mood: str,
                                 state_title: str, health: str,
                                 conditions: list, transition_options: list,
                                 energy_delta: float = 0.0) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO life_state_daily
                    (date, energy, mood, state_title, health,
                     conditions_json, transition_options_json,
                     energy_delta, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        energy=excluded.energy,
                        mood=excluded.mood,
                        state_title=excluded.state_title,
                        health=excluded.health,
                        conditions_json=excluded.conditions_json,
                        transition_options_json=excluded.transition_options_json,
                        energy_delta=excluded.energy_delta,
                        updated_at=excluded.updated_at
                ''', (date, energy, mood, state_title, health,
                      json.dumps(conditions, ensure_ascii=False),
                      json.dumps(transition_options, ensure_ascii=False),
                      energy_delta, datetime.now().isoformat(),
                      datetime.now().isoformat()))
                return True
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ upsert_life_state_daily 出错: {e}")
            return False

    def get_life_state_daily(self, date: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM life_state_daily WHERE date = ?', (date,))
                row = cursor.fetchone()
                if not row:
                    return None
                record = dict(row)
                record['conditions'] = json.loads(record.pop('conditions_json') or '[]')
                record['transition_options'] = json.loads(record.pop('transition_options_json') or '[]')
                return record
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_life_state_daily 出错: {e}")
            return None

    # ==================== 梦境记录方法（P1：DreamDiaryManager）====================

    def insert_dream_record(self, date: str, dream_type: str, content: str,
                            afterglow: str = "", label: str = "",
                            mood: str = "", energy_delta: float = 0.0,
                            duration_hours: float = 7.0,
                            weather: Optional[Dict[str, Any]] = None) -> str:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                dream_uuid = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO dream_records
                    (uuid, date, dream_type, content, afterglow, label,
                     mood, energy_delta, duration_hours, weather_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (dream_uuid, date, dream_type, content, afterglow, label,
                      mood, energy_delta, duration_hours,
                      json.dumps(weather or {}, ensure_ascii=False),
                      datetime.now().isoformat()))
                return dream_uuid
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ insert_dream_record 出错: {e}")
            return ""

    def get_recent_dreams(self, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM dream_records
                    ORDER BY date DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
                rows = [dict(row) for row in cursor.fetchall()]
                for r in rows:
                    r['weather'] = json.loads(r.pop('weather_json') or '{}')
                return rows
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_recent_dreams 出错: {e}")
            return []

    def get_dream_fragments_pool(self, limit: int = 50) -> List[str]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT content FROM dream_records
                    ORDER BY date DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
                return [row['content'] for row in cursor.fetchall()]
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_dream_fragments_pool 出错: {e}")
            return []

    # ==================== 日记条目方法（P1：DreamDiaryManager）====================

    def insert_diary_entry(self, date: str, body: str, title: str = "",
                           mood: str = "", tags: Optional[List[str]] = None,
                           related_entities: Optional[List[str]] = None) -> str:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                entry_uuid = str(uuid.uuid4())
                word_count = len(body)
                cursor.execute('''
                    INSERT INTO diary_entries
                    (uuid, date, title, body, mood, tags_json,
                     related_entities_json, word_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entry_uuid, date, title, body, mood,
                      json.dumps(tags or [], ensure_ascii=False),
                      json.dumps(related_entities or [], ensure_ascii=False),
                      word_count, datetime.now().isoformat()))
                return entry_uuid
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ insert_diary_entry 出错: {e}")
            return ""

    def get_recent_diaries(self, limit: int = 3) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM diary_entries
                    ORDER BY date DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
                rows = [dict(row) for row in cursor.fetchall()]
                for r in rows:
                    r['tags'] = json.loads(r.pop('tags_json') or '[]')
                    r['related_entities'] = json.loads(r.pop('related_entities_json') or '[]')
                return rows
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_recent_diaries 出错: {e}")
            return []

    # ==================== 未完话题方法（P2：OpenLoopTracker）====================

    def insert_open_loop(self, topic: str, context: str = "",
                         related_keywords: Optional[List[str]] = None,
                         raised_at: Optional[str] = None) -> str:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                loop_uuid = str(uuid.uuid4())
                now_iso = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO open_loops
                    (uuid, topic, status, raised_at, related_keywords_json,
                     context, mention_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                ''', (loop_uuid, topic, 'open',
                      raised_at or now_iso,
                      json.dumps(related_keywords or [], ensure_ascii=False),
                      context, now_iso, now_iso))
                return loop_uuid
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ insert_open_loop 出错: {e}")
            return ""

    def get_open_loops(self, status: str = "open", limit: int = 20) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM open_loops
                    WHERE status = ?
                    ORDER BY raised_at DESC
                    LIMIT ?
                ''', (status, limit))
                rows = [dict(row) for row in cursor.fetchall()]
                for r in rows:
                    r['related_keywords'] = json.loads(r.pop('related_keywords_json') or '[]')
                return rows
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_open_loops 出错: {e}")
            return []

    def resolve_open_loop(self, loop_uuid: str) -> bool:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE open_loops
                    SET status = 'resolved',
                        resolved_at = ?,
                        updated_at = ?
                    WHERE uuid = ?
                ''', (datetime.now().isoformat(),
                      datetime.now().isoformat(), loop_uuid))
                return cursor.rowcount > 0
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ resolve_open_loop 出错: {e}")
            return False

    def find_matching_open_loop(self, keyword: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM open_loops WHERE status = ?',
                               ('open',))
                rows = [dict(row) for row in cursor.fetchall()]
                kw = (keyword or '').lower()
                for r in rows:
                    topic = (r.get('topic') or '').lower()
                    if kw and (kw in topic or topic in kw):
                        try:
                            r['related_keywords'] = json.loads(r.pop('related_keywords_json') or '[]')
                        except Exception:
                            r['related_keywords'] = []
                        return r
                return None
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ find_matching_open_loop 出错: {e}")
            return None

    # ==================== P3: Creative Project CRUD ====================

    def create_creative_project(self, project: Dict[str, Any]) -> str:
        try:
            project_uuid = project.get('uuid') or str(uuid.uuid4())
            now_iso = datetime.now().isoformat()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO creative_projects
                    (uuid, title, work_type, premise, tone, point_of_view,
                     target_chars, current_chars, status, inspiration_source,
                     outline_json, characters_json, draft_chunks_json,
                     next_advance_at, last_advanced_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_uuid,
                    project.get('title', '未命名'),
                    project.get('work_type', '短篇'),
                    project.get('premise', ''),
                    project.get('tone', ''),
                    project.get('point_of_view', '第一人称'),
                    int(project.get('target_chars', 5000)),
                    int(project.get('current_chars', 0)),
                    project.get('status', 'drafting'),
                    project.get('inspiration_source', ''),
                    json.dumps(project.get('outline', []), ensure_ascii=False),
                    json.dumps(project.get('characters', []), ensure_ascii=False),
                    json.dumps(project.get('draft_chunks', []), ensure_ascii=False),
                    project.get('next_advance_at'),
                    project.get('last_advanced_at'),
                    now_iso, now_iso,
                ))
            return project_uuid
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ create_creative_project 出错: {e}")
            return ""

    def update_creative_project(self, project_uuid: str,
                                 updates: Dict[str, Any]) -> bool:
        try:
            fields_map = {
                'title': 'title', 'work_type': 'work_type',
                'premise': 'premise', 'tone': 'tone',
                'point_of_view': 'point_of_view',
                'target_chars': 'target_chars', 'current_chars': 'current_chars',
                'status': 'status', 'inspiration_source': 'inspiration_source',
                'next_advance_at': 'next_advance_at',
                'last_advanced_at': 'last_advanced_at',
            }
            json_map = {
                'outline': 'outline_json',
                'characters': 'characters_json',
                'draft_chunks': 'draft_chunks_json',
            }
            sets = []
            values: List[Any] = []
            for k, v in updates.items():
                if k in fields_map:
                    sets.append(f'{fields_map[k]} = ?')
                    values.append(v)
                elif k in json_map:
                    sets.append(f'{json_map[k]} = ?')
                    values.append(json.dumps(v, ensure_ascii=False))
            if not sets:
                return False
            sets.append('updated_at = ?')
            values.append(datetime.now().isoformat())
            values.append(project_uuid)
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f'UPDATE creative_projects SET {", ".join(sets)} WHERE uuid = ?',
                    values,
                )
                return cursor.rowcount > 0
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ update_creative_project 出错: {e}")
            return False

    def get_creative_project(self, project_uuid: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM creative_projects WHERE uuid = ?',
                               (project_uuid,))
                row = cursor.fetchone()
                if not row:
                    return None
                data = dict(row)
                for json_k in ('outline_json', 'characters_json', 'draft_chunks_json'):
                    try:
                        data[json_k.replace('_json', '')] = json.loads(data.get(json_k) or '[]')
                    except Exception:
                        data[json_k.replace('_json', '')] = []
                return data
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_creative_project 出错: {e}")
            return None

    def list_creative_projects(self, status: Optional[str] = None,
                               limit: int = 20) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if status:
                    cursor.execute('''
                        SELECT * FROM creative_projects
                        WHERE status = ?
                        ORDER BY created_at DESC LIMIT ?
                    ''', (status, limit))
                else:
                    cursor.execute('''
                        SELECT * FROM creative_projects
                        ORDER BY created_at DESC LIMIT ?
                    ''', (limit,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ list_creative_projects 出错: {e}")
            return []

    def upsert_story_bible(self, project_uuid: str, bible: Dict[str, Any]) -> bool:
        try:
            now_iso = datetime.now().isoformat()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO creative_story_bibles
                    (project_uuid, mainline_direction, active_themes_json,
                     unresolved_threads_json, resolved_threads_json,
                     important_facts_json, next_direction, recent_keywords_json,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_uuid,
                    bible.get('mainline_direction', ''),
                    json.dumps(bible.get('active_themes', []), ensure_ascii=False),
                    json.dumps(bible.get('unresolved_threads', []), ensure_ascii=False),
                    json.dumps(bible.get('resolved_threads', []), ensure_ascii=False),
                    json.dumps(bible.get('important_facts', []), ensure_ascii=False),
                    bible.get('next_direction', ''),
                    json.dumps(bible.get('recent_keywords', []), ensure_ascii=False),
                    now_iso, now_iso,
                ))
                return True
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ upsert_story_bible 出错: {e}")
            return False

    def get_story_bible(self, project_uuid: str) -> Optional[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT * FROM creative_story_bibles WHERE project_uuid = ?',
                    (project_uuid,))
                row = cursor.fetchone()
                if not row:
                    return None
                data = dict(row)
                for k in ('active_themes_json', 'unresolved_threads_json',
                          'resolved_threads_json', 'important_facts_json',
                          'recent_keywords_json'):
                    try:
                        data[k.replace('_json', '')] = json.loads(data.get(k) or '[]')
                    except Exception:
                        data[k.replace('_json', '')] = []
                return data
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_story_bible 出错: {e}")
            return None

    def add_creative_memory(self, project_uuid: str, memory_type: str,
                            content: str, importance: float = 0.5) -> str:
        try:
            mem_uuid = str(uuid.uuid4())
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO creative_memory_pool
                    (uuid, project_uuid, memory_type, content, importance, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (mem_uuid, project_uuid, memory_type, content,
                      float(importance), datetime.now().isoformat()))
                return mem_uuid
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ add_creative_memory 出错: {e}")
            return ""

    def get_creative_memory_pool(self, project_uuid: str, limit: int = 50) -> List[Dict[str, Any]]:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM creative_memory_pool
                    WHERE project_uuid = ?
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                ''', (project_uuid, limit))
                return [dict(r) for r in cursor.fetchall()]
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ get_creative_memory_pool 出错: {e}")
            return []

    def prune_creative_memory_pool(self, project_uuid: str,
                                   keep_max: int = 50) -> int:
        """保留高 importance + 最新的 keep_max 条；返回删除条数。"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT uuid FROM creative_memory_pool
                    WHERE project_uuid = ?
                    ORDER BY importance DESC, created_at DESC
                ''', (project_uuid,))
                rows = [r[0] for r in cursor.fetchall()]
                if len(rows) <= keep_max:
                    return 0
                to_delete = rows[keep_max:]
                cursor.executemany(
                    'DELETE FROM creative_memory_pool WHERE uuid = ?',
                    [(u,) for u in to_delete],
                )
                return len(to_delete)
        except Exception as e:
            if self.debug:
                print(f"🐛 [DEBUG] ✗ prune_creative_memory_pool 出错: {e}")
            return 0

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

    # ==================== v3.1.0: ChatSessionRepository 单例 ====================
    _chat_session_repo: Optional["ChatSessionRepository"] = None  # type: ignore[name-defined]

    def get_chat_session_repository(self) -> "ChatSessionRepository":  # type: ignore[name-defined]
        """
        获取 ChatSessionRepository 单例（懒加载）。

        为什么不放模块顶层：避免循环 import
        (database_manager → chat_session_repository → database_manager)。
        """
        if self._chat_session_repo is None:
            from src.core.chat_session_repository import ChatSessionRepository
            self._chat_session_repo = ChatSessionRepository(self)
        return self._chat_session_repo


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

