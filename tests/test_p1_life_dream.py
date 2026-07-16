"""
测试 P1 阶段：LifeStateManager + DreamDiaryManager
环境无 pytest 时，本文件可作为 AST 解析与 import 路径的契约检查。
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestLifeStateManagerContract(unittest.TestCase):
    """LifeStateManager API 契约检查（不依赖真实 LLM 调用）"""

    def test_class_and_methods_exist(self):
        from src.core.life_state import LifeStateManager
        required = [
            'ensure_daily_state', 'generate_state_conditions',
            'get_current_state_snapshot', 'apply_transition',
            'format_state_for_prompt', 'consume_dream_energy_delta',
        ]
        for name in required:
            self.assertTrue(hasattr(LifeStateManager, name),
                            f'LifeStateManager 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import life_state as ls
        # 默认关闭（开发与生产可独立调整）
        self.assertFalse(ls.ENABLE_LIFE_STATE,
                         'ENABLE_LIFE_STATE 默认应为关闭')

    def test_disabled_returns_default_snapshot(self):
        from src.core.life_state import LifeStateManager
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            from src.core.database_manager import DatabaseManager
            db = DatabaseManager(db_path=db_path, debug=False)
            mgr = LifeStateManager(db_manager=db)
            snap = mgr.ensure_daily_state()
            self.assertEqual(snap['state_title'], '常态')
            self.assertEqual(snap['mood'], '平静')
            self.assertEqual(snap['health'], '健康')
            self.assertEqual(snap['energy'], 0.7)
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_consume_dream_energy_delta(self):
        from src.core.life_state import LifeStateManager
        mgr = LifeStateManager(db_manager=MagicMock())
        mgr.consume_dream_energy_delta(0.2)
        self.assertEqual(mgr._last_dream_energy_delta, 0.2)


class TestDreamDiaryManagerContract(unittest.TestCase):
    """DreamDiaryManager API 契约检查"""

    def test_class_and_methods_exist(self):
        from src.core.dream_diary import DreamDiaryManager
        required = [
            'generate_dream_pick', 'generate_daily_diary',
            'build_dream_memory_fragments', 'recent_diary_context',
        ]
        for name in required:
            self.assertTrue(hasattr(DreamDiaryManager, name),
                            f'DreamDiaryManager 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import dream_diary as dd
        self.assertFalse(dd.ENABLE_DREAM_DIARY,
                         'ENABLE_DREAM_DIARY 默认应为关闭')

    def test_dream_types_and_labels(self):
        from src.core.dream_diary import DreamDiaryManager
        self.assertEqual(len(DreamDiaryManager.DREAM_TYPES), 6)
        self.assertIn('温柔日常', DreamDiaryManager.DREAM_TYPES)
        self.assertIn('怀旧', DreamDiaryManager.DREAM_TYPES)

    def test_disabled_returns_empty(self):
        from src.core.dream_diary import DreamDiaryManager
        mgr = DreamDiaryManager(db_manager=MagicMock())
        self.assertEqual(mgr.generate_dream_pick(), {})
        self.assertEqual(mgr.generate_daily_diary(), {})
        self.assertEqual(mgr.recent_diary_context(count=3), "")


class TestPromptTemplatesExist(unittest.TestCase):
    """P1 新增 3 个 system prompt 模板存在性检查"""

    def test_templates_exist(self):
        prompt_dir = os.path.join(
            os.path.dirname(__file__), '..', 'prompts', 'system'
        )
        for name in ('life_state.md', 'dream_generation.md', 'daily_diary.md'):
            path = os.path.join(prompt_dir, name)
            self.assertTrue(os.path.exists(path),
                            f'P1 prompt 模板缺失: {name}')

    def test_life_state_template_has_required_vars(self):
        path = os.path.join(os.path.dirname(__file__), '..',
                            'prompts', 'system', 'life_state.md')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        for var in ('{character_name}', '{date}', '{weather}', '{dream_energy_delta}'):
            self.assertIn(var, content,
                          f'life_state.md 缺少变量: {var}')

    def test_daily_diary_template_has_required_vars(self):
        path = os.path.join(os.path.dirname(__file__), '..',
                            'prompts', 'system', 'daily_diary.md')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        for var in ('{state_title}', '{recent_dream_types}', '{fragments}'):
            self.assertIn(var, content,
                          f'daily_diary.md 缺少变量: {var}')


class TestDatabaseSchema(unittest.TestCase):
    """P1 新增 3 张表存在性检查"""

    def test_new_tables_exist(self):
        from src.core.database_manager import DatabaseManager
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        try:
            db = DatabaseManager(db_path=db_path, debug=False)
            import sqlite3
            conn = sqlite3.connect(db_path)
            try:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = {row[0] for row in cur.fetchall()}
            finally:
                conn.close()
            for tbl in ('life_state_daily', 'dream_records', 'diary_entries'):
                self.assertIn(tbl, tables, f'P1 表缺失: {tbl}')
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
