"""
LLM Providers - v3.1.0 兼容层

v4.0 重构说明：
- 真实实现已迁移到 src.cortex.providers.registry
- 本文件保留原接口，通过导入转发保持 v3.1.0 代码向后兼容
- 新代码应优先使用 src.cortex.providers.registry
"""

from __future__ import annotations

# 从 v4.0 位置导入所有公共接口
from src.cortex.providers.registry import (
    ConfigError,
    LLMProvider,
    PROVIDERS,
    get_provider_obj,
    get_provider_summary,
    resolve_api_key,
    resolve_base_url,
    resolve_model_name,
    resolve_provider,
)

__all__ = [
    "ConfigError",
    "LLMProvider",
    "PROVIDERS",
    "resolve_provider",
    "resolve_api_key",
    "resolve_base_url",
    "resolve_model_name",
    "get_provider_obj",
    "get_provider_summary",
]
