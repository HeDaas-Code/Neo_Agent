"""
Emotion Analyzer - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.limbic.amygdala.emotion_state
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.limbic.amygdala.emotion_state
"""

from __future__ import annotations

from src.limbic.amygdala.emotion_state import (
    EmotionRelationshipAnalyzer,
    PlutchikEmotionWheel,
    format_emotion_summary,
    ENABLE_EMOTION_WHEEL,
)

__all__ = [
    "EmotionRelationshipAnalyzer",
    "PlutchikEmotionWheel",
    "format_emotion_summary",
    "ENABLE_EMOTION_WHEEL",
]
