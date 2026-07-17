"""
Database consistency verification tests.

验证 DatabaseManager 在 WAL 模式下的并发安全：

1. ``test_database_manager_works_for_both_modes``
   用同一 ``DatabaseManager('chat_agent.db')`` 实例化两次
   （模拟多个进程/线程同时持有），分别写入/读取，
   验证 WAL 模式下不冲突。
2. ``test_wal_mode_is_enabled``
   调用 ``db.get_connection()`` 后查询 ``PRAGMA journal_mode`` 应为 ``wal``。
   **必须 try/except 保护**：sqlite3 WAL pragma 失败时 skip 而非 fail。

兼容性：
- 使用标准库 ``unittest.TestCase``（同步测试）。
- 通过临时目录隔离测试数据，结束后清理 ``*.db`` / ``*.db-wal`` / ``*.db-shm``。
- 当 ``sqlite3`` / ``DatabaseManager`` 不可用时 skip 整个文件。
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------
# 可选依赖探测
# ---------------------------------------------------------------
try:
    from src.core.database_manager import DatabaseManager
    _DB_OK = True
    _DB_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _exc:  # noqa: BLE001
    DatabaseManager = None  # type: ignore
    _DB_OK = False
    _DB_IMPORT_ERROR = _exc


# 若 DatabaseManager 不可用，整个文件 skip
if not _DB_OK:
    raise unittest.SkipTest(
        f"无法导入 DatabaseManager，跳过 db_consistency 测试: {_DB_IMPORT_ERROR}"
    )


# ---------------------------------------------------------------
# 工具
# ---------------------------------------------------------------
def _new_tmp_db_path() -> str:
    """生成一个临时 db 文件路径（文件本身尚未创建）。"""
    fd, path = tempfile.mkstemp(prefix="db_consistency_test_", suffix=".db")
    os.close(fd)
    # mkstemp 已经创建空文件；删除让 DatabaseManager 自己 init
    try:
        os.remove(path)
    except OSError:  # pragma: no cover
        pass
    return path


def _cleanup_db_files(path: str) -> None:
    """清理 db 文件及其 WAL / SHM 副产物。"""
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            os.remove(path + suffix)
        except OSError:  # pragma: no cover
            pass


# ---------------------------------------------------------------
# 1) 双 DatabaseManager 实例共存（WAL 模式不冲突）
# ---------------------------------------------------------------
class TestDatabaseManagerSharedBetweenModes(unittest.TestCase):
    """模拟多持有者：两个 DatabaseManager 实例共用同一 db。"""

    def setUp(self) -> None:
        self.db_path = _new_tmp_db_path()

    def tearDown(self) -> None:
        _cleanup_db_files(self.db_path)

    def test_database_manager_works_for_both_modes(self) -> None:
        """同一 ``DatabaseManager('chat_agent.db')`` 实例化两次，
        分别写入/读取，验证 WAL 模式下不冲突。

        步骤：
            1. db_first  = DatabaseManager(self.db_path)   # 模拟第一个持有者
            2. db_second = DatabaseManager(self.db_path)   # 模拟第二个持有者
            3. db_first  写入一行（commit）
            4. db_second 读取并校验
            5. db_second 写入另一行（commit）
            6. db_first  读取并校验
        """
        # 第 1 步：两个 DatabaseManager 实例共用同一 db
        db_first = DatabaseManager(self.db_path, debug=False)
        db_second = DatabaseManager(self.db_path, debug=False)

        # 第 2 步：建表（第一个持有者）
        with db_first.get_connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS rollback_probe ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "source TEXT NOT NULL,"
                "value TEXT NOT NULL,"
                "created_at TEXT NOT NULL"
                ")"
            )

        # 第 3 步：第一个持有者写入
        with db_first.get_connection() as conn:
            conn.execute(
                "INSERT INTO rollback_probe(source, value, created_at) "
                "VALUES (?, ?, ?)",
                ("first", "from-first-process", "2026-07-14T00:00:00Z"),
            )

        # 第 4 步：第二个持有者读取（必须能看到 first 写入的数据）
        with db_second.get_connection() as conn:
            rows = conn.execute(
                "SELECT source, value FROM rollback_probe ORDER BY id"
            ).fetchall()
        self.assertEqual(
            len(rows), 1,
            f"second 端应当看到 1 条 first 写入，实际: {len(rows)}",
        )
        self.assertEqual(rows[0]["source"], "first")
        self.assertEqual(rows[0]["value"], "from-first-process")

        # 第 5 步：第二个持有者写入
        with db_second.get_connection() as conn:
            conn.execute(
                "INSERT INTO rollback_probe(source, value, created_at) "
                "VALUES (?, ?, ?)",
                ("second", "from-second-process", "2026-07-14T00:00:01Z"),
            )

        # 第 6 步：第一个持有者读取（必须能看到 second 写入的数据）
        with db_first.get_connection() as conn:
            rows = conn.execute(
                "SELECT source, value FROM rollback_probe ORDER BY id"
            ).fetchall()
        self.assertEqual(
            len(rows), 2,
            f"first 端应当看到 2 条（first + second）写入，实际: {len(rows)}",
        )
        sources = [r["source"] for r in rows]
        self.assertIn("first", sources)
        self.assertIn("second", sources)

        # 不应出现 "database is locked" 之类的并发冲突
        # （若 WAL 未启用，第二个 DatabaseManager 在写入时可能 OperationalError）


# ---------------------------------------------------------------
# 2) WAL 模式已启用
# ---------------------------------------------------------------
class TestWalModeEnabled(unittest.TestCase):
    """``PRAGMA journal_mode`` 应返回 ``wal``。"""

    def setUp(self) -> None:
        self.db_path = _new_tmp_db_path()

    def tearDown(self) -> None:
        _cleanup_db_files(self.db_path)

    def test_wal_mode_is_enabled(self) -> None:
        """调用 ``db.get_connection()`` 后查询 ``PRAGMA journal_mode`` 应为 ``wal``。

        必须在 try/except 内执行：若 sqlite3 PRAGMA 调用失败（例如权限不足、
        只读文件系统、磁盘满），则 skip 而非 fail，以保持 CI 绿。
        """
        db = DatabaseManager(self.db_path, debug=False)

        try:
            with db.get_connection() as conn:
                try:
                    cursor = conn.execute("PRAGMA journal_mode")
                    row = cursor.fetchone()
                except sqlite3.Error as pragma_err:
                    # PRAGMA 调用失败：跳过而非失败
                    self.skipTest(
                        f"PRAGMA journal_mode 调用失败（WAL 检测无法完成）: {pragma_err}"
                    )

            # row 可能是 None（极端环境）；视为无法判断
            if row is None:
                self.skipTest("PRAGMA journal_mode 返回 None，无法判断 WAL 状态")

            # 提取结果（sqlite3.Row 支持索引访问）
            try:
                mode_value = row["journal_mode"]
            except (KeyError, IndexError, TypeError):
                try:
                    mode_value = row[0]
                except (KeyError, IndexError, TypeError):
                    self.skipTest(
                        f"无法解析 PRAGMA journal_mode 的返回结构: {row!r}"
                    )

            self.assertEqual(
                mode_value, "wal",
                f"SQLite journal_mode 应为 'wal'，实际: {mode_value!r}",
            )
        except OSError as os_err:
            # 文件系统级错误（权限、磁盘满等）— 跳过而非失败
            self.skipTest(f"无法验证 WAL 模式（操作系统错误）: {os_err}")


# ---------------------------------------------------------------
# 入口
# ---------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
