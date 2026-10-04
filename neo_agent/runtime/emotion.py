"""Explainable relationship-affect analysis using LangChain and PyVDisk."""
from __future__ import annotations

import json
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any


class EmotionService:
    """Persist a structured, evidence-linked relationship impression timeline."""

    def __init__(self, store: Any, model: Any | None = None):
        self.store = store
        self.model = model

    def history(self, relationship_id: str | None = None) -> list[dict[str, Any]]:
        rows = self.store.emotion_history(relationship_id)
        return sorted(rows, key=lambda row: row.get("created_at", ""), reverse=True)

    def record_cognitive_state(self, relationship_id: str, *, signal: str,
                               affective_state: str, confidence: float,
                               round_id: str) -> dict[str, Any]:
        """Store one turn's temporary affect and gate durable changes by evidence.

        A round ID is idempotent. Only three distinct, same-direction rounds
        with confidence >= .8 commit a bounded relationship change.
        """
        signal = str(signal).strip().casefold()
        direction = 1 if signal in {"positive", "warm", "trusting", "积极", "正向"} else (
            -1 if signal in {"negative", "distant", "tense", "消极", "负向"} else 0)
        confidence = max(0.0, min(1.0, float(confidence)))
        tone = str(affective_state or "neutral")[:80]
        self.store.add_emotion(relationship_id, tone, float(direction),
                               evidence=f"conversation_round:{round_id}")
        ledger_path = f"/runtime/relationship-evidence/{hashlib.sha256(relationship_id.encode()).hexdigest()[:16]}.json"
        ledger = self.store.read_json(ledger_path, default={"relationship_id": relationship_id, "rounds": {}})
        rounds = dict(ledger.get("rounds", {}))
        if direction and confidence >= 0.8:
            rounds.setdefault(str(round_id), {"change": direction, "confidence": confidence})
        evidence = [row for row in rounds.values() if int(row.get("change", 0)) == direction and direction != 0]
        committed = direction != 0 and confidence >= 0.8 and len(evidence) >= 3
        change = max(-3, min(3, direction)) if committed else 0
        if committed:
            rounds = {}
            current = self.store.get_document("relationships", relationship_id) or {"score": 0, "interactions": []}
            score = max(-100.0, min(100.0, float(current.get("score", 0)) + change))
            interactions = list(current.get("interactions", []))
            interactions.append({"note": "多轮认知门控证据确认", "delta": change,
                                 "evidence_rounds": len(evidence), "confidence": confidence})
            self.store.save_document("relationships", relationship_id, {
                **current, "score": score, "interactions": interactions[-200:],
                "last_affect_state": tone, "last_affect_at": datetime.now(timezone.utc).isoformat(),
            })
        self.store.write_json(ledger_path, {"relationship_id": relationship_id, "rounds": rounds})
        self.store.append_event("relationship.cognitive_state.recorded", {
            "relationship_id": relationship_id, "round_id": str(round_id),
            "signal": "positive" if direction > 0 else "negative" if direction < 0 else "neutral",
            "confidence": confidence, "evidence_count": len(evidence),
            "persistent_update": committed, "score_change": change,
        })
        return {"affective_state": tone, "evidence_count": len(evidence),
                "persistent_update": committed, "score_change": change}

    def analyze(self, relationship_id: str, messages: list[dict[str, str]], *,
                character_name: str = "Agent", character_settings: str = "",
                round_id: str | None = None, confidence: float | None = None) -> dict[str, Any]:
        if self.model is None:
            raise RuntimeError("尚未配置 LangChain 模型，无法分析情绪关系")
        transcript = [row for row in messages if row.get("role") in {"user", "assistant"} and str(row.get("content", "")).strip()]
        if len(transcript) < 2:
            raise ValueError("至少需要一轮完整对话才能分析关系")
        previous = self.history(relationship_id)
        current_score = float(previous[0].get("overall_score", previous[0].get("score", 50))) if previous else 50.0
        dialogue = "\n".join(f"{row['role']}: {str(row['content'])[:2000]}" for row in transcript[-30:])
        from langchain_core.messages import HumanMessage, SystemMessage
        prompt = f"""分析角色与用户的关系印象。只依据给出的对话，不要将推测写成事实。输出单个 JSON 对象，字段：
{{"impression":"简短可解释印象","score_change":整数(-3至3),"confidence":0至1,"sentiment":"positive|neutral|negative","relationship_type":"关系阶段","emotional_tone":"基调","key_topics":["话题"],"analysis":"简短证据摘要","dimensions":{{"warmth":0至100,"trust":0至100,"familiarity":0至100,"tension":0至100}}}}
角色：{character_name}。设定：{character_settings[:2000]}。此前关系分：{current_score:.1f}/100。
近期对话：\n{dialogue}"""
        response = self.model.invoke([SystemMessage(content="你是谨慎、证据导向的关系分析器。只输出 JSON。"), HumanMessage(content=prompt)])
        raw = getattr(response, "content", response)
        if isinstance(raw, list):
            raw = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw)
        match = re.search(r"\{[\s\S]*\}", str(raw))
        if not match:
            raise ValueError("模型未返回有效的 JSON 对象")
        result = json.loads(match.group(0))
        dimensions = result.get("dimensions", {})
        if not isinstance(dimensions, dict):
            raise ValueError("dimensions 必须是对象")
        dims = {key: max(0, min(100, float(dimensions.get(key, 50))))
                for key in ("warmth", "trust", "familiarity", "tension")}
        proposed = max(-3, min(3, int(result.get("score_change", 0))))
        try:
            confidence_value = max(0.0, min(1.0, float(confidence if confidence is not None else result.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence_value = 0.0
        evidence_round = str(round_id or hashlib.sha256(dialogue.encode()).hexdigest()[:24])
        ledger_path = f"/runtime/relationship-evidence/{hashlib.sha256(relationship_id.encode()).hexdigest()[:16]}.json"
        ledger = self.store.read_json(ledger_path, default={"relationship_id": relationship_id, "rounds": {}})
        rounds = dict(ledger.get("rounds", {}))
        if confidence_value >= 0.8 and proposed:
            rounds[evidence_round] = {"change": proposed, "confidence": confidence_value}
        same_direction = [row for row in rounds.values() if (int(row.get("change", 0)) > 0) == (proposed > 0) and int(row.get("change", 0)) != 0]
        committed = len(same_direction) >= 3 and proposed != 0 and confidence_value >= 0.8
        change = proposed if committed else 0
        if committed:
            rounds = {}
        self.store.write_json(ledger_path, {"relationship_id": relationship_id, "rounds": rounds})
        overall = max(0.0, min(100.0, current_score + change))
        record = {
            "relationship_id": relationship_id, "overall_score": overall,
            "previous_score": current_score if previous else None,
            "score_change": change if previous else 0,
            "proposed_score_change": proposed, "confidence": confidence_value,
            "evidence_round": evidence_round, "evidence_count": len(same_direction),
            "persistent_update": committed,
            "sentiment": str(result.get("sentiment", "neutral")),
            "relationship_type": str(result.get("relationship_type", "初识" if not previous else "熟悉中")),
            "emotional_tone": str(result.get("emotional_tone", "中性")),
            "impression": str(result.get("impression", "")),
            "analysis": str(result.get("analysis", "")),
            "key_topics": [str(topic) for topic in result.get("key_topics", [])][:20],
            "dimensions": dims, "evidence": dialogue,
            "message_count": len(transcript), "created_at": datetime.now(timezone.utc).isoformat(),
        }
        record_id = uuid.uuid4().hex[:20]
        saved = self.store.save_document("emotions", record_id, record)
        if committed:
            relationship = self.store.get_document("relationships", relationship_id) or {
                "score": 0.0, "interactions": [],
            }
            relationship_score = max(-100.0, min(100.0, float(relationship.get("score", 0.0)) + change))
            interactions = list(relationship.get("interactions", []))
            interactions.append({
                "note": "经多轮高置信度情绪证据确认的关系变化",
                "delta": change, "evidence_rounds": len(same_direction),
                "confidence": confidence_value, "emotion_record_id": record_id,
            })
            self.store.save_document("relationships", relationship_id, {
                **relationship, "score": relationship_score, "interactions": interactions[-200:],
                "last_affect_score": overall, "last_affect_state": record["emotional_tone"],
                "last_affect_at": record["created_at"],
            })
        self.store.append_event("relationship.emotion.analyzed", {
            "relationship_id": relationship_id, "record_id": record_id,
            "score": overall, "score_change": record["score_change"],
            "persistent_update": committed, "evidence_count": len(same_direction),
            "confidence": confidence_value,
        })
        return saved
