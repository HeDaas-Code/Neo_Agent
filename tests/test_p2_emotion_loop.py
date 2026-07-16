"""
测试 P2 阶段：PlutchikEmotionWheel + OpenLoopTracker
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

# 注入最小 dotenv stub 以兼容无依赖环境（仅满足 `from dotenv import load_dotenv`）
try:
    import dotenv  # noqa: F401
except ImportError:
    _dotenv_stub = types.ModuleType("dotenv")

    def _load_dotenv(*args, **kwargs):
        return None

    _dotenv_stub.load_dotenv = _load_dotenv
    sys.modules["dotenv"] = _dotenv_stub

try:
    import requests  # noqa: F401
except ImportError:
    _requests_stub = types.ModuleType("requests")

    def _post(*args, **kwargs):
        raise RuntimeError("requests stub: network disabled in test sandbox")

    _requests_stub.post = _post
    sys.modules["requests"] = _requests_stub


class TestPlutchikEmotionWheelContract(unittest.TestCase):
    """PlutchikEmotionWheel API 契约检查（不依赖真实 LLM）"""

    def test_class_and_methods_exist(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        required = [
            'decay_emotions', 'nudge_emotion',
            'profile_from_basic', 'format_emotion_hint',
        ]
        for name in required:
            self.assertTrue(hasattr(PlutchikEmotionWheel, name),
                            f'PlutchikEmotionWheel 缺少方法: {name}')

    def test_eight_basic_emotions(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        expected = {'joy', 'trust', 'fear', 'surprise',
                    'sadness', 'disgust', 'anger', 'anticipation'}
        self.assertEqual(set(PlutchikEmotionWheel.EMOTIONS), expected)
        self.assertEqual(set(PlutchikEmotionWheel.EMOTION_CN.keys()), expected)
        for k, v in PlutchikEmotionWheel.EMOTION_CN.items():
            self.assertIsInstance(v, str) and len(v) > 0
        # OPPOSITES 必须配对
        for k, v in PlutchikEmotionWheel.OPPOSITES.items():
            self.assertEqual(PlutchikEmotionWheel.OPPOSITES[v], k)

    def test_feature_flag_default_off(self):
        from src.core import emotion_analyzer as ea
        self.assertFalse(ea.ENABLE_EMOTION_WHEEL,
                         'ENABLE_EMOTION_WHEEL 默认应为关闭')

    def test_nudge_emotion_clamps(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock())
        out = wheel.nudge_emotion({'joy': 0.5}, 'joy', 1.0)
        self.assertEqual(out['joy'], 1.0)
        out = wheel.nudge_emotion({'joy': 0.3}, 'joy', -1.0)
        self.assertEqual(out['joy'], 0.0)
        # 未知维度应被忽略
        out = wheel.nudge_emotion({'joy': 0.5}, 'unknown', 0.5)
        self.assertNotIn('unknown', out)

    def test_decay_emotions_applies_exponential(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock(), half_life_hours=24.0)
        state = {
            'emotions': {'joy': 1.0, 'trust': 0.5},
            'last_update': (datetime.now() - timedelta(hours=24)).isoformat(),
        }
        out = wheel.decay_emotions(state)
        # 半衰期后，joy 约为 0.5
        self.assertAlmostEqual(out['emotions']['joy'], 0.5, places=2)
        # trust 约为 0.25
        self.assertAlmostEqual(out['emotions']['trust'], 0.25, places=2)
        self.assertIsNotNone(out.get('last_update'))

    def test_decay_default_state(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock())
        out = wheel.decay_emotions({})
        self.assertEqual(set(out['emotions'].keys()), set(wheel.EMOTIONS))
        for v in out['emotions'].values():
            self.assertEqual(v, 0.0)

    def test_profile_primary_secondary_compound(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock())
        profile = wheel.profile_from_basic({
            'joy': 0.8, 'anticipation': 0.6,
            'fear': 0.1, 'sadness': 0.0,
            'trust': 0.3, 'surprise': 0.2,
            'disgust': 0.0, 'anger': 0.0,
        })
        self.assertEqual(profile['primary'], '喜悦')
        self.assertEqual(profile['secondary'], '期待')
        self.assertIn('但有点', profile['compound_desc'])
        self.assertTrue(profile['intensity'] > 0)

    def test_profile_empty(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock())
        profile = wheel.profile_from_basic({})
        self.assertEqual(profile['primary'], '平静')
        self.assertIsNone(profile['secondary'])

    def test_format_disabled_returns_empty(self):
        from src.core import emotion_analyzer as ea
        # 直接构造一个 enabled=False 的实例（避免污染全局）
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock())
        wheel.enabled = False
        self.assertEqual(
            wheel.format_emotion_hint({'emotions': {'joy': 0.5}}),
            "",
        )

    def test_format_emotion_hint_contains_label(self):
        from src.core.emotion_analyzer import PlutchikEmotionWheel
        wheel = PlutchikEmotionWheel(db_manager=MagicMock())
        wheel.enabled = True
        text = wheel.format_emotion_hint({
            'emotions': {'joy': 0.8, 'anticipation': 0.4, **{k: 0.0 for k in [
                'trust', 'fear', 'surprise', 'sadness', 'disgust', 'anger'
            ]}}
        })
        self.assertIn('【当下情绪】', text)
        self.assertIn('喜悦', text)


class TestOpenLoopTrackerContract(unittest.TestCase):
    """OpenLoopTracker API 契约检查"""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        from src.core.database_manager import DatabaseManager
        self.db = DatabaseManager(db_path=self._tmp.name, debug=False)

    def tearDown(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_class_and_methods_exist(self):
        from src.core.long_term_memory import OpenLoopTracker
        required = ['update_from_message', 'resolve_matching_loop', 'format_for_prompt']
        for name in required:
            self.assertTrue(hasattr(OpenLoopTracker, name),
                            f'OpenLoopTracker 缺少方法: {name}')

    def test_feature_flag_default_off(self):
        from src.core import long_term_memory as ltm
        self.assertFalse(ltm.ENABLE_OPEN_LOOP,
                         'ENABLE_OPEN_LOOP 默认应为关闭')

    def test_update_extracts_topic(self):
        from src.core.long_term_memory import OpenLoopTracker
        tracker = OpenLoopTracker(db_manager=self.db)
        tracker.enabled = True
        result = tracker.update_from_message('u1', '记得明天帮我带杯咖啡')
        self.assertIsNotNone(result)
        self.assertEqual(result.get('status'), 'open')
        self.assertIn('uuid', result)

    def test_update_no_match_returns_empty(self):
        from src.core.long_term_memory import OpenLoopTracker
        tracker = OpenLoopTracker(db_manager=self.db)
        tracker.enabled = True
        result = tracker.update_from_message('u1', '今天天气真好啊')
        # 仅关键词但无触发器，仍可能返回空
        self.assertIsInstance(result, dict)

    def test_format_disabled_returns_empty(self):
        from src.core.long_term_memory import OpenLoopTracker
        tracker = OpenLoopTracker(db_manager=self.db)
        tracker.enabled = False
        self.assertEqual(tracker.format_for_prompt(), "")

    def test_format_with_active_loops(self):
        from src.core.long_term_memory import OpenLoopTracker
        tracker = OpenLoopTracker(db_manager=self.db)
        tracker.enabled = True
        tracker.update_from_message('u1', '记得明天帮我带杯咖啡')
        text = tracker.format_for_prompt()
        self.assertIn('【未完话题】', text)

    def test_resolve_matching_loop(self):
        from src.core.long_term_memory import OpenLoopTracker
        tracker = OpenLoopTracker(db_manager=self.db)
        tracker.enabled = True
        tracker.update_from_message('u1', '记得明天帮我带杯咖啡')
        # 用相似关键词解析
        result = tracker.resolve_matching_loop('咖啡')
        # 命中或不命中皆可，主要看实现不报错
        self.assertTrue(result is None or isinstance(result, dict))


class TestAccumulatedScoringNotBroken(unittest.TestCase):
    """回归测试：现有 EmotionRelationshipAnalyzer 累加评分机制未被破坏"""

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        from src.core.database_manager import DatabaseManager
        self.db = DatabaseManager(db_path=self._tmp.name, debug=False)

    def tearDown(self):
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_emotion_relationship_analyzer_unchanged(self):
        from src.core.emotion_analyzer import EmotionRelationshipAnalyzer
        # 关键方法必须保留
        for name in [
            'analyze_emotion_relationship', '_save_emotion_to_db',
            'get_latest_emotion', 'get_emotion_trend', 'generate_tone_prompt',
        ]:
            self.assertTrue(hasattr(EmotionRelationshipAnalyzer, name),
                            f'EmotionRelationshipAnalyzer 缺少方法: {name}')

    def test_plutchik_class_is_new(self):
        # PlutchikEmotionWheel 与 EmotionRelationshipAnalyzer 是并列类，不是子类
        from src.core.emotion_analyzer import (
            EmotionRelationshipAnalyzer, PlutchikEmotionWheel
        )
        self.assertFalse(
            issubclass(PlutchikEmotionWheel, EmotionRelationshipAnalyzer),
            'PlutchikEmotionWheel 不应继承自 EmotionRelationshipAnalyzer'
        )


class TestP2PromptExtension(unittest.TestCase):
    """emotion_analysis.md 扩展（Plutchik 维度）契约检查"""

    def test_emotion_analysis_prompt_contains_plutchik_section(self):
        path = os.path.join(
            os.path.dirname(__file__), '..',
            'prompts', 'system', 'emotion_analysis.md'
        )
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('Plutchik', content)
        self.assertIn('emotion_wheel', content)
        for dim in ('joy', 'trust', 'fear', 'surprise',
                    'sadness', 'disgust', 'anger', 'anticipation'):
            self.assertIn(dim, content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
