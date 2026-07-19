"""
Neo Agent - Core modules (v3 兼容层)

src/core/ 保留 v3.x 的 ChatAgent 及配套基础设施，供 Web 后端（v3 路径）继续使用。
v4.0 新增的神经-认知架构位于：
  - src/nervous_system/   中央路由、网关、中间件
  - src/cortex/           大脑皮层（LLMCore、工具调用）
  - src/prefrontal/       工作流编排
  - src/limbic/           记忆与情感
  - src/cerebellum/       工具与日程意图

职责边界：
  - core/chat_agent.py:  v3 ChatAgent 单入口，维护会话、情感、日程、主动决策
  - core/cross_module_workflow.py:  v4 WorkflowModule 内部使用的工作流实现
  - core/database_manager.py / long_term_memory.py / emotion_analyzer.py:
    v3 与 v4 共享的数据/分析基础设施
  - core/llm_helper.py / langchain_llm.py / model_config.py / llm_providers.py:
    v3 LLM 封装；v4 已迁移到 src/cortex/
  - 其它模块（event_manager / knowledge_base / multi_agent_coordinator 等）:
    v3 功能模块，由 Web API / creative_service / event_service 调用

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
