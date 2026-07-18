"""
Emotion service module.
情感雷达后端服务 - 包装 EmotionRelationshipAnalyzer + PlutchikEmotionWheel，
为 /api/emotion/latest 和 WebSocket emotion_update 推送提供：
  - 8 维累加评分（关系状态维度）
  - 8 维 Plutchik 强度（当下情绪维度）
  - 最近一次分析的时间戳 / 用户消息

设计要点：
1. 懒加载 emotion_analyzer：避免 Web 启动时强制实例化 ChatAgent / LLM
2. 缓存最近一次结果（避免每次 HTTP 请求都跑 LLM / 走 DB）
3. 失败/缺失时一律降级为全 0 字典 + 空字符串，不抛异常
4. 进程内单例：emotion_service = EmotionService()
"""

from __future__ import annotations

import sys
import threading
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


PLUTCHIK_KEYS = (
    'joy', 'trust', 'fear', 'surprise',
    'sadness', 'disgust', 'anger', 'anticipation',
)


def _empty_eight() -> Dict[str, float]:
    return {k: 0.0 for k in PLUTCHIK_KEYS}


def _empty_payload(user_id: str = "default") -> Dict[str, Any]:
    """失败/无数据时的兜底 payload。"""
    return {
        "cumulative": _empty_eight(),
        "plutchik": _empty_eight(),
        "last_message": "",
        "timestamp": "",
        "user_id": user_id or "default",
        "historical_max": None,
    }


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_dict(d: Any) -> Dict[str, float]:
    """把任意 dict 转成 8 维 dict；缺键补 0.0。"""
    out = _empty_eight()
    if not isinstance(d, dict):
        return out
    for k in PLUTCHIK_KEYS:
        if k in d:
            out[k] = _coerce_float(d[k], 0.0)
    return out


class EmotionService:
    """
    情感雷达后端服务（Web 端入口）

    Attributes:
        _cache: 进程内缓存 {user_id: (ts, payload)}，避免每次 HTTP 都跑 LLM
        _lock: 写缓存的轻量锁
        _analyzer: 懒加载的 EmotionRelationshipAnalyzer 实例
        _wheel: 懒加载的 PlutchikEmotionWheel 实例
    """

    # 缓存有效期（秒）：同一用户在这个窗口内的请求直接走缓存
    CACHE_TTL_SECONDS = 30.0

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._analyzer: Optional[Any] = None
        self._wheel: Optional[Any] = None
        # 主动尝试一次懒加载（失败时静默降级）
        self._try_init()

    # ------------------------------------------------------------------
    # 懒加载 EmotionRelationshipAnalyzer / PlutchikEmotionWheel
    # ------------------------------------------------------------------
    def _try_init(self) -> None:
        try:
            from src.core.emotion_analyzer import (  # type: ignore
                EmotionRelationshipAnalyzer,
                PlutchikEmotionWheel,
            )
            self._analyzer = EmotionRelationshipAnalyzer()
            self._wheel = PlutchikEmotionWheel(db_manager=self._analyzer.db)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[EmotionService] 情感分析器初始化失败，将以无 analyzer 模式运行: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            self._analyzer = None
            self._wheel = None

    def _ensure(self) -> bool:
        """确保 analyzer / wheel 可用。失败时返回 False。"""
        if self._analyzer is None or self._wheel is None:
            self._try_init()
        return self._analyzer is not None and self._wheel is not None

    # ------------------------------------------------------------------
    # 对外：缓存读写
    # ------------------------------------------------------------------
    def _cache_get(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._cache.get(user_id)
            if not entry:
                return None
            ts = float(entry.get("ts", 0.0))
            if (time.time() - ts) > self.CACHE_TTL_SECONDS:
                # 缓存过期
                self._cache.pop(user_id, None)
                return None
            return entry.get("payload")

    def _cache_put(self, user_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            self._cache[user_id] = {"ts": time.time(), "payload": dict(payload)}
            # 兜底：cache 体积上限 64
            if len(self._cache) > 64:
                # 删除最旧的一条
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].get("ts", 0.0),
                )
                self._cache.pop(oldest_key, None)

    def cache_clear(self, user_id: Optional[str] = None) -> None:
        """主动失效缓存（测试 / 显式刷新）。"""
        with self._lock:
            if user_id is None:
                self._cache.clear()
            else:
                self._cache.pop(user_id, None)

    # ------------------------------------------------------------------
    # 对外：构造 payload
    # ------------------------------------------------------------------
    def get_latest_emotion(self, user_id: str = "default") -> Dict[str, Any]:
        """
        返回最新的情感分析结果。

        Args:
            user_id: 用户标识（当前实现下所有用户共用一份全局情感数据，
                user_id 仅作为返回字段透传 + 缓存 key 使用）

        Returns:
            dict:
              {
                "cumulative":      {joy, trust, fear, surprise, sadness, disgust, anger, anticipation}  # 8 维累加
                "plutchik":        {同 8 维}  # 0-1 归一化的当下情绪
                "last_message":    str  # 最近一次参与分析的用户消息（尽力从 DB 拼出）
                "timestamp":       str  # ISO 8601
                "user_id":         str
                "historical_max":  Optional[dict]  # 8 维历史最高，没有则为 None
              }
        """
        uid = (user_id or "default").strip() or "default"

        # 1) 命中缓存：直接返回
        cached = self._cache_get(uid)
        if cached is not None:
            return dict(cached)

        # 2) 没命中 / 过期：尝试重新构造
        payload = self._build_payload(uid)
        self._cache_put(uid, payload)
        return dict(payload)

    def _build_payload(self, user_id: str) -> Dict[str, Any]:
        """实际从 analyzer 拉数据；失败时返回空 payload。"""
        empty = _empty_payload(user_id)
        if not self._ensure():
            return empty

        # ---- 2.1) 拉取最近一次关系型分析（DB） ----
        try:
            latest = self._analyzer.get_latest_emotion()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            latest = None

        # ---- 2.2) 计算 cumulative（关系状态维度） ----
        cumulative = self._derive_cumulative(latest)

        # ---- 2.3) 计算 plutchik（当下情绪维度） ----
        plutchik = self._derive_plutchik()

        # ---- 2.4) last_message / timestamp ----
        timestamp = ""
        last_message = ""
        if isinstance(latest, dict):
            timestamp = str(latest.get("timestamp") or latest.get("created_at") or "")
            # impression 包含历史印象；不直接作为 last_message。
            # last_message 优先从短时记忆 DB 推断，否则留空。
        last_message = self._derive_last_message(latest)

        # ---- 2.5) historical_max（8 维历史最高） ----
        historical_max = self._derive_historical_max(cumulative, plutchik)

        return {
            "cumulative": cumulative,
            "plutchik": plutchik,
            "last_message": last_message,
            "timestamp": timestamp,
            "user_id": user_id,
            "historical_max": historical_max,
        }

    # ------------------------------------------------------------------
    # 内部：维度推导
    # ------------------------------------------------------------------
    def _derive_cumulative(self, latest: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """
        把 relationship_type / emotional_tone / overall_score 映射成
        8 维 0-1 归一化评分。

        规则（启发式，无 LLM）：
          - 整体评分（overall_score 0-100）→ 主导正向情绪的权重
          - emotional_tone / sentiment 调整正负向分布
        """
        out = _empty_eight()
        if not isinstance(latest, dict):
            return out

        try:
            overall = _coerce_float(latest.get("overall_score"), 0.0)
        except Exception:
            overall = 0.0
        # 0-100 → 0-1
        score_norm = max(0.0, min(1.0, overall / 100.0))

        tone = str(latest.get("emotional_tone") or "").strip()
        sentiment = str(latest.get("sentiment") or "").strip().lower()
        relationship = str(latest.get("relationship_type") or "").strip()

        # 主导：积极 / 消极 tone → 8 维分布
        is_positive = (
            tone in ("积极", "正面", "乐观", "友好")
            or sentiment in ("positive", "pos")
        )
        is_negative = (
            tone in ("消极", "负面", "悲观", "紧张")
            or sentiment in ("negative", "neg")
        )

        if is_positive:
            # 积极：joy / trust / anticipation 为主，surprise 副
            out["joy"] = round(score_norm * 0.9, 4)
            out["trust"] = round(score_norm * 0.7, 4)
            out["anticipation"] = round(score_norm * 0.5, 4)
            out["surprise"] = round(score_norm * 0.3, 4)
        elif is_negative:
            # 消极：sadness / anger / fear / disgust 为主
            out["sadness"] = round(score_norm * 0.9, 4)
            out["anger"] = round(score_norm * 0.6, 4)
            out["fear"] = round(score_norm * 0.5, 4)
            out["disgust"] = round(score_norm * 0.4, 4)
        else:
            # 中性：信任 / 期待 + 轻微 4 维
            out["trust"] = round(0.4 + score_norm * 0.3, 4)
            out["anticipation"] = round(0.3 + score_norm * 0.2, 4)
            out["joy"] = round(0.2 + score_norm * 0.2, 4)
            out["surprise"] = round(0.1 + score_norm * 0.1, 4)

        # 关系类型微调
        if relationship in ("知己", "亲密朋友", "好友"):
            out["trust"] = min(1.0, out["trust"] + 0.15)
            out["joy"] = min(1.0, out["joy"] + 0.1)
        elif relationship in ("初识", "陌生人"):
            out["fear"] = min(1.0, out["fear"] + 0.1)
            out["surprise"] = min(1.0, out["surprise"] + 0.1)

        return out

    def _derive_plutchik(self) -> Dict[str, float]:
        """
        从 PlutchikEmotionWheel 拉取衰减后的 8 维强度；
        无 wheel 或失败时返回全 0。
        """
        if self._wheel is None:
            return _empty_eight()
        try:
            # wheel 状态在 ChatAgent 里维护；这里只读 _last_emotion_wheel_state
            state = self._read_wheel_state()
            if not state:
                return _empty_eight()
            # 应用衰减
            try:
                state = self._wheel.decay_emotions(state)
            except Exception:
                pass
            return _safe_dict(state.get("emotions") or {})
        except Exception:  # noqa: BLE001
            return _empty_eight()

    def _read_wheel_state(self) -> Optional[Dict[str, Any]]:
        """
        读取 PlutchikEmotionWheel 当前状态。
        优先从 ChatAgent 进程内单例拿；拿不到再尝试 metadata 表里的快照。
        """
        # 1) 尝试从 ChatAgent 拿（如果有）
        try:
            from src.core.chat_agent import ChatAgent  # type: ignore
            agent = ChatAgent()
            state = getattr(agent, "_last_emotion_wheel_state", None)
            if isinstance(state, dict):
                return state
        except Exception:
            pass

        # 2) 尝试从 metadata 表读快照（key='emotion_wheel_state'）
        try:
            db = None
            if self._wheel is not None and getattr(self._wheel, "db", None) is not None:
                db = self._wheel.db
            elif self._analyzer is not None and getattr(self._analyzer, "db", None) is not None:
                db = self._analyzer.db
            if db is not None and hasattr(db, "get_metadata"):
                raw = db.get_metadata("emotion_wheel_state")
                if raw:
                    import json
                    try:
                        return json.loads(raw) if isinstance(raw, str) else dict(raw)
                    except Exception:
                        return None
        except Exception:
            return None
        return None

    def _derive_last_message(self, latest: Optional[Dict[str, Any]]) -> str:
        """
        尽力从短时记忆中取最近一条用户消息。
        失败时返回空字符串。
        """
        if not isinstance(latest, dict):
            return ""
        # 如果 latest 字典里直接带了 last_message 字段（兜底），优先用
        direct = latest.get("last_message")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()[:2000]
        # 尝试从 short_term_memory 表里查最近 1 条 user 消息
        try:
            db = None
            if self._analyzer is not None and getattr(self._analyzer, "db", None) is not None:
                db = self._analyzer.db
            if db is None:
                return ""
            method = getattr(db, "get_recent_messages", None)
            if method is None:
                return ""
            try:
                rows = method(limit=1, role="user")  # type: ignore[arg-type]
            except TypeError:
                # 兼容不同的方法签名
                rows = method(limit=1)
            if not rows:
                return ""
            row = rows[0] if isinstance(rows, list) else rows
            if isinstance(row, dict):
                content = row.get("content") or row.get("message") or ""
            else:
                content = str(getattr(row, "content", "") or "")
            return str(content).strip()[:2000]
        except Exception:
            return ""

    def _derive_historical_max(
        self,
        cumulative: Dict[str, float],
        plutchik: Dict[str, float],
    ) -> Optional[Dict[str, float]]:
        """
        尽力从 emotion_history 表聚合 8 维历史最高。
        当前没有按维度存 Plutchik 历史 → 直接用 cumulative + plutchik 元素最大值。
        """
        try:
            db = None
            if self._analyzer is not None and getattr(self._analyzer, "db", None) is not None:
                db = self._analyzer.db
            if db is None:
                return None
            history = db.get_emotion_history() if hasattr(db, "get_emotion_history") else []
            if not history:
                return None
            # 简单策略：取最近 20 条的整体评分，映射到 8 维
            scores: list = []
            for h in history[:20]:
                if not isinstance(h, dict):
                    continue
                try:
                    s = _coerce_float(h.get("overall_score"), 0.0)
                except Exception:
                    continue
                scores.append(max(0.0, min(1.0, s / 100.0)))
            if not scores:
                return None
            peak = max(scores)
            # 按 cumulative 模板放大
            return {k: round(min(1.0, v + peak * 0.2), 4)
                    for k, v in cumulative.items()}
        except Exception:
            return None

    # ------------------------------------------------------------------
    # 对外：emit（WebSocket emotion_update 推文的 helper）
    # ------------------------------------------------------------------
    def build_emotion_update_event(
        self, user_id: str = "default"
    ) -> Dict[str, Any]:
        """
        为 WebSocket 推送构造 emotion_update 事件 payload。

        返回 dict：
          {
            "type": "emotion_update",
            "data": { 8 维 plutchik },
            "cumulative": { 8 维 },
            "historical_max": Optional[dict],
            "last_message": str,
            "timestamp": str,
            "user_id": str,
          }
        """
        payload = self.get_latest_emotion(user_id)
        return {
            "type": "emotion_update",
            "data": dict(payload.get("plutchik") or {}),
            "cumulative": dict(payload.get("cumulative") or {}),
            "historical_max": payload.get("historical_max"),
            "last_message": payload.get("last_message", ""),
            "timestamp": payload.get("timestamp", ""),
            "user_id": payload.get("user_id", user_id),
        }

    def get_stats(self) -> Dict[str, Any]:
        """返回服务状态。"""
        return {
            "analyzer_loaded": self._analyzer is not None,
            "wheel_loaded": self._wheel is not None,
            "cache_size": len(self._cache),
            "cache_ttl_seconds": self.CACHE_TTL_SECONDS,
            "version": "1.0.0",
        }


# 全局单例
emotion_service = EmotionService()


__all__ = [
    "EmotionService",
    "emotion_service",
    "PLUTCHIK_KEYS",
]
