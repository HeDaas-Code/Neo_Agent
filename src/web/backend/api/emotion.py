"""
Emotion API Router
``/api/emotion`` 端点 — Plutchik 8 维情感雷达数据源。

Stage B.3:
- GET /api/emotion/latest?user_id=default
  返回 EmotionResponse 形状的 JSON：
    {
      "cumulative":     {8 维累加},
      "plutchik":       {8 维当下},
      "last_message":   "...",
      "timestamp":      "ISO 8601",
      "user_id":        "default",
      "historical_max": Optional[8 维]
    }
- 失败 / 无数据：按硬约束降级为 200 OK + 全 0 dict + 空字符串
  （不让前端雷达图崩溃）。
- POST /api/emotion/refresh?user_id=default
  主动失效缓存（用于聊天流式结束后强制刷新）。

设计要点：
1. 单点失败不返回 5xx：包装在 try/except，异常路径同样 200 OK + 空 payload。
2. 复用 emotion_service 单例：避免重复加载 EmotionRelationshipAnalyzer。
3. Pydantic v2 schema（EmotionResponse）做响应序列化。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.web.backend.services.emotion_service import emotion_service
except Exception:  # noqa: BLE001
    emotion_service = None  # type: ignore

try:
    from src.web.backend.schemas.emotion import EmotionResponse
except Exception:  # noqa: BLE001
    EmotionResponse = None  # type: ignore


router = APIRouter(prefix="/api/emotion", tags=["emotion"])


# ----------------------------------------------------------------------
# 内部：构造兜底 payload
# ----------------------------------------------------------------------
def _empty_response(user_id: str = "default") -> Dict[str, Any]:
    return {
        "cumulative": {k: 0.0 for k in (
            'joy', 'trust', 'fear', 'surprise',
            'sadness', 'disgust', 'anger', 'anticipation',
        )},
        "plutchik": {k: 0.0 for k in (
            'joy', 'trust', 'fear', 'surprise',
            'sadness', 'disgust', 'anger', 'anticipation',
        )},
        "last_message": "",
        "timestamp": "",
        "user_id": user_id or "default",
        "historical_max": None,
    }


# ----------------------------------------------------------------------
# 1) GET /api/emotion/latest
# ----------------------------------------------------------------------
@router.get("/latest")
async def get_latest_emotion(
    user_id: str = Query(
        "default",
        description="用户标识（当前所有用户共用情感数据；仅作缓存 key 透传）",
    ),
) -> Dict[str, Any]:
    """
    获取最新情感分析结果。

    失败 / 无数据 → 200 OK + 全 0 payload（前端雷达不崩）。
    """
    uid = (user_id or "default").strip() or "default"
    fallback = _empty_response(uid)

    if emotion_service is None:
        return fallback

    try:
        payload = emotion_service.get_latest_emotion(uid)
    except Exception:  # noqa: BLE001
        # 降级：不让前端崩
        return fallback

    if not isinstance(payload, dict):
        return fallback

    # 强制覆盖 user_id 透传
    payload["user_id"] = uid

    # 用 Pydantic schema 校验 / 规范化（可序列化）
    if EmotionResponse is not None:
        try:
            model = EmotionResponse(**payload)
            return model.model_dump()
        except Exception:
            # schema 校验失败：仍返回 raw payload（兜底）
            return payload

    return payload


# ----------------------------------------------------------------------
# 2) POST /api/emotion/refresh
# ----------------------------------------------------------------------
@router.post("/refresh")
async def refresh_emotion_cache(
    user_id: str = Query(
        "default",
        description="用户标识；省略则清空所有用户缓存",
    ),
) -> Dict[str, Any]:
    """
    主动失效指定用户的情感缓存。
    下次 GET /api/emotion/latest 会重新构造 payload。
    """
    if emotion_service is None:
        return {"cleared": 0, "user_id": user_id or "default"}
    try:
        emotion_service.cache_clear(user_id if user_id else None)
    except Exception:  # noqa: BLE001
        return {"cleared": 0, "user_id": user_id or "default"}
    return {"cleared": 1, "user_id": user_id or "default"}


# ----------------------------------------------------------------------
# 3) GET /api/emotion/stats
# ----------------------------------------------------------------------
@router.get("/stats")
async def get_emotion_stats() -> Dict[str, Any]:
    """
    返回情感服务状态（analyzer 是否加载、缓存大小等）。
    """
    if emotion_service is None:
        return {
            "analyzer_loaded": False,
            "wheel_loaded": False,
            "cache_size": 0,
            "version": "1.0.0",
        }
    try:
        return emotion_service.get_stats()
    except Exception:  # noqa: BLE001
        return {
            "analyzer_loaded": False,
            "wheel_loaded": False,
            "cache_size": 0,
            "version": "1.0.0",
        }


__all__ = ["router"]
