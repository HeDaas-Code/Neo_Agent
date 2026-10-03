"""Schedule planning and human-in-the-loop services backed by PyVDisk."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class _TemporaryActivity(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    time_slot_index: int = Field(ge=0)
    duration_minutes: int = Field(ge=15, le=1440)
    involves_user: bool = False
    reason: str = Field(min_length=1, max_length=500)


class _TemporaryActivityPlan(BaseModel):
    suggestions: list[_TemporaryActivity] = Field(min_length=1, max_length=3)


class _ScheduleSimilarity(BaseModel):
    is_similar: bool
    reason: str = Field(min_length=1, max_length=500)
    similarity: float = Field(ge=0, le=1)


class _ScheduleIntentOutput(BaseModel):
    intent: Literal["create", "query", "find_free_time", "unknown"]
    title: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=2000)
    time_expression: str = Field(default="", max_length=200)
    start_at: str | None = None
    end_at: str | None = None
    involves_agent: bool = False
    involves_user: bool = False
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(default="", max_length=1000)


class SchedulePlanningService:
    """Natural-language schedule intent and planning helpers.

    Parsing is deliberately conservative: ambiguous dates are returned as
    clarification-needed rather than silently persisted.
    """

    def __init__(self, store, model: Any | None = None):
        self.store = store
        self.model = model

    def detect_intent(self, text: str, *, now: datetime | None = None,
                      character_name: str = "智能体", context: str = "") -> dict[str, Any]:
        source = str(text).strip()
        if not source:
            return {"intent": "unknown", "needs_clarification": True, "reason": "empty input"}
        moment = now or datetime.now().astimezone()
        if self.model is not None:
            return self._detect_intent_with_model(
                source, moment=moment, character_name=character_name, context=context,
            )
        if any(word in source for word in ("空闲", "有空", "空档")):
            intent = "find_free_time"
        elif any(word in source for word in ("日程", "安排", "计划", "提醒", "预约")):
            intent = "create" if any(word in source for word in ("安排", "计划", "提醒", "预约", "添加", "创建")) else "query"
        else:
            return {"intent": "unknown", "needs_clarification": False}

        day = self._resolve_day(source, moment.date())
        time_match = re.search(
            r"(?:(上午|早上|中午|下午|晚上|傍晚|凌晨)\s*(\d{1,2})(?:点|时)?(?:([:：])(\d{1,2})分?)?|"
            r"(\d{1,2})[:：](\d{1,2}))",
            source,
        )
        due_at = None
        if time_match and day:
            period, period_hour, _separator, period_minute, plain_hour, plain_minute = time_match.groups()
            hour = int(period_hour or plain_hour)
            minute = int(period_minute or plain_minute or 0)
            if period in ("下午", "晚上", "傍晚") and 1 <= hour <= 11:
                hour += 12
            elif period == "中午" and hour < 11:
                hour += 12
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                return {"intent": intent, "needs_clarification": True, "reason": "invalid time"}
            due_at = datetime.combine(day, time(hour, minute), tzinfo=moment.tzinfo or timezone.utc).isoformat()
        title = re.sub(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}日?", "", source)
        title = re.sub(r"(下周|下星期|本周|这周|星期|周)\s*[一二三四五六日天1-7]", "", title)
        title = re.sub(r"(今天|明天|后天|大后天|上午|早上|中午|下午|晚上|傍晚|凌晨)", "", title)
        title = re.sub(r"(?:\d{1,2}[:：]\d{1,2}|\d{1,2}点(?:\d{1,2}分?)?|\d{1,2}时(?:\d{1,2}分?)?)", "", title)
        title = re.sub(r"^(请)?(帮我)?(安排|计划|添加|创建|设置|预约|提醒我|提醒)\s*", "", title)
        title = re.sub(r"\s*(安排|计划|添加|创建|设置|预约|提醒我|提醒)\s*", " ", title)
        title = title.strip(" ，,。!！-：:")
        missing = []
        if intent == "create" and not due_at:
            missing.append("date and time")
        if intent == "create" and not title:
            missing.append("title")
        return {"intent": intent, "title": title, "due_at": due_at,
                "date": day.isoformat() if day else None,
                "needs_clarification": bool(missing), "missing": missing}

    def _detect_intent_with_model(self, source: str, *, moment: datetime,
                                  character_name: str, context: str) -> dict[str, Any]:
        structured_output = getattr(self.model, "with_structured_output", None)
        if structured_output is None:
            raise TypeError("schedule planning model must support with_structured_output")
        parser = structured_output(_ScheduleIntentOutput)
        result = parser.invoke([
            ("system", "你是虚拟群友的日程意图分析器。识别邀约、安排、查询和空闲时段请求；"
                       "结合当前日期、角色与上下文解析自然语言时间。不要创建/修改日程。"
                       "不确定的字段留空并降低置信度，禁止臆造具体日期。输出时区明确的 ISO-8601 时间；"
                       "start_at/end_at 缺少时区时由调用方按当前时区解释。"),
            ("human", f"当前时间：{moment.isoformat()}\n角色：{character_name}\n上下文：{context or '无'}\n"
                       f"用户输入：{source}"),
        ])
        if isinstance(result, dict):
            result = _ScheduleIntentOutput.model_validate(result)
        elif not isinstance(result, _ScheduleIntentOutput):
            result = _ScheduleIntentOutput.model_validate(result)

        start = self._model_datetime(result.start_at, moment) if result.start_at else None
        end = self._model_datetime(result.end_at, moment) if result.end_at else None
        day = start.date() if start else self._resolve_day(result.time_expression + " " + source, moment.date())
        due_at = start.isoformat() if start else None
        if result.intent == "create" and due_at is None and result.time_expression:
            due_at = self._parse_time_expression(result.time_expression + " " + source, moment, day)
            if due_at:
                start = datetime.fromisoformat(due_at)
        if result.intent == "create" and start is not None and end is None:
            end = start + timedelta(hours=2)
        if start is not None and end is not None and end <= start:
            return {
                "intent": result.intent, "title": result.title, "description": result.description,
                "due_at": due_at, "end_at": end.isoformat(), "date": day.isoformat() if day else None,
                "involves_agent": result.involves_agent, "involves_user": result.involves_user,
                "confidence": result.confidence, "reasoning": result.reasoning,
                "needs_clarification": True, "missing": ["valid end time"],
            }
        missing = []
        if result.intent == "create" and not due_at:
            missing.append("date and time")
        if result.intent == "create" and not result.title.strip():
            missing.append("title")
        if result.intent == "create" and result.confidence < 0.55:
            missing.append("low confidence")
        return {
            "intent": result.intent, "title": result.title.strip(), "description": result.description.strip(),
            "due_at": due_at, "end_at": end.isoformat() if end else None,
            "date": day.isoformat() if day else None,
            "involves_agent": result.involves_agent, "involves_user": result.involves_user,
            "confidence": result.confidence, "reasoning": result.reasoning,
            "needs_clarification": bool(missing), "missing": missing,
        }

    @staticmethod
    def _model_datetime(value: str, reference: datetime) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError(f"LangChain model returned an invalid schedule timestamp: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=reference.tzinfo or timezone.utc)
        return parsed

    @classmethod
    def _parse_time_expression(cls, expression: str, moment: datetime,
                               day: date | None = None) -> str | None:
        target_day = day or cls._resolve_day(expression, moment.date())
        if target_day is None:
            return None
        match = re.search(
            r"(?:(上午|早上|早晨|中午|下午|晚上|傍晚|凌晨|夜里|深夜)\s*(\d{1,2})(?:点|时)?(?:[:：](\d{1,2})|\s*(\d{1,2})分?)?|"
            r"(\d{1,2})[:：](\d{1,2}))",
            expression,
        )
        if not match:
            period_match = re.search(r"(早上|早晨|上午|中午|下午|晚上|傍晚|凌晨|夜里|深夜)", expression)
            if not period_match:
                return None
            period = period_match.group(1)
            hour = {"早上": 9, "早晨": 9, "上午": 9, "中午": 12, "下午": 14,
                    "晚上": 18, "傍晚": 18, "凌晨": 1, "夜里": 22, "深夜": 23}[period]
            minute = 0
        else:
            period, period_hour, colon_minute, spaced_minute, plain_hour, plain_minute = match.groups()
            hour = int(period_hour or plain_hour)
            minute = int(colon_minute or spaced_minute or plain_minute or 0)
            if period in ("下午", "晚上", "傍晚") and 1 <= hour <= 11:
                hour += 12
            elif period == "中午" and hour < 11:
                hour += 12
            elif period in ("凌晨", "夜里", "深夜") and hour == 12:
                hour = 0 if period == "凌晨" else 12
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("schedule time expression contains an invalid time")
        return datetime.combine(target_day, time(hour, minute), tzinfo=moment.tzinfo or timezone.utc).isoformat()

    @staticmethod
    def _resolve_day(text: str, base: date) -> date | None:
        for phrase, offset in (("大后天", 3), ("后天", 2), ("明天", 1), ("今天", 0)):
            if phrase in text:
                return base + timedelta(days=offset)
        weekday_match = re.search(r"(下周|下星期|本周|这周|周|星期)\s*([一二三四五六日天1-7])", text)
        if weekday_match:
            prefix, weekday_label = weekday_match.groups()
            weekdays = {
                "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5,
                "日": 6, "天": 6, "1": 0, "2": 1, "3": 2, "4": 3,
                "5": 4, "6": 5, "7": 6,
            }
            target_weekday = weekdays[weekday_label]
            if prefix in {"下周", "下星期"}:
                # Anchor “next week” to the next Monday, even if its target
                # weekday is earlier than today's weekday.
                days_ahead = 7 - base.weekday() + target_weekday
            else:
                days_ahead = (target_weekday - base.weekday()) % 7
            return base + timedelta(days=days_ahead)
        match = re.search(r"(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?", text)
        if match:
            try:
                return date(*(int(part) for part in match.groups()))
            except ValueError:
                return None
        return None

    def find_free_slots(self, start_at: str, end_at: str, *, duration_minutes: int = 60) -> list[dict[str, str]]:
        return self.store.free_time_slots(start_at, end_at, duration_minutes=duration_minutes)

    def temporary_suggestions(self, start_at: str, end_at: str, *, duration_minutes: int = 60,
                              character_name: str = "智能体", hobbies: str = "阅读、学习",
                              context: str = "") -> list[dict[str, Any]]:
        slots = self.find_free_slots(start_at, end_at, duration_minutes=duration_minutes)
        if not slots:
            return []
        if self.model is not None:
            structured_model = getattr(self.model, "with_structured_output", None)
            if structured_model is None:
                raise TypeError("schedule planning model must support with_structured_output")
            plan_model = structured_model(_TemporaryActivityPlan)
            slot_context = "\n".join(
                f"{index}: {slot['start_at']} — {slot['end_at']}"
                for index, slot in enumerate(slots)
            )
            plan = plan_model.invoke([
                ("system", "为虚拟群友规划 1 至 3 个临时活动建议。只能使用给定空闲时段；不要创建日程。活动需符合角色兴趣，可提出用户共同参与。"),
                ("human", f"角色：{character_name}\n兴趣：{hobbies}\n上下文：{context or '无'}\n"
                           f"最短活动时长：{duration_minutes} 分钟\n可用时段（索引从 0 开始）：\n{slot_context}"),
            ])
            if isinstance(plan, dict):
                plan = _TemporaryActivityPlan.model_validate(plan)
            elif not isinstance(plan, _TemporaryActivityPlan):
                plan = _TemporaryActivityPlan.model_validate(plan)
            suggestions = []
            used_slots: set[int] = set()
            for proposal in plan.suggestions:
                index = proposal.time_slot_index
                if index >= len(slots):
                    raise ValueError(f"模型选择了不存在的空闲时段索引：{index}")
                if index in used_slots:
                    raise ValueError(f"模型为多个建议重复选择了空闲时段：{index}")
                used_slots.add(index)
                slot = slots[index]
                start = datetime.fromisoformat(slot["start_at"])
                end = datetime.fromisoformat(slot["end_at"])
                slot_minutes = int((end - start).total_seconds() // 60)
                if proposal.duration_minutes > slot_minutes:
                    raise ValueError(f"模型建议时长超出空闲时段：{index}")
                suggestions.append({
                    "title": proposal.title,
                    "description": proposal.description,
                    "due_at": start.isoformat(),
                    "end_at": (start + timedelta(minutes=proposal.duration_minutes)).isoformat(),
                    "type": "temporary", "priority": "low", "status": "suggested",
                    "involves_user": proposal.involves_user, "reason": proposal.reason,
                })
            return suggestions

        suggestions = []
        for slot in slots[:3]:
            start = datetime.fromisoformat(slot["start_at"])
            end = datetime.fromisoformat(slot["end_at"])
            duration = int((end - start).total_seconds() // 60)
            suggestions.append({"title": f"{character_name}的自主活动", "description": f"结合兴趣：{hobbies}",
                                "due_at": start.isoformat(),
                                "end_at": min(end, start + timedelta(minutes=max(duration_minutes, min(duration, 90)))).isoformat(),
                                "type": "temporary", "priority": "low", "status": "suggested",
                                "reason": "该时段没有与现有日程冲突；建议确认后再创建。"})
        return suggestions

    def compare_similar(self, candidate: dict[str, Any], *, threshold: float = 0.55) -> list[dict[str, Any]]:
        """Return explainable same-day semantic candidates; never auto-delete."""
        title = str(candidate.get("title", ""))
        due = datetime.fromisoformat(str(candidate["due_at"]).replace("Z", "+00:00"))
        words = self._tokens(title + " " + str(candidate.get("description", "")))
        similarity_model = None
        if self.model is not None:
            structured_output = getattr(self.model, "with_structured_output", None)
            if structured_output is None:
                raise TypeError("schedule planning model must support with_structured_output")
            similarity_model = structured_output(_ScheduleSimilarity)
        results = []
        for existing in self.store.schedules():
            if existing.get("status") in {"cancelled", "rejected", "deleted", "completed"}:
                continue
            other_due = datetime.fromisoformat(existing["due_at"].replace("Z", "+00:00"))
            if other_due.date() != due.date():
                continue
            if similarity_model is not None:
                judgment = similarity_model.invoke([
                    ("system", "判断两个日程是否核心活动重复。时间接近与否不是唯一标准；主题/活动不同则不相似。只作提示，绝不修改或删除记录。"),
                    ("human", f"新日程：{title}\n{candidate.get('description', '')}\n{due.isoformat()}\n\n"
                               f"已有日程：{existing.get('title', '')}\n{existing.get('description', '')}\n{other_due.isoformat()}"),
                ])
                if isinstance(judgment, dict):
                    judgment = _ScheduleSimilarity.model_validate(judgment)
                elif not isinstance(judgment, _ScheduleSimilarity):
                    judgment = _ScheduleSimilarity.model_validate(judgment)
                if judgment.is_similar:
                    results.append({"schedule": existing, "similarity": judgment.similarity,
                                    "reason": judgment.reason, "recommendation": "review_before_create"})
            else:
                other_words = self._tokens(str(existing.get("title", "")) + " " + str(existing.get("description", "")))
                score = len(words & other_words) / max(1, len(words | other_words))
                if score >= threshold:
                    results.append({"schedule": existing, "similarity": round(score, 3),
                                    "reason": "same local date and overlapping title/description terms",
                                    "recommendation": "review_before_create"})
        return sorted(results, key=lambda row: row["similarity"], reverse=True)

    @staticmethod
    def _tokens(text: str) -> set[str]:
        normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text.casefold())
        result = set()
        for token in normalized.split():
            if len(token) <= 4:
                result.add(token)
            else:
                result.update(token[i:i + 2] for i in range(len(token) - 1))
        return result


class InterruptQuestionService:
    """Durable non-blocking human-in-the-loop questions."""

    def __init__(self, store):
        self.store = store

    def ask(self, question: str, *, context: str = "", conversation_id: str = "default") -> dict[str, Any]:
        question = str(question).strip()
        if not question:
            raise ValueError("question must not be empty")
        request_id = uuid.uuid4().hex[:20]
        record = {"id": request_id, "question": question, "context": str(context),
                  "conversation_id": str(conversation_id), "status": "pending",
                  "created_at": datetime.now(timezone.utc).isoformat()}
        self.store.save_document("question_requests", request_id, record)
        self.store.append_event("human.question.requested", {"question_id": request_id, "conversation_id": conversation_id})
        return record

    def pending(self) -> list[dict[str, Any]]:
        return [row for row in self.store.list_documents("question_requests") if row.get("status") == "pending"]

    def resolve(self, request_id: str, answer: str) -> dict[str, Any]:
        answer = str(answer).strip()
        if not answer:
            raise ValueError("answer must not be empty")
        row = self.store.get_document("question_requests", request_id)
        if not row:
            raise KeyError(request_id)
        if row.get("status") != "pending":
            raise ValueError("question is already resolved")
        row.update(status="answered", answer=answer, answered_at=datetime.now(timezone.utc).isoformat())
        self.store.save_document("question_requests", request_id, row)
        self.store.append_event("human.question.answered", {"question_id": request_id})
        return row
