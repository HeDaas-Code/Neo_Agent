"""
Neo Agent - Core modules

核心模块包含对话代理、数据库管理、记忆系统等核心功能

注意：以下 Usage 块中的 import 行为为示例说明，并非 __init__ 运行时真实 import。
本文件通过 __all__ 暴露子模块名，子模块的类需由调用方自行 import。
本仓库中实际可用的类名为 TemporaryScheduleGenerator（位于 src/core/schedule_generator.py），
不存在顶层名为 ScheduleGenerator 的类。

Usage (示例):
    from src.core.chat_agent import ChatAgent
    from src.core.database_manager import DatabaseManager
    from src.core.emotion_analyzer import EmotionAnalyzer
    from src.core.event_manager import EventManager
    from src.core.knowledge_base import KnowledgeBase
    from src.core.long_term_memory import LongTermMemory
    from src.core.base_knowledge import BaseKnowledge
    from src.core.multi_agent_coordinator import MultiAgentCoordinator
    from src.core.schedule_manager import ScheduleManager
    from src.core.schedule_generator import TemporaryScheduleGenerator
    from src.core.schedule_similarity_checker import ScheduleSimilarityChecker
"""

__all__ = [
    'chat_agent',
    'database_manager',
    'emotion_analyzer',
    'event_manager',
    'knowledge_base',
    'long_term_memory',
    'base_knowledge',
    'multi_agent_coordinator',
    'schedule_manager',
    'schedule_generator',
    'schedule_similarity_checker',
]
