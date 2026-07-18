"""
Model Config - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.cortex.config.model_config
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.cortex.config.model_config
"""

from __future__ import annotations

from src.cortex.config.model_config import (
    ModelConfig,
    ModelType,
    get_model_config,
)

__all__ = ["ModelConfig", "ModelType", "get_model_config"]
