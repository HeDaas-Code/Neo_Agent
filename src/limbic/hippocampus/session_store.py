"""
SessionStore - 海马体中的会话存储模块。

负责聊天会话(chat_sessions)与消息(chat_messages)的持久化，
对应 v3.1.0 的 ChatSessionRepository，迁移到 v4.0 神经系统架构的 limbic/hippocampus 层。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class SessionStore:
    """
    聊天会话仓库。

    Args:
        db_manager: ``DatabaseManager`` 实例。
    """

    def __init__(self, db_manager: Any) -> None:
        self._db = db_manager

    # ------------------------------------------------------------------
    # 内部 helper
    # ------------------------------------------------------------------
    def _row(self, row: Any) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return dict(row)

    # ------------------------------------------------------------------
    # Session 操作
    # ------------------------------------------------------------------
    def create(self, user_id: str, title: str = "新会话") -> int:
        """
        创建新会话并返回 session_id。

        Args:
            user_id: 归属用户标识
            title: 初始标题（默认 "新会话"）

        Returns:
            新插入行的自增 id
        """
        now = time.time()
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO chat_sessions (user_id, title, created_at, updated_at, message_count)
                VALUES (?, ?, ?, ?, 0)
                ''',
                (user_id, title, now, now),
            )
            new_id = cursor.lastrowid
        return int(new_id) if new_id is not None else 0

    def list(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出用户会话，按 updated_at 倒序。

        Args:
            user_id: 用户标识
            limit: 最多返回条数
            offset: 起始偏移

        Returns:
            session 字典列表
        """
        try:
            safe_limit = max(1, min(int(limit), 200))
        except (TypeError, ValueError):
            safe_limit = 50
        try:
            safe_offset = max(0, int(offset))
        except (TypeError, ValueError):
            safe_offset = 0

        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT * FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                ''',
                (user_id, safe_limit, safe_offset),
            )
            rows = cursor.fetchall()
        return [self._row(r) for r in rows]

    def get(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        按 id 查单条 session。

        Args:
            session_id: 会话 id

        Returns:
            session 字典或 None
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chat_sessions WHERE id = ?', (int(session_id),))
            row = cursor.fetchone()
        return self._row(row)

    def delete(self, session_id: int) -> bool:
        """
        删除 session（依赖 ON DELETE CASCADE 自动删 messages）。

        Args:
            session_id: 会话 id

        Returns:
            是否实际删除了行
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chat_sessions WHERE id = ?', (int(session_id),))
            return cursor.rowcount > 0

    def update_title(self, session_id: int, title: str) -> bool:
        """
        更新会话标题（同步刷新 updated_at）。

        Args:
            session_id: 会话 id
            title: 新标题

        Returns:
            是否实际更新了行
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE chat_sessions
                SET title = ?, updated_at = ?
                WHERE id = ?
                ''',
                (title, time.time(), int(session_id)),
            )
            return cursor.rowcount > 0

    def touch(self, session_id: int) -> None:
        """
        刷新 session 的 ``updated_at`` + 重新计算 ``message_count``。
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE chat_sessions
                SET updated_at = ?,
                    message_count = (
                        SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
                    )
                WHERE id = ?
                ''',
                (time.time(), int(session_id), int(session_id)),
            )

    # ------------------------------------------------------------------
    # Message 操作
    # ------------------------------------------------------------------
    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        emotion_json: Optional[str] = None,
        conn_id: Optional[str] = None,
    ) -> int:
        """
        插入一条消息 + 自动 touch session。

        Args:
            session_id: 归属会话 id
            role: 角色（user / assistant / system）
            content: 文本内容
            emotion_json: 序列化后的情感数据（可空）
            conn_id: WebSocket 连接 id（可空）

        Returns:
            新插入 message 的自增 id
        """
        now = time.time()
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO chat_messages
                    (session_id, role, content, emotion_json, conn_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (int(session_id), role, content, emotion_json, conn_id, now),
            )
            new_id = cursor.lastrowid
            # 自动维护 session 元信息
            cursor.execute(
                '''
                UPDATE chat_sessions
                SET updated_at = ?,
                    message_count = (
                        SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
                    )
                WHERE id = ?
                ''',
                (now, int(session_id), int(session_id)),
            )
        return int(new_id) if new_id is not None else 0

    def update_message_emotion(self, message_id: int, emotion_json: str) -> bool:
        """
        异步更新某条消息的 emotion_json（emotion_update 事件触发时调用）。

        Args:
            message_id: 消息 id
            emotion_json: 序列化后的情感数据

        Returns:
            是否实际更新了行
        """
        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE chat_messages
                SET emotion_json = ?
                WHERE id = ?
                ''',
                (emotion_json, int(message_id)),
            )
            return cursor.rowcount > 0

    def list_messages(
        self,
        session_id: int,
        limit: int = 200,
        before_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        拉取会话的消息列表，按 id 升序。

        Args:
            session_id: 会话 id
            limit: 最多返回条数
            before_id: 可选；仅返回 id < before_id 的消息（向后翻页）

        Returns:
            message 字典列表
        """
        try:
            safe_limit = max(1, min(int(limit), 1000))
        except (TypeError, ValueError):
            safe_limit = 200

        with self._db.get_connection() as conn:
            cursor = conn.cursor()
            if before_id is not None:
                cursor.execute(
                    '''
                    SELECT * FROM chat_messages
                    WHERE session_id = ? AND id < ?
                    ORDER BY id ASC
                    LIMIT ?
                    ''',
                    (int(session_id), int(before_id), safe_limit),
                )
            else:
                cursor.execute(
                    '''
                    SELECT * FROM chat_messages
                    WHERE session_id = ?
                    ORDER BY id ASC
                    LIMIT ?
                    ''',
                    (int(session_id), safe_limit),
                )
            rows = cursor.fetchall()
        return [self._row(r) for r in rows]


__all__ = ["SessionStore"]
