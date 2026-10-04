"""Cognitive gating, action execution results and offline reply arbitration.

This module intentionally stores only concise structured decisions; it never
persists model chain-of-thought or raw tool arguments/results.
"""
from __future__ import annotations

import ast
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


@dataclass(frozen=True)
class CognitionDecision:
    intent: str = "conversation"
    action_needed: bool = False
    reply_strategy: Literal["reply", "clarify", "delay", "silence"] = "reply"
    confidence: float = 0.5
    relationship_signal: str = "neutral"
    affective_state: str = "neutral"
    action_rationale: str = ""

    @classmethod
    def from_mapping(cls, value: Any) -> "CognitionDecision":
        if not isinstance(value, dict):
            return cls()
        strategy = value.get("reply_strategy", "reply")
        if strategy not in {"reply", "clarify", "delay", "silence"}:
            strategy = "reply"
        try:
            confidence = max(0.0, min(1.0, float(value.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        action_value = value.get("action_needed", False)
        action_needed = action_value is True or str(action_value).strip().casefold() in {"true", "yes", "1"}
        return cls(
            intent=str(value.get("intent", "conversation"))[:80],
            action_needed=action_needed,
            reply_strategy=strategy, confidence=confidence,
            relationship_signal=str(value.get("relationship_signal", "neutral"))[:40],
            affective_state=str(value.get("affective_state", "neutral"))[:40],
            action_rationale=str(value.get("action_rationale", ""))[:240],
        )


@dataclass(frozen=True)
class ActionResult:
    tool_name: str
    capability: str
    status: Literal["succeeded", "failed", "denied"]
    risk: Literal["low", "high"] = "low"
    summary: str = ""

    def public_dict(self) -> dict[str, str]:
        # Persona wording receives only the outcome and a curated public fact.
        # Internal tool names, capabilities and execution metadata stay in audit.
        return {"status": self.status, "summary": self.summary[:300]}


@dataclass(frozen=True)
class ReplyCandidate:
    message_id: str
    group_id: str
    speaker_id: str
    text: str
    relevance: float
    confidence: float
    activity: float
    cooldown: bool
    decision: Literal["reply", "delay", "silence"]
    reason: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    group_id: str
    speaker_id: str
    text: str
    addressed_to_agent: bool = False
    relevance: float | None = None
    confidence: float = 0.75
    activity: float = 0.5
    cooldown: bool = False
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GroupReplyGate:
    """Deterministic, replayable first-pass group reply/quiet gate."""

    def evaluate(self, incoming: IncomingMessage, *, relevance: float | None = None,
                 confidence: float | None = None, activity: float | None = None,
                 cooldown: bool | None = None) -> ReplyCandidate:
        text = incoming.text.strip()
        if relevance is None:
            relevance = incoming.relevance
        if relevance is None:
            relevance = 1.0 if incoming.addressed_to_agent else (0.65 if "?" in text or "？" in text else 0.35)
        confidence = incoming.confidence if confidence is None else confidence
        activity = incoming.activity if activity is None else activity
        cooldown = incoming.cooldown if cooldown is None else cooldown
        relevance = max(0.0, min(1.0, float(relevance)))
        confidence = max(0.0, min(1.0, float(confidence)))
        activity = max(0.0, min(1.0, float(activity)))
        if cooldown and not incoming.addressed_to_agent:
            decision, reason = "silence", "cooldown_active"
        elif incoming.addressed_to_agent and confidence >= 0.45:
            decision, reason = "reply", "direct_address"
        elif confidence < 0.45 or relevance < 0.25:
            decision, reason = "silence", "low_relevance_or_confidence"
        elif confidence < 0.65:
            decision, reason = "delay", "uncertain_intent"
        elif activity > 0.9 and relevance < 0.8:
            decision, reason = "delay", "group_is_busy"
        else:
            decision, reason = "reply", "relevant_message"
        return ReplyCandidate(incoming.message_id, incoming.group_id, incoming.speaker_id,
                             incoming.text, relevance, confidence, activity, cooldown,
                             decision, reason)

    def replay(self, messages: list[IncomingMessage], *, cooldown_ids: set[str] | None = None) -> list[ReplyCandidate]:
        cooldown_ids = cooldown_ids or set()
        return [self.evaluate(item, cooldown=item.cooldown or item.group_id in cooldown_ids) for item in messages]


HIGH_RISK_MARKERS = ("delete", "remove", "overwrite", "install", "enable", "send", "permission", "secret", "token", "key", "删除", "覆盖", "安装", "启用", "发送", "权限", "密钥", "插件")

def risk_for_tool(tool_name: str, capabilities: tuple[str, ...] | list[str] = ()) -> str:
    text = (tool_name + " " + " ".join(capabilities)).casefold()
    # Generic filesystem write capability can overwrite or remove data; classify
    # conservatively so its audit always carries enhanced-risk metadata.
    if "sandbox.fs.write" in text or "nps.create" in text or "plugin.install" in text:
        return "high"
    return "high" if any(marker in text for marker in HIGH_RISK_MARKERS) else "low"


def safe_result_summary(value: Any, *, failed: bool = False) -> str:
    """Reduce execution output to a bounded user-safe fact, not a raw trace."""
    if failed:
        return "操作未能完成。"
    parsed = value
    if isinstance(value, str):
        encoded = value.strip()
        try:
            parsed = json.loads(encoded)
        except (ValueError, TypeError):
            try:
                candidate = ast.literal_eval(encoded)
                parsed = candidate if isinstance(candidate, dict) else ""
            except (ValueError, SyntaxError, TypeError):
                # Unstructured plugin output is not safe to forward to the
                # persona model, even if it looks like ordinary prose.
                parsed = ""
    if isinstance(parsed, dict):
        if parsed.get("status") in {"failed", "error"} or parsed.get("ok") is False or "error" in parsed:
            return "操作未能完成。"
        text = next((parsed[key].strip() for key in ("summary", "message")
                     if isinstance(parsed.get(key), str) and parsed[key].strip()), "操作已完成。")
    else:
        text = "操作已完成。"
    text = re.sub(r"(?i)(api[_-]?key|token|secret|password|authorization|bearer)\s*[:=]\s*\S+", r"\1=[已隐藏]", text)
    text = re.sub(r"(?i)(/[A-Za-z0-9_.~/-]+|[A-Za-z]:\\[^\s,;]+)", "[路径已隐藏]", text)
    text = re.sub(r"\s+", " ", text)
    # Prevent an accidental implementation identifier in a plugin summary from
    # revealing the underlying tool operation to the persona model.
    if "_" in text:
        text = re.sub(r"\b[a-z][a-z0-9_]{2,}\b", "[内部标识已隐藏]", text)
    return text[:300] or "操作已完成。"


class CognitionService:
    """Model-backed structured cognitive assessment with safe fallback."""
    def __init__(self, model: Any | None = None):
        self.model = model

    def assess(self, *, message: str, context: str = "", personality: str = "", direct_chat: bool = False) -> CognitionDecision:
        if self.model is None:
            return CognitionDecision()
        from langchain_core.messages import HumanMessage, SystemMessage
        prompt = (
            "Return only a JSON object with intent, action_needed (boolean), "
            "reply_strategy (reply|clarify|delay|silence), confidence (0..1), "
            "relationship_signal (positive|neutral|negative) and affective_state (brief temporary mood label). "
            "Do not output rationale or chain of thought. Decide whether a declared "
            "capability is needed; set action_needed only for clear user intent and sufficient details. "
            "Use clarify when required information is missing.\n"
            f"Direct one-to-one chat: {direct_chat}; if true, strategy must be reply or clarify.\n"
            f"Character: {personality[:2000]}\nContext: {context[-6000:]}\nUser: {message[:4000]}"
        )
        try:
            response = self.model.invoke([
                SystemMessage(content="You are a conservative, structured cognitive gate. Output JSON only."),
                HumanMessage(content=prompt),
            ])
            raw = getattr(response, "content", response)
            if isinstance(raw, list):
                raw = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw)
            match = re.search(r"\{[\s\S]*\}", str(raw))
            decision = CognitionDecision.from_mapping(json.loads(match.group()) if match else {})
            if direct_chat and decision.reply_strategy in {"delay", "silence"}:
                decision = CognitionDecision.from_mapping({**decision.__dict__, "reply_strategy": "reply"})
            return decision
        except Exception:
            return CognitionDecision()
