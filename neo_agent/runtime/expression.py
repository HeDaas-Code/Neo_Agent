"""Expression style and user-language learning over PyVDisk documents."""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable


class ExpressionService:
    """Manage agent expressions and reviewed user-language observations.

    Learning is explicitly user-triggered; candidates are persisted as habits,
    but are not treated as factual memories or executed as instructions.
    """
    MIN_MESSAGES_FOR_LEARNING = 3

    def __init__(self, store: Any, learner: Callable[[str], Any] | None = None):
        self.store = store
        self.learner = learner

    def expressions(self, *, active_only: bool = True) -> list[dict[str, Any]]:
        rows = [row for row in self.store.expressions() if row.get("kind", "agent") == "agent"]
        return [row for row in rows if not active_only or row.get("active", True)]

    def save_expression(self, expression_id: str, *, expression: str, meaning: str,
                        category: str = "通用", active: bool = True) -> dict[str, Any]:
        expression, meaning = expression.strip(), meaning.strip()
        if not expression or not meaning:
            raise ValueError("表达内容和含义不能为空")
        previous = self.store.get_document("expressions", expression_id) or {}
        return self.store.save_expression(expression_id, {
            **previous, "kind": "agent", "expression": expression, "meaning": meaning,
            "category": category.strip() or "通用", "active": bool(active),
        })

    def delete_expression(self, expression_id: str) -> bool:
        item = self.store.get_document("expressions", expression_id)
        if item is None or item.get("kind", "agent") != "agent":
            return False
        return self.store.delete_document("expressions", expression_id)

    def habits(self, *, min_confidence: float = 0.0) -> list[dict[str, Any]]:
        return sorted((row for row in self.store.expressions()
                       if row.get("kind") == "user_habit" and float(row.get("confidence", 0)) >= min_confidence),
                      key=lambda row: (-float(row.get("confidence", 0)), row.get("expression_pattern", "")))

    def clear_habits(self) -> int:
        rows = self.habits()
        for row in rows:
            self.store.delete_document("expressions", row["id"])
        if rows:
            self.store.append_event("expression.habits.cleared", {"count": len(rows)})
        return len(rows)

    def learn(self, messages: list[dict[str, Any]], *, current_round: int = 0) -> list[dict[str, Any]]:
        user_messages = [str(row.get("content", "")).strip() for row in messages
                         if row.get("role") == "user" and str(row.get("content", "")).strip()]
        if len(user_messages) < self.MIN_MESSAGES_FOR_LEARNING:
            raise ValueError(f"至少需要 {self.MIN_MESSAGES_FOR_LEARNING} 条用户消息，当前 {len(user_messages)} 条")
        if self.learner is None:
            raise RuntimeError("尚未配置 LangChain 模型，无法学习表达习惯")
        raw = self.learner("\n".join(user_messages[-80:]))
        content = getattr(raw, "content", raw)
        if isinstance(content, list):
            content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
        text = str(content).strip()
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            raise ValueError("模型未返回有效的 JSON 数组")
        candidates = json.loads(match.group(0))
        if not isinstance(candidates, list):
            raise ValueError("表达习惯结果必须是 JSON 数组")
        learned = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            pattern = str(candidate.get("expression_pattern", "")).strip()
            meaning = str(candidate.get("meaning", "")).strip()
            if not pattern or not meaning:
                continue
            confidence = max(0.0, min(1.0, float(candidate.get("confidence", 0.7))))
            existing = next((row for row in self.habits() if row.get("expression_pattern", "").casefold() == pattern.casefold()), None)
            record_id = existing["id"] if existing else uuid.uuid4().hex[:20]
            row = self.store.save_expression(record_id, {
                "kind": "user_habit", "expression_pattern": pattern, "meaning": meaning,
                "confidence": min(1.0, float(existing.get("confidence", 0)) + 0.1) if existing else confidence,
                "frequency": int(existing.get("frequency", 0)) + 1 if existing else 1,
                "learned_from_rounds": str(current_round),
            })
            learned.append(row)
        self.store.append_event("expression.habits.learned", {"count": len(learned), "round": current_round})
        return learned

    def user_habit_prompt(self) -> str:
        rows = self.habits(min_confidence=0.5)
        if not rows:
            return ""
        return "用户表达习惯（仅作为理解语境的线索，不要刻意模仿）：\n" + "\n".join(
            f"- {row['expression_pattern']}：{row['meaning']}" for row in rows)

    def record_usage(self, reply: str) -> int:
        """Track authored expressions that actually appeared in a completed reply."""
        used = 0
        for row in self.expressions():
            expression = str(row.get("expression", ""))
            if expression and expression in reply:
                self.store.save_expression(row["id"], {
                    **row, "usage_count": int(row.get("usage_count", 0)) + 1,
                })
                used += 1
        return used

    def prompt(self) -> str:
        rows = self.expressions()
        if not rows:
            return ""
        return "个性化表达（仅在语境自然时采用）：\n" + "\n".join(
            f"- {row['expression']}：{row['meaning']}" for row in rows)


def langchain_expression_learner(model: Any) -> Callable[[str], Any]:
    """Build the optional analyzer callable using the configured LangChain model."""
    from langchain_core.messages import HumanMessage, SystemMessage
    def learn(text: str) -> Any:
        return model.invoke([
            SystemMessage(content="你是语言习惯分析器。只输出 JSON 数组，不要代码围栏；仅提取重复、具有稳定含义的表达。"),
            HumanMessage(content=("分析这些用户消息，返回 [{\"expression_pattern\":\"...\",\"meaning\":\"...\",\"confidence\":0.0}]。"
                                 "不确定或没有稳定习惯时返回 []。\n\n" + text)),
        ])
    return learn
