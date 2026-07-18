"""
测试探索性阶段：UserHabitTracker + SelfTimelineAggregator + LifeStateManager.body_cycle
环境无 pytest / 缺依赖时，本文件可作为 AST 解析与 import 路径的契约检查。
"""

import os
import sys
import unittest
import tempfile
import types
from datetime import datetime
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import dotenv  # noqa: F401
except ImportError:
    _stub = types.ModuleType("dotenv")
    _stub.load_dotenv = lambda *a, **k: None
    sys.modules["dotenv"] = _stub
try:
    import requests  # noqa: F401
except ImportError:
    _stub = types.ModuleType("requests")
    _stub.post = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("stub"))
    sys.modules["requests"] = _stub


class TestUserHabitTrackerContract(unittest.TestCase):
    """UserHabitTracker API 契约检查"""

    def test_class_and_methods_exist(self):
        from src.core.user_habits import UserHabitTracker
        required = [
            'update_from_message', 'qualified_habits',
            'habit_proactive_event', 'format_for_schedule',
        ]
        for name in required:
            self.assertTrue(hasattr(UserHabitTracker, name),
                            f'UserHabitTracker 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import user_habits as uh
        self.assertFalse(uh.ENABLE_USER_HABITS, 'ENABLE_USER_HABITS 默认关闭')

    def test_categories(self):
        from src.core.user_habits import UserHabitTracker
        for cat in ('作息', '饮食', '工作', '娱乐'):
            self.assertIn(cat, UserHabitTracker.CATEGORIES)

    def test_qualify_rule(self):
        from src.core.user_habits import UserHabitTracker
        self.assertEqual(UserHabitTracker.MIN_DAYS_FOR_QUALIFY, 2)


class TestSelfTimelineAggregatorContract(unittest.TestCase):
    """SelfTimelineAggregator API 契约检查"""

    def test_class_and_methods_exist(self):
        from src.core.self_timeline import SelfTimelineAggregator
        required = ['is_timeline_query', 'aggregate_timeline', 'format_for_prompt']
        for name in required:
            self.assertTrue(hasattr(SelfTimelineAggregator, name),
                            f'SelfTimelineAggregator 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import self_timeline as st
        self.assertFalse(st.ENABLE_SELF_TIMELINE, 'ENABLE_SELF_TIMELINE 默认关闭')

    def test_timeline_query_detection(self):
        from src.core.self_timeline import SelfTimelineAggregator
        agg = SelfTimelineAggregator(db_manager=MagicMock())
        self.assertTrue(agg.is_timeline_query('你今天做了什么？'))
        self.assertTrue(agg.is_timeline_query('你最近怎么样？'))
        self.assertTrue(agg.is_timeline_query('你昨天晚上睡得好吗？'))
        self.assertFalse(agg.is_timeline_query('今天天气怎么样？'))

    def test_disabled_aggregate_empty(self):
        from src.core.self_timeline import SelfTimelineAggregator
        agg = SelfTimelineAggregator(db_manager=MagicMock())
        agg.enabled = False
        self.assertEqual(agg.aggregate_timeline('u1', '你今天做什么？'), [])


class TestLifeStateBodyCycleContract(unittest.TestCase):
    """LifeStateManager.body_cycle 子模块契约检查"""

    def test_methods_exist(self):
        from src.core.life_state import LifeStateManager
        for name in ('body_cycle', 'cycle_phase', 'cycle_energy_modifier'):
            self.assertTrue(hasattr(LifeStateManager, name),
                            f'LifeStateManager 缺少方法: {name}')

    def test_disabled_for_male(self):
        from src.core.life_state import LifeStateManager
        mgr = LifeStateManager(db_manager=MagicMock(), character_info={'gender': 'male'})
        out = mgr.body_cycle()
        self.assertFalse(out['enabled'])
        self.assertEqual(out['phase'], '')

    def test_enabled_for_female(self):
        from src.core.life_state import LifeStateManager
        mgr = LifeStateManager(db_manager=MagicMock(), character_info={'gender': 'female'})
        out = mgr.body_cycle()
        self.assertTrue(out['enabled'])
        self.assertIn(out['phase'], ('经期', '经后', '排卵期', '经前'))
        self.assertIsInstance(out['energy_modifier'], float)

    def test_phase_buckets(self):
        from src.core.life_state import LifeStateManager
        self.assertEqual(LifeStateManager.cycle_phase(0), '经期')
        self.assertEqual(LifeStateManager.cycle_phase(4), '经期')
        self.assertEqual(LifeStateManager.cycle_phase(5), '经后')
        self.assertEqual(LifeStateManager.cycle_phase(12), '经后')
        self.assertEqual(LifeStateManager.cycle_phase(13), '排卵期')
        self.assertEqual(LifeStateManager.cycle_phase(16), '排卵期')
        self.assertEqual(LifeStateManager.cycle_phase(17), '经前')
        self.assertEqual(LifeStateManager.cycle_phase(27), '经前')
        self.assertEqual(LifeStateManager.cycle_phase(28), '经期')  # wraps

    def test_energy_modifier_ranges(self):
        from src.core.life_state import LifeStateManager
        for phase in ('经期', '经后', '排卵期', '经前'):
            mod = LifeStateManager.cycle_energy_modifier(phase)
            self.assertGreaterEqual(mod, -0.2)
            self.assertLessEqual(mod, 0.1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
