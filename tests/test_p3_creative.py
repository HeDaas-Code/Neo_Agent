"""
测试 P3 阶段：CreativeProjectManager
环境无 pytest / 缺依赖时，本文件可作为 AST 解析与 import 路径的契约检查。
"""

import os
import sys
import unittest
import tempfile
import types
from datetime import datetime, timedelta
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 注入最小 dotenv / requests stub
try:
    import dotenv  # noqa: F401
except ImportError:
    _dotenv_stub = types.ModuleType("dotenv")
    _dotenv_stub.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = _dotenv_stub
try:
    import requests  # noqa: F401
except ImportError:
    _requests_stub = types.ModuleType("requests")
    _requests_stub.post = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stub"))
    sys.modules["requests"] = _requests_stub


class TestCreativeProjectManagerContract(unittest.TestCase):
    """CreativeProjectManager API 契约检查"""

    def test_class_and_methods_exist(self):
        from src.core.creative_writer import CreativeProjectManager
        required = [
            'maybe_start_creative_project', 'maybe_advance_creative_projects',
            'generate_creative_chunk', 'generate_creative_project',
            'get_or_create_story_bible', 'get_or_create_memory_pool',
            'creative_inspiration_source', 'get_finished_projects',
        ]
        for name in required:
            self.assertTrue(hasattr(CreativeProjectManager, name),
                            f'CreativeProjectManager 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import creative_writer as cw
        self.assertFalse(cw.ENABLE_CREATIVE_WRITER,
                         'ENABLE_CREATIVE_WRITER 默认应为关闭')

    def test_template_constants(self):
        from src.core.creative_writer import (
            DEFAULT_CREATIVE_PROJECT_TEMPLATE, CREATIVE_STORY_BIBLE_TEMPLATE,
        )
        # 项目模板关键字段
        for key in ('title', 'work_type', 'premise', 'tone', 'point_of_view',
                    'target_chars', 'current_chars', 'status', 'draft_chunks',
                    'story_bible', 'creative_memory_pool', 'outline',
                    'characters', 'next_advance_at'):
            self.assertIn(key, DEFAULT_CREATIVE_PROJECT_TEMPLATE,
                          f'项目模板缺少字段: {key}')
        # Story Bible 关键字段
        for key in ('mainline_direction', 'active_themes',
                    'unresolved_threads', 'resolved_threads',
                    'important_facts', 'next_direction', 'recent_keywords'):
            self.assertIn(key, CREATIVE_STORY_BIBLE_TEMPLATE,
                          f'Story Bible 缺少字段: {key}')

    def test_quality_constants(self):
        from src.core.creative_writer import CreativeProjectManager
        self.assertEqual(CreativeProjectManager.SIMILARITY_THRESHOLD, 0.72)
        self.assertEqual(CreativeProjectManager.MAX_RETRY, 2)
        self.assertEqual(CreativeProjectManager.MIN_SCORE, 7)
        self.assertEqual(CreativeProjectManager.MAX_POOL_SIZE, 50)
        self.assertEqual(CreativeProjectManager.DEFAULT_CHUNK_MIN, 60)
        self.assertEqual(CreativeProjectManager.DEFAULT_CHUNK_MAX, 1200)
        self.assertEqual(CreativeProjectManager.DEFAULT_INTERVAL_MIN, 95)
        self.assertEqual(CreativeProjectManager.DEFAULT_INTERVAL_MAX, 320)

    def test_disabled_returns_empty(self):
        from src.core.creative_writer import CreativeProjectManager
        mgr = CreativeProjectManager(db_manager=MagicMock())
        mgr.enabled = False
        self.assertEqual(mgr.generate_creative_project({}), {})
        self.assertEqual(mgr.generate_creative_chunk({}, 200), "")

    def test_jaccard_similarity(self):
        from src.core.creative_writer import CreativeProjectManager
        sim_same = CreativeProjectManager._jaccard_similarity(
            '我喜欢喝咖啡', '我喜欢喝咖啡')
        self.assertGreater(sim_same, 0.9)
        sim_diff = CreativeProjectManager._jaccard_similarity(
            '今天下雨了', '我喜欢吃苹果')
        self.assertLess(sim_diff, 0.5)
        self.assertEqual(CreativeProjectManager._jaccard_similarity('', ''), 0.0)


class TestCreativeDatabaseSchema(unittest.TestCase):
    """P3 新增表存在性检查"""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        from src.core.database_manager import DatabaseManager
        self.db = DatabaseManager(db_path=self._tmp.name, debug=False)

    def tearDown(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_p3_tables_exist(self):
        import sqlite3
        conn = sqlite3.connect(self._tmp.name)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
        for tbl in ('creative_projects', 'creative_story_bibles',
                    'creative_memory_pool'):
            self.assertIn(tbl, tables, f'P3 表缺失: {tbl}')

    def test_create_and_list_project(self):
        project = {
            'title': '测试项目',
            'work_type': '短篇',
            'premise': '一个小故事',
            'tone': '温暖',
            'point_of_view': '第一人称',
            'target_chars': 1000,
        }
        pid = self.db.create_creative_project(project)
        self.assertTrue(pid)
        # 数据库直接更新状态
        self.db.update_creative_project(pid, {'status': 'finished'})
        rows = self.db.list_creative_projects(status='finished')
        self.assertGreaterEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'finished')

    def test_story_bible_upsert(self):
        project = {
            'title': 'A', 'work_type': '短篇',
            'premise': '', 'target_chars': 1000,
        }
        pid = self.db.create_creative_project(project)
        bible = {
            'mainline_direction': 'main',
            'active_themes': ['成长'],
            'unresolved_threads': ['谜题'],
            'resolved_threads': [],
            'important_facts': ['人物 A'],
            'next_direction': '下一章',
            'recent_keywords': ['x', 'y'],
        }
        self.assertTrue(self.db.upsert_story_bible(pid, bible))
        out = self.db.get_story_bible(pid)
        self.assertEqual(out['mainline_direction'], 'main')
        self.assertIn('成长', out['active_themes'])

    def test_memory_pool_prune(self):
        project = {
            'title': 'B', 'work_type': '短篇',
            'premise': '', 'target_chars': 1000,
        }
        pid = self.db.create_creative_project(project)
        for i in range(55):
            self.db.add_creative_memory(pid, 'chunk',
                                        f'片段 {i}', importance=i / 100.0)
        # 修剪到 50 条
        deleted = self.db.prune_creative_memory_pool(pid, keep_max=50)
        self.assertEqual(deleted, 5)
        pool = self.db.get_creative_memory_pool(pid, limit=100)
        self.assertEqual(len(pool), 50)


class TestP3PromptTemplate(unittest.TestCase):
    """creative_writing.md prompt 模板存在性检查"""

    def test_creative_writing_prompt_exists(self):
        path = os.path.join(os.path.dirname(__file__), '..',
                            'prompts', 'task', 'creative_writing.md')
        self.assertTrue(os.path.exists(path),
                        'creative_writing.md prompt 缺失')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        # 关键段落
        self.assertIn('立项任务', content)
        self.assertIn('续写任务', content)
        self.assertIn('质量要求', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
