"""
v4.0 兼容层单元测试（下丘脑）。

验证旧路径（src.core.life_state / src.core.user_habits）
仍然可以通过导入转发访问新实现。
"""

from src.core.life_state import (
    ENABLE_LIFE_STATE as CoreEnableLifeState,
    LifeStateManager as CoreLifeStateManager,
)
from src.core.user_habits import (
    ENABLE_USER_HABITS as CoreEnableUserHabits,
    UserHabitTracker as CoreUserHabitTracker,
)
from src.hypothalamus.state.life_state import (
    ENABLE_LIFE_STATE as HypothalamusEnableLifeState,
    LifeStateManager as HypothalamusLifeStateManager,
)
from src.hypothalamus.habits.user_habits import (
    ENABLE_USER_HABITS as HypothalamusEnableUserHabits,
    UserHabitTracker as HypothalamusUserHabitTracker,
)


def test_life_state_compat():
    """
    src.core.life_state 应转发到 src.hypothalamus.state.life_state。
    """
    assert CoreLifeStateManager is HypothalamusLifeStateManager
    assert CoreEnableLifeState is HypothalamusEnableLifeState


def test_user_habits_compat():
    """
    src.core.user_habits 应转发到 src.hypothalamus.habits.user_habits。
    """
    assert CoreUserHabitTracker is HypothalamusUserHabitTracker
    assert CoreEnableUserHabits is HypothalamusEnableUserHabits
