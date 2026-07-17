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

try:
    from src.web.backend.services.neo_bridge import neo_request
except Exception:  # noqa: BLE001
    neo_request = None  # type: ignore


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
# 内部：尝试通过 v4 Amygdala 获取情感数据并转换为 v3 格式
# ----------------------------------------------------------------------
def _convert_v4_emotion_to_v3(v4_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    将 AmygdalaModule.emotion_latest 的返回结构转换为 emotion_service 兼容格式。

    v4 返回字段：timestamp, additive_scores(0-100), plutchik(0-1), dominant
    v3 期望字段：cumulative(0-1), plutchik(0-1), last_message, timestamp, user_id, historical_max
    """
    empty = _empty_response(user_id)
    if not isinstance(v4_data, dict):
        return empty

    plutchik = v4_data.get("plutchik") or {}
    if not isinstance(plutchik, dict):
        plutchik = {}

    additive = v4_data.get("additive_scores") or {}
    if not isinstance(additive, dict):
        additive = {}

    # 将 additive_scores (0-100) 归一化为 cumulative (0-1)
    cumulative = {}
    for k in empty["cumulative"]:
        try:
            cumulative[k] = round(float(additive.get(k, 0.0)) / 100.0, 4)
        except (TypeError, ValueError):
            cumulative[k] = 0.0

    # 确保 plutchik 8 维完整且为 0-1 浮点数
    normalized_plutchik = {}
    for k in empty["plutchik"]:
        try:
            normalized_plutchik[k] = round(float(plutchik.get(k, 0.0)), 4)
        except (TypeError, ValueError):
            normalized_plutchik[k] = 0.0

    return {
        "cumulative": cumulative,
        "plutchik": normalized_plutchik,
        "last_message": "",  # v4 emotion_latest 不返回 last_message
        "timestamp": str(v4_data.get("timestamp") or ""),
        "user_id": user_id,
        "historical_max": None,
    }


async def _try_v4_latest_emotion(user_id: str) -> Optional[Dict[str, Any]]:
    """
    通过 neo_request 调用 limbic.amygdala / emotion_latest。
    成功且返回非空数据时转换为 v3 格式；否则返回 None 让调用方回退。
    """
    if neo_request is None:
        return None

    try:
        response = await neo_request(
            target="limbic.amygdala",
            channel="emotion_latest",
            payload={"user_id": user_id},
        )
    except Exception:  # noqa: BLE001
        return None

    if response is None or response.is_error():
        return None

    v4_data = response.payload
    if not isinstance(v4_data, dict) or not v4_data:
        return None

    return _convert_v4_emotion_to_v3(v4_data, user_id)


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

    优先尝试 v4 Amygdala；失败或无数据时回退到 emotion_service。
    失败 / 无数据 → 200 OK + 全 0 payload（前端雷达不崩）。
    """
    uid = (user_id or "default").strip() or "default"
    fallback = _empty_response(uid)

    # Phase 6: 优先走 v4 神经系统
    try:
        v4_payload = await _try_v4_latest_emotion(uid)
        if isinstance(v4_payload, dict) and v4_payload:
            if EmotionResponse is not None:
                try:
                    model = EmotionResponse(**v4_payload)
                    return model.model_dump()
                except Exception:
                    return v4_payload
            return v4_payload
    except Exception:  # noqa: BLE001
        pass

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
