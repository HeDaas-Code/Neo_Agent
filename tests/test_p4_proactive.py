"""
测试 P4 阶段：ProactiveEngine + BackgroundScheduler
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


class TestProactiveEngineContract(unittest.TestCase):
    """ProactiveEngine API 契约检查"""

    def test_class_and_methods_exist(self):
        from src.core.proactive_engine import ProactiveEngine
        required = [
            'schedule_next_proactive', 'should_send',
            'bot_proactive_drive', 'proactive_inner_readiness',
            'proactive_impulse_pool', 'bot_proactive_drive_send',
        ]
        for name in required:
            self.assertTrue(hasattr(ProactiveEngine, name),
                            f'ProactiveEngine 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import proactive_engine as pe
        self.assertFalse(pe.ENABLE_PROACTIVE_ENGINE,
                         'ENABLE_PROACTIVE_ENGINE 默认应为关闭')

    def test_disabled_should_send_returns_false(self):
        from src.core.proactive_engine import ProactiveEngine
        engine = ProactiveEngine(db_manager=MagicMock())
        engine.enabled = False
        ok, reason = engine.should_send('u1')
        self.assertFalse(ok)
        self.assertEqual(reason, 'disabled')

    def test_disabled_impulse_pool_empty(self):
        from src.core.proactive_engine import ProactiveEngine
        engine = ProactiveEngine(db_manager=MagicMock())
        engine.enabled = False
        self.assertEqual(engine.proactive_impulse_pool('u1'), [])

    def test_quiet_hours_detection(self):
        from src.core.proactive_engine import ProactiveEngine
        engine = ProactiveEngine(db_manager=MagicMock())
        engine.enabled = True
        late_night = datetime(2026, 7, 13, 23, 30)
        early_morning = datetime(2026, 7, 13, 6, 30)
        afternoon = datetime(2026, 7, 13, 14, 30)
        self.assertTrue(engine._is_quiet_time(late_night))
        self.assertTrue(engine._is_quiet_time(early_morning))
        self.assertFalse(engine._is_quiet_time(afternoon))


class TestBackgroundSchedulerContract(unittest.TestCase):
    """BackgroundScheduler API 契约检查"""

    def test_class_and_methods_exist(self):
        from src.core.background_scheduler import BackgroundScheduler
        required = [
            'start', 'stop', 'scheduler_loop', 'get_status',
        ]
        for name in required:
            self.assertTrue(hasattr(BackgroundScheduler, name),
                            f'BackgroundScheduler 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import background_scheduler as bs
        self.assertFalse(bs.ENABLE_BACKGROUND_SCHEDULER,
                         'ENABLE_BACKGROUND_SCHEDULER 默认应为关闭')

    def test_disabled_start_returns_false(self):
        from src.core.background_scheduler import BackgroundScheduler
        sched = BackgroundScheduler(tick_seconds=10)
        sched.enabled = False
        self.assertFalse(sched.start())

    def test_get_status(self):
        from src.core.background_scheduler import BackgroundScheduler
        sched = BackgroundScheduler(tick_seconds=20)
        status = sched.get_status()
        self.assertEqual(status['tick_seconds'], 20)
        self.assertFalse(status['running'])
        self.assertEqual(status['last_run_at'], {})

    def test_thread_isolation(self):
        """线程隔离：scheduler.start 在独立子线程运行，不阻塞主线程。"""
        from src.core.background_scheduler import BackgroundScheduler
        sched = BackgroundScheduler(tick_seconds=1)
        sched.enabled = True
        try:
            sched.start()
            # 主线程应立即返回，scheduler 在子线程中运行
            self.assertTrue(sched._thread is not None)
            self.assertNotEqual(sched._thread.name, 'MainThread')
            self.assertTrue(sched._thread.daemon)
        finally:
            sched.stop(timeout=2)


class TestMainEntryPoint(unittest.TestCase):
    """main.py 启动后台调度（线程隔离）契约检查"""

    def test_main_creates_background_scheduler(self):
        path = os.path.join(os.path.dirname(__file__), '..', 'main.py')
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('background_scheduler', content)
        self.assertIn('start_default_scheduler', content)
        self.assertIn('background_scheduler.stop()', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
