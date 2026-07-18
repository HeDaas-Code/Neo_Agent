# Compatibility shim: src.core.knowledge_base has moved to src.limbic.hippocampus.knowledge_store (v4.0)
from src.limbic.hippocampus.knowledge_store import KnowledgeBase

__all__ = ["KnowledgeBase"]
