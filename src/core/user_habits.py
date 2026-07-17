"""
UserHabits - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.hypothalamus.habits.user_habits
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.hypothalamus.habits.user_habits
"""

from __future__ import annotations

from src.hypothalamus.habits.user_habits import (
    ENABLE_USER_HABITS,
    UserHabitTracker,
)

__all__ = [
    "ENABLE_USER_HABITS",
    "UserHabitTracker",
]
