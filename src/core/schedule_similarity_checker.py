"""
Schedule Similarity Checker - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.prefrontal.schedule.schedule_similarity_checker
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.prefrontal.schedule.schedule_similarity_checker
"""

from __future__ import annotations

from src.prefrontal.schedule.schedule_similarity_checker import (
    ScheduleSimilarityChecker,
    get_schedules_on_same_day,
)

__all__ = ["ScheduleSimilarityChecker", "get_schedules_on_same_day"]
