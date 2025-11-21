"""
笔记管理模块
提供笔记的创建、编辑、查询和分类功能
"""

import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class Note:
    """笔记条目"""

    def __init__(
        self,
        note_id: str = None,
        title: str = "",
        content: str = "",
        tags: List[str] = None,
        category: str = "",
        is_pinned: bool = False,
        created_at: datetime = None,
        updated_at: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        """
        初始化笔记

        Args:
            note_id: 笔记ID
            title: 标题
            content: 内容
            tags: 标签列表
            category: 分类
            is_pinned: 是否置顶
            created_at: 创建时间
            updated_at: 更新时间
            metadata: 附加元数据
        """
        self.note_id = note_id or str(uuid.uuid4())
        self.title = title
        self.content = content
        self.tags = tags or []
        self.category = category
        self.is_pinned = is_pinned
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'note_id': self.note_id,
            'title': self.title,
            'content': self.content,
            'tags': self.tags,
            'category': self.category,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """从字典创建笔记"""
        return cls(
            note_id=data.get('note_id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            tags=data.get('tags', []),
            category=data.get('category', ''),
            is_pinned=data.get('is_pinned', False),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat())),
            metadata=data.get('metadata', {})
        )

    def update_content(self, content: str):
        """更新内容并刷新更新时间"""
        self.content = content
        self.updated_at = datetime.now()


class NoteManager:
    """
    笔记管理器
    负责笔记的创建、查询、更新和删除
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化笔记管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager or DatabaseManager()
        self._init_database()

        debug_logger.log_info('NoteManager', '初始化笔记管理器')

    def _init_database(self):
        """初始化数据库表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS notes (
            note_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            content TEXT,
            tags TEXT,
            category TEXT,
            is_pinned INTEGER,
            created_at TEXT,
            updated_at TEXT,
            metadata TEXT
        )
        """
        self.db_manager.execute_query(create_table_sql)
        debug_logger.log_info('NoteManager', '数据库表初始化完成')

    def add_note(self, note: Note) -> bool:
        """
        添加笔记

        Args:
            note: 笔记对象

        Returns:
            是否添加成功
        """
        try:
            insert_sql = """
            INSERT INTO notes 
            (note_id, title, content, tags, category, is_pinned, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            self.db_manager.execute_query(
                insert_sql,
                (
                    note.note_id,
                    note.title,
                    note.content,
                    json.dumps(note.tags, ensure_ascii=False),
                    note.category,
                    1 if note.is_pinned else 0,
                    note.created_at.isoformat(),
                    note.updated_at.isoformat(),
                    json.dumps(note.metadata, ensure_ascii=False)
                )
            )

            debug_logger.log_info('NoteManager', '添加笔记成功', {
                'note_id': note.note_id,
                'title': note.title
            })
            return True

        except Exception as e:
            debug_logger.log_error('NoteManager', '添加笔记失败', e)
            return False

    def get_note(self, note_id: str) -> Optional[Note]:
        """
        获取指定笔记

        Args:
            note_id: 笔记ID

        Returns:
            笔记对象或None
        """
        try:
            query_sql = "SELECT * FROM notes WHERE note_id = ?"
            result = self.db_manager.fetch_one(query_sql, (note_id,))

            if result:
                return self._row_to_note(result)
            return None

        except Exception as e:
            debug_logger.log_error('NoteManager', '获取笔记失败', e)
            return None

    def get_all_notes(self, order_by: str = 'updated_at') -> List[Note]:
        """
        获取所有笔记

        Args:
            order_by: 排序字段（updated_at, created_at, title）

        Returns:
            笔记列表
        """
        try:
            # 置顶的笔记排在前面
            query_sql = f"""
            SELECT * FROM notes 
            ORDER BY is_pinned DESC, {order_by} DESC
            """
            results = self.db_manager.fetch_all(query_sql)

            return [self._row_to_note(row) for row in results]

        except Exception as e:
            debug_logger.log_error('NoteManager', '获取笔记列表失败', e)
            return []

    def get_notes_by_category(self, category: str) -> List[Note]:
        """
        按分类获取笔记

        Args:
            category: 分类名称

        Returns:
            笔记列表
        """
        try:
            query_sql = """
            SELECT * FROM notes 
            WHERE category = ?
            ORDER BY is_pinned DESC, updated_at DESC
            """
            results = self.db_manager.fetch_all(query_sql, (category,))

            return [self._row_to_note(row) for row in results]

        except Exception as e:
            debug_logger.log_error('NoteManager', '按分类获取笔记失败', e)
            return []

    def get_notes_by_tag(self, tag: str) -> List[Note]:
        """
        按标签获取笔记

        Args:
            tag: 标签名称

        Returns:
            笔记列表
        """
        try:
            # SQLite的JSON查询可能需要特殊处理
            all_notes = self.get_all_notes()
            return [note for note in all_notes if tag in note.tags]

        except Exception as e:
            debug_logger.log_error('NoteManager', '按标签获取笔记失败', e)
            return []

    def search_notes(self, keyword: str) -> List[Note]:
        """
        搜索笔记

        Args:
            keyword: 搜索关键词

        Returns:
            笔记列表
        """
        try:
            query_sql = """
            SELECT * FROM notes 
            WHERE title LIKE ? OR content LIKE ?
            ORDER BY is_pinned DESC, updated_at DESC
            """
            search_pattern = f"%{keyword}%"
            results = self.db_manager.fetch_all(query_sql, (search_pattern, search_pattern))

            return [self._row_to_note(row) for row in results]

        except Exception as e:
            debug_logger.log_error('NoteManager', '搜索笔记失败', e)
            return []

    def update_note(self, note: Note) -> bool:
        """
        更新笔记

        Args:
            note: 笔记对象

        Returns:
            是否更新成功
        """
        try:
            # 自动更新更新时间
            note.updated_at = datetime.now()

            update_sql = """
            UPDATE notes 
            SET title = ?, content = ?, tags = ?, category = ?, 
                is_pinned = ?, updated_at = ?, metadata = ?
            WHERE note_id = ?
            """
            self.db_manager.execute_query(
                update_sql,
                (
                    note.title,
                    note.content,
                    json.dumps(note.tags, ensure_ascii=False),
                    note.category,
                    1 if note.is_pinned else 0,
                    note.updated_at.isoformat(),
                    json.dumps(note.metadata, ensure_ascii=False),
                    note.note_id
                )
            )

            debug_logger.log_info('NoteManager', '更新笔记成功', {
                'note_id': note.note_id
            })
            return True

        except Exception as e:
            debug_logger.log_error('NoteManager', '更新笔记失败', e)
            return False

    def delete_note(self, note_id: str) -> bool:
        """
        删除笔记

        Args:
            note_id: 笔记ID

        Returns:
            是否删除成功
        """
        try:
            delete_sql = "DELETE FROM notes WHERE note_id = ?"
            self.db_manager.execute_query(delete_sql, (note_id,))

            debug_logger.log_info('NoteManager', '删除笔记成功', {
                'note_id': note_id
            })
            return True

        except Exception as e:
            debug_logger.log_error('NoteManager', '删除笔记失败', e)
            return False

    def toggle_pin(self, note_id: str) -> bool:
        """
        切换笔记置顶状态

        Args:
            note_id: 笔记ID

        Returns:
            是否操作成功
        """
        note = self.get_note(note_id)
        if note:
            note.is_pinned = not note.is_pinned
            return self.update_note(note)
        return False

    def get_all_categories(self) -> List[str]:
        """
        获取所有分类

        Returns:
            分类列表
        """
        try:
            query_sql = "SELECT DISTINCT category FROM notes WHERE category != ''"
            results = self.db_manager.fetch_all(query_sql)

            return [row[0] for row in results]

        except Exception as e:
            debug_logger.log_error('NoteManager', '获取分类列表失败', e)
            return []

    def get_all_tags(self) -> List[str]:
        """
        获取所有标签

        Returns:
            标签列表
        """
        try:
            all_notes = self.get_all_notes()
            tags_set = set()

            for note in all_notes:
                tags_set.update(note.tags)

            return sorted(list(tags_set))

        except Exception as e:
            debug_logger.log_error('NoteManager', '获取标签列表失败', e)
            return []

    def _row_to_note(self, row: tuple) -> Note:
        """
        将数据库行转换为Note对象

        Args:
            row: 数据库查询结果行

        Returns:
            Note对象
        """
        return Note(
            note_id=row[0],
            title=row[1],
            content=row[2],
            tags=json.loads(row[3]) if row[3] else [],
            category=row[4],
            is_pinned=bool(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7]),
            metadata=json.loads(row[8]) if row[8] else {}
        )

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取笔记统计信息

        Returns:
            统计信息字典
        """
        all_notes = self.get_all_notes()

        stats = {
            'total': len(all_notes),
            'pinned': len([n for n in all_notes if n.is_pinned]),
            'categories': len(self.get_all_categories()),
            'tags': len(self.get_all_tags()),
            'recent_7_days': len([
                n for n in all_notes
                if (datetime.now() - n.created_at).days <= 7
            ])
        }

        return stats
