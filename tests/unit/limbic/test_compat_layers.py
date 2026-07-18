"""
v4.0 兼容层单元测试。

验证旧路径（src.core.*）仍然可以通过导入转发访问新实现。
"""

from src.core.emotion_analyzer import (
    EmotionRelationshipAnalyzer as CoreEmotionAnalyzer,
    PlutchikEmotionWheel as CorePlutchikEmotionWheel,
)
from src.core.knowledge_base import KnowledgeBase as CoreKnowledgeBase
from src.core.long_term_memory import (
    LongTermMemoryManager as CoreLongTermMemoryManager,
    OpenLoopTracker as CoreOpenLoopTracker,
)
from src.core.chat_session_repository import ChatSessionRepository
from src.core.model_config import ModelConfig, ModelType
from src.limbic.amygdala.emotion_state import (
    EmotionRelationshipAnalyzer as LimbicEmotionAnalyzer,
    PlutchikEmotionWheel as LimbicPlutchikEmotionWheel,
)
from src.limbic.hippocampus.knowledge_store import KnowledgeBase as LimbicKnowledgeBase
from src.limbic.hippocampus.memory_store import (
    LongTermMemoryManager as LimbicLongTermMemoryManager,
    OpenLoopTracker as LimbicOpenLoopTracker,
)
from src.limbic.hippocampus.session_store import SessionStore


def test_emotion_analyzer_compat():
    """
    src.core.emotion_analyzer 应转发到 src.limbic.amygdala.emotion_state。
    """
    assert CoreEmotionAnalyzer is LimbicEmotionAnalyzer
    assert CorePlutchikEmotionWheel is LimbicPlutchikEmotionWheel


def test_knowledge_base_compat():
    """
    src.core.knowledge_base 应转发到 src.limbic.hippocampus.knowledge_store。
    """
    assert CoreKnowledgeBase is LimbicKnowledgeBase


def test_long_term_memory_compat():
    """
    src.core.long_term_memory 应转发到 src.limbic.hippocampus.memory_store。
    """
    assert CoreLongTermMemoryManager is LimbicLongTermMemoryManager
    assert CoreOpenLoopTracker is LimbicOpenLoopTracker


def test_chat_session_repository_compat():
    """
    src.core.chat_session_repository 应转发到 src.limbic.hippocampus.session_store。
    """
    assert ChatSessionRepository is SessionStore


def test_model_config_compat():
    """
    src.core.model_config 应转发到 src.cortex.config.model_config。
    """
    assert ModelConfig is not None
    assert ModelType is not None
