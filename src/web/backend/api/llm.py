"""
LLM REST API - v3.1.0
======================

端点：
- GET  /api/llm/config    返回当前生效 provider / base_url / model / 是否有效
- POST /api/llm/test      用现配置发一次 ping 调用，验证连通性

设计要点：
1. 复用 ``llm_providers.get_provider_summary()`` + ``get_model_config().is_valid()``，
   避免在 Web 层硬编码供应商逻辑。
2. ``/api/llm/test`` 用 ``LangChainLLM`` 实跑一次调用，latency 用
   ``time.time()`` 简单计时；失败时返回 ``{ok: false, error}``，
   永远不向消费者抛 5xx（验收硬约束）。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.core import llm_providers
except Exception:  # noqa: BLE001
    llm_providers = None  # type: ignore

try:
    from src.core.model_config import get_model_config, ModelType
except Exception:  # noqa: BLE001
    get_model_config = None  # type: ignore
    ModelType = None  # type: ignore

try:
    from src.core.langchain_llm import LangChainLLM
except Exception:  # noqa: BLE001
    LangChainLLM = None  # type: ignore

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def log_warn(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        return _Stub()


router = APIRouter(prefix="/api/llm", tags=["llm"])
debug_logger = get_debug_logger()


# ----------------------------------------------------------------------
# 内部 helper
# ----------------------------------------------------------------------
def _safe_get_summary() -> Dict[str, Any]:
    """
    取得 provider summary，失败时返默认值。
    """
    if llm_providers is None:
        return {
            "provider": "unknown",
            "base_url": "",
            "model_name": "",
            "api_key_set": False,
        }
    try:
        return llm_providers.get_provider_summary()
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_warn('api.llm', f'get_provider_summary 失败: {exc}')
        except Exception:
            pass
        return {
            "provider": llm_providers.resolve_provider() if llm_providers else "unknown",
            "base_url": "",
            "model_name": "",
            "api_key_set": bool(llm_providers.resolve_api_key()) if llm_providers else False,
        }


def _get_timeout() -> int:
    if get_model_config is None:
        return 30
    try:
        cfg = get_model_config()
        return int(getattr(cfg, "vision_llm_timeout", 30) or 30)
    except Exception:
        return 30


# ----------------------------------------------------------------------
# GET /api/llm/config
# ----------------------------------------------------------------------
@router.get("/config")
async def get_llm_config() -> Dict[str, Any]:
    """
    返回当前生效的 LLM 配置概览。
    """
    summary = _safe_get_summary()
    valid = False
    temperature = 0.8
    max_tokens = 2000
    timeout = _get_timeout()

    if get_model_config is not None:
        try:
            cfg = get_model_config()
            valid = bool(cfg.is_valid())
            main = cfg.get_model_config(ModelType.MAIN) if ModelType is not None else {}
            temperature = float(main.get("temperature", 0.8) or 0.8)
            max_tokens = int(main.get("max_tokens", 2000) or 2000)
        except Exception as exc:  # noqa: BLE001
            try:
                debug_logger.log_warn('api.llm', f'get_model_config 失败: {exc}')
            except Exception:
                pass

    return {
        "provider": summary.get("provider", "unknown"),
        "base_url": summary.get("base_url", ""),
        "model_name": summary.get("model_name", ""),
        "api_key_set": bool(summary.get("api_key_set", False)),
        "valid": valid,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
    }


# ----------------------------------------------------------------------
# POST /api/llm/test
# ----------------------------------------------------------------------
class LLMTestRequest(BaseModel):
    prompt: str = Field(default="ping", min_length=1, max_length=2000)


@router.post("/test")
async def test_llm_connection(req: Optional[LLMTestRequest] = None) -> Dict[str, Any]:
    """
    调 LangChainLLM 跑一次 ping 调用，返回 {ok, latency_ms, sample}。
    """
    prompt = (req.prompt if req and req.prompt else "ping").strip() or "ping"

    if get_model_config is None or LangChainLLM is None or ModelType is None:
        return {"ok": False, "error": "LLM components unavailable", "latency_ms": 0}

    try:
        cfg = get_model_config()
        if not cfg.is_valid():
            return {
                "ok": False,
                "error": "API key not configured (set LLM_API_KEY or legacy SILICONFLOW_API_KEY)",
                "latency_ms": 0,
            }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"config error: {exc}", "latency_ms": 0}

    start = time.time()
    try:
        llm = LangChainLLM(ModelType.MAIN)
        content = llm.chat([{"role": "user", "content": prompt}]) or ""
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_error('api.llm', f'LLM chat 失败: {exc}', exc)
        except Exception:
            pass
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": int((time.time() - start) * 1000),
        }

    latency_ms = int((time.time() - start) * 1000)
    return {
        "ok": True,
        "latency_ms": latency_ms,
        "sample_response": (content or "")[:200],
    }


__all__ = ["router"]
