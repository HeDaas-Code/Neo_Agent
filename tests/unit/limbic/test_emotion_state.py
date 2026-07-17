"""
emotion_state 单元测试。

主要测试 PlutchikEmotionWheel 的纯逻辑功能，不依赖真实 LLM/DB。
"""

import os
from datetime import datetime, timedelta

import pytest

from src.limbic.amygdala.emotion_state import (
    EmotionRelationshipAnalyzer,
    PlutchikEmotionWheel,
    format_emotion_summary,
)


def test_plutchik_default_state():
    """
    测试 PlutchikEmotionWheel 默认状态所有情绪为 0。
    """
    wheel = PlutchikEmotionWheel()
    state = wheel._default_state()

    assert set(state["emotions"].keys()) == set(PlutchikEmotionWheel.EMOTIONS)
    assert all(v == 0.0 for v in state["emotions"].values())


def test_plutchik_decay():
    """
    测试情绪随时间衰减。
    """
    wheel = PlutchikEmotionWheel(half_life_hours=1.0)
    now = datetime.now()
    state = {
        "emotions": {"joy": 1.0},
        "last_update": (now - timedelta(hours=1)).isoformat(),
    }

    decayed = wheel.decay_emotions(state, now)

    # 经过一个半衰期，joy 应衰减到约 0.5
    assert decayed["emotions"]["joy"] == pytest.approx(0.5, abs=0.01)
    assert decayed["last_update"] == now.isoformat()


def test_plutchik_nudge_clamps():
    """
    测试 nudge_emotion 在 [0, 1] 范围内截断。
    """
    wheel = PlutchikEmotionWheel()
    emotions = {"joy": 0.8}

    assert wheel.nudge_emotion(emotions, "joy", 0.5)["joy"] == 1.0
    assert wheel.nudge_emotion(emotions, "joy", -2.0)["joy"] == 0.0
    assert wheel.nudge_emotion(emotions, "unknown", 0.1) == emotions


def test_plutchik_profile_from_basic():
    """
    测试从 8 维情绪推导 profile。
    """
    wheel = PlutchikEmotionWheel()
    emotions = {
        "joy": 0.8,
        "trust": 0.2,
        "fear": 0.0,
        "surprise": 0.0,
        "sadness": 0.0,
        "disgust": 0.0,
        "anger": 0.0,
        "anticipation": 0.3,
    }

    profile = wheel.profile_from_basic(emotions)

    assert profile["primary"] == "喜悦"
    assert profile["intensity"] > 0


def test_format_emotion_summary_initial():
    """
    测试初次评估结果格式化。
    """
    emotion_data = {
        "impression": "用户很友好",
        "relationship_type": "初识",
        "emotional_tone": "积极",
        "overall_score": 30,
        "sentiment": "positive",
        "key_topics": ["问候"],
        "analysis": "初次交流很愉快",
        "is_initial": True,
    }

    summary = format_emotion_summary(emotion_data)

    assert "30/35" in summary
    assert "用户很友好" in summary


def test_format_emotion_summary_update():
    """
    测试更新评估结果格式化。
    """
    emotion_data = {
        "impression": "用户表现正常",
        "relationship_type": "朋友",
        "emotional_tone": "中性",
        "overall_score": 65,
        "previous_score": 62,
        "score_change": 3,
        "sentiment": "neutral",
        "key_topics": [],
        "analysis": "关系稳定",
        "is_initial": False,
    }

    summary = format_emotion_summary(emotion_data)

    assert "65/100" in summary
    assert "+3" in summary
