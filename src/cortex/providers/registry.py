"""
Cortex Provider Registry - v4.0 供应商注册表

位于 src/cortex/providers/，属于大脑皮层（Cortex）的认知基础设施。

提供 6 个 OpenAI-兼容 preset + 统一的环境变量解析入口。

注意：本模块从 v3.1.0 的 src.core.llm_providers 迁移而来，逻辑保持一致。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


class ConfigError(Exception):
    """LLM 配置错误（如 custom 预设缺少 LLM_BASE_URL / LLM_MODEL_NAME）。"""


@dataclass(frozen=True)
class LLMProvider:
    """
    LLM 供应商预设。

    Attributes:
        name: 内部名称（小写，用于环境变量匹配）
        base_url: 默认 API 根地址（不含 /chat/completions）
        default_model: 默认模型名（custom 时为 None）
    """

    name: str
    base_url: Optional[str]
    default_model: Optional[str]


# 6 个 preset
PROVIDERS: Dict[str, LLMProvider] = {
    "openai": LLMProvider(
        name="openai",
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
    ),
    "deepseek": LLMProvider(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
    ),
    "siliconflow": LLMProvider(
        name="siliconflow",
        base_url="https://api.siliconflow.cn/v1",
        default_model="deepseek-ai/DeepSeek-V3.2",
    ),
    "moonshot": LLMProvider(
        name="moonshot",
        base_url="https://api.moonshot.cn/v1",
        default_model="moonshot-v1-8k",
    ),
    "zhipu": LLMProvider(
        name="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-flash",
    ),
    "custom": LLMProvider(
        name="custom",
        base_url=None,
        default_model=None,
    ),
}


def resolve_provider() -> str:
    """
    解析当前生效的 provider 名称。

    优先级：
    1. ``LLM_PROVIDER`` 显式设置
    2. ``SILICONFLOW_API_URL`` 含 ``siliconflow.cn`` → siliconflow
    3. ``SILICONFLOW_API_KEY`` 已设 → siliconflow（向后兼容）
    4. 默认 ``openai``
    """
    explicit = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if explicit:
        if explicit in PROVIDERS:
            return explicit
        return "custom"

    legacy_url = (os.getenv("SILICONFLOW_API_URL") or "").strip().lower()
    if "siliconflow.cn" in legacy_url:
        return "siliconflow"

    if (os.getenv("SILICONFLOW_API_KEY") or "").strip():
        return "siliconflow"

    return "openai"


def get_provider_obj(name: Optional[str] = None) -> LLMProvider:
    """
    取得 provider 的 dataclass 实例（不存在时返回 custom）。
    """
    target = (name or resolve_provider()).lower()
    return PROVIDERS.get(target, PROVIDERS["custom"])


def resolve_api_key() -> str:
    """
    解析 API key。

    优先级：``LLM_API_KEY`` > ``OPENAI_API_KEY`` > ``SILICONFLOW_API_KEY`` > ""
    """
    for k in ("LLM_API_KEY", "OPENAI_API_KEY", "SILICONFLOW_API_KEY"):
        v = (os.getenv(k) or "").strip()
        if v:
            return v
    return ""


def resolve_base_url(provider: Optional[str] = None) -> str:
    """
    解析 base_url。

    优先级：``LLM_BASE_URL`` > provider preset 的默认 base_url。
    custom 预设若 ``LLM_BASE_URL`` 未设则 raise ConfigError。
    """
    explicit = (os.getenv("LLM_BASE_URL") or "").strip()
    if explicit:
        return explicit

    obj = get_provider_obj(provider)
    if obj.base_url:
        return obj.base_url

    raise ConfigError("LLM_BASE_URL 未设置（custom 供应商必须显式提供）")


def resolve_model_name(provider: Optional[str] = None) -> str:
    """
    解析模型名。

    优先级：``LLM_MODEL_NAME`` > provider preset 的 default_model。
    custom 预设若 ``LLM_MODEL_NAME`` 未设则 raise ConfigError。
    """
    explicit = (os.getenv("LLM_MODEL_NAME") or "").strip()
    if explicit:
        return explicit

    obj = get_provider_obj(provider)
    if obj.default_model:
        return obj.default_model

    raise ConfigError("LLM_MODEL_NAME 未设置（custom 供应商必须显式提供）")


def get_provider_summary() -> Dict[str, Any]:
    """
    返回当前生效的 provider 配置（供 /api/llm/config 端点使用）。
    """
    provider_name = resolve_provider()
    base_url = resolve_base_url(provider_name)
    model_name = resolve_model_name(provider_name)
    api_key = resolve_api_key()
    return {
        "provider": provider_name,
        "base_url": base_url,
        "model_name": model_name,
        "api_key_set": bool(api_key),
    }


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
