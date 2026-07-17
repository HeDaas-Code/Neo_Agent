"""
Proactive Engine - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.prefrontal.proactive.proactive_engine
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.prefrontal.proactive.proactive_engine
"""

from __future__ import annotations

from src.prefrontal.proactive.proactive_engine import (
    ENABLE_PROACTIVE_ENGINE,
    ProactiveEngine,
)

__all__ = ["ProactiveEngine", "ENABLE_PROACTIVE_ENGINE"]
