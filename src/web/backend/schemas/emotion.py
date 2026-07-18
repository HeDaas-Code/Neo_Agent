"""
Emotion schemas - Pydantic v2 models for emotion endpoints.
情感分析相关的 Pydantic v2 模型。

Stage B.3: 为 /api/emotion/* 提供情感雷达所需的响应契约。
对齐前端 EmotionPanel.tsx 的 EmotionData 类型。

`cumulative` 字段映射"关系状态"维度（EmotionRelationshipAnalyzer
累加评分），`plutchik` 字段映射"当下情绪"维度（PlutchikEmotionWheel
8 维归一化强度）。`last_message` 为最近一次参与情感分析的用户消息。
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# 常量：Plutchik 8 维
# ----------------------------------------------------------------------
PLUTCHIK_KEYS = (
    'joy', 'trust', 'fear', 'surprise',
    'sadness', 'disgust', 'anger', 'anticipation',
)


def _default_eight() -> Dict[str, float]:
    """8 维默认值 0.0。"""
    return {k: 0.0 for k in PLUTCHIK_KEYS}


# ----------------------------------------------------------------------
# Pydantic v2 模型
# ----------------------------------------------------------------------
class EmotionResponse(BaseModel):
    """
    最新情感分析响应（Stage B.3 雷达后端契约）。

    Attributes:
        cumulative: 累加评分（Plutchik 8 维）。
            由 EmotionRelationshipAnalyzer 的累加评分映射而来，
            代表"关系状态"维度。
        plutchik: Plutchik 8 维情绪强度（0-1 归一化）。
            由 PlutchikEmotionWheel 计算，代表"当下情绪"维度。
        last_message: 最近一次参与情感分析的用户消息原文。
            没有则为空字符串。
        timestamp: ISO 8601 时间戳（情感分析完成时刻）。
            没有则为空字符串。
        user_id: 用户标识（请求里透传，默认 "default"）。
        historical_max: 可选历史最高（淡色背景叠加）。

    Notes:
        - 8 维字典使用 default_factory 兜底；缺键自动补 0.0。
        - 兼容 Pydantic v2 from_attributes，便于直接以 ORM 行/类填充。
    """
    model_config = ConfigDict(from_attributes=True)

    cumulative: Dict[str, float] = Field(
        default_factory=_default_eight,
        description="累加评分（8 维 0-1 归一化）",
    )
    plutchik: Dict[str, float] = Field(
        default_factory=_default_eight,
        description="Plutchik 8 维当下情绪（0-1 归一化）",
    )
    last_message: str = Field(
        default="",
        description="最近一次参与分析的用户消息",
    )
    timestamp: str = Field(
        default="",
        description="ISO 8601 时间戳",
    )
    user_id: str = Field(
        default="default",
        description="用户标识",
    )
    historical_max: Optional[Dict[str, float]] = Field(
        default=None,
        description="可选历史最高（8 维）",
    )


# 兼容历史导入：保留旧名字（Stage A.3 早期曾用过）
EmotionLatestResponse = EmotionResponse


__all__ = [
    "PLUTCHIK_KEYS",
    "EmotionResponse",
    "EmotionLatestResponse",
]
