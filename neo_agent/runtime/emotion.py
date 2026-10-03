"""Explainable relationship-affect analysis using LangChain and PyVDisk."""
from __future__ import annotations

import json
import re
import uuid
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

    def analyze(self, relationship_id: str, messages: list[dict[str, str]], *,
                character_name: str = "Agent", character_settings: str = "") -> dict[str, Any]:
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
{{"impression":"简短可解释印象","score_change":整数(-3至3),"sentiment":"positive|neutral|negative","relationship_type":"关系阶段","emotional_tone":"基调","key_topics":["话题"],"analysis":"变化理由","dimensions":{{"warmth":0至100,"trust":0至100,"familiarity":0至100,"tension":0至100}}}}
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
        change = max(-3, min(3, int(result.get("score_change", 0))))
        overall = max(0.0, min(100.0, current_score + change))
        record = {
            "relationship_id": relationship_id, "overall_score": overall,
            "previous_score": current_score if previous else None,
            "score_change": change if previous else 0,
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
        self.store.append_event("relationship.emotion.analyzed", {
            "relationship_id": relationship_id, "record_id": record_id,
            "score": overall, "score_change": record["score_change"],
        })
        return saved
