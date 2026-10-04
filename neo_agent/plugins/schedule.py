"""Agent-facing event and schedule capabilities backed by PyVDisk."""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Literal

from neo_agent.services.scheduling import InterruptQuestionService, SchedulePlanningService

from neo_agent.plugins.base import PluginContext, PluginManifest


class CreateScheduleArgs(BaseModel):
    schedule_id: str = Field(default="", description="Optional stable identifier; generated automatically when omitted")
    title: str = Field(description="Short schedule title")
    due_at: str = Field(description="ISO-8601 timestamp including timezone")
    end_at: str = Field(default="", description="Optional ISO-8601 end timestamp including timezone")
    description: str = Field(default="", description="Optional details")
    purpose: str = Field(default="", description="Why this activity exists; used for scene selection")
    category: Literal["agent", "shared"] = Field(default="agent", description="Agent personal activity or explicit shared activity")
    participants: list[Literal["agent", "user"]] = Field(default_factory=list, description="Participants; shared activities require both")
    place_id: str = Field(default="", description="Optional generated/visited place binding")
    area_id: str = Field(default="", description="Optional place area binding")


class DetectScheduleIntentArgs(BaseModel):
    text: str = Field(description="User's natural-language schedule request")
    character_name: str = Field(default="智能体", description="Agent whose schedule is being discussed")
    context: str = Field(default="", description="Recent conversation context needed to resolve omitted details")


class FreeSlotsArgs(BaseModel):
    start_at: str = Field(description="Timezone-aware ISO-8601 range start")
    end_at: str = Field(description="Timezone-aware ISO-8601 range end")
    duration_minutes: int = Field(default=60, ge=1, description="Minimum free slot duration")


class TemporarySuggestionsArgs(BaseModel):
    start_at: str = Field(description="Timezone-aware ISO-8601 window start")
    end_at: str = Field(description="Timezone-aware ISO-8601 window end")
    duration_minutes: int = Field(default=60, ge=1)
    character_name: str = Field(default="智能体")
    hobbies: str = Field(default="阅读、学习")


class CompareSchedulesArgs(BaseModel):
    title: str = Field(description="Proposed schedule title")
    due_at: str = Field(description="Timezone-aware ISO-8601 start")
    description: str = Field(default="")


class AskUserArgs(BaseModel):
    question: str = Field(description="Clear question to ask the user")
    context: str = Field(default="", description="Why the agent needs this answer")
    conversation_id: str = Field(default="default", description="Conversation to resume after answering")


class ResolveQuestionArgs(BaseModel):
    question_id: str = Field(description="Pending question identifier")
    answer: str = Field(description="User's answer")


class AppendEventArgs(BaseModel):
    event_type: str = Field(description="Namespaced domain event type")
    summary: str = Field(description="Human-readable event summary")


class ScheduleEventPlugin:
    manifest = PluginManifest(
        plugin_id="core.events-schedules",
        name="事件与日程",
        version="1.0.0",
        description="将角色行程、用户日程或双方共同活动保存到 PyVDisk，并记录领域事件；不会投递或暂存提醒。",
        capabilities=("events.append", "schedules.create"),
    )

    def load_tools(self, context: PluginContext):
        planner = SchedulePlanningService(context.store, model=context.model)
        questions = InterruptQuestionService(context.store)
        return [
            StructuredTool.from_function(
                name="detect_schedule_intent",
                description="Use LangChain structured analysis and conservative time parsing to classify a natural-language schedule request. Returns missing details for clarification and never creates a schedule.",
                func=lambda text, character_name="智能体", context="": planner.detect_intent(
                    text, character_name=character_name, context=context,
                ),
                args_schema=DetectScheduleIntentArgs,
            ),
            StructuredTool.from_function(
                name="find_schedule_free_slots",
                description="Find available intervals in a timezone-aware date range.",
                func=lambda start_at, end_at, duration_minutes=60: planner.find_free_slots(start_at, end_at, duration_minutes=duration_minutes),
                args_schema=FreeSlotsArgs,
            ),
            StructuredTool.from_function(
                name="suggest_temporary_schedules",
                description="Suggest activities for existing free slots; suggestions are not persisted until explicitly confirmed.",
                func=lambda start_at, end_at, duration_minutes=60, character_name="智能体", hobbies="阅读、学习": planner.temporary_suggestions(
                    start_at, end_at, duration_minutes=duration_minutes, character_name=character_name, hobbies=hobbies
                ),
                args_schema=TemporarySuggestionsArgs,
            ),
            StructuredTool.from_function(
                name="compare_similar_schedules",
                description="Find explainable same-day schedule duplicates for human review; never deletes or overwrites records.",
                func=lambda title, due_at, description="": planner.compare_similar({"title": title, "due_at": due_at, "description": description}),
                args_schema=CompareSchedulesArgs,
            ),
            StructuredTool.from_function(
                name="ask_user",
                description="Create a durable human-in-the-loop question. Returns immediately with a pending request ID; do not pretend the user answered yet.",
                func=lambda question, context="", conversation_id="default": questions.ask(question, context=context, conversation_id=conversation_id),
                args_schema=AskUserArgs,
            ),
            StructuredTool.from_function(
                name="resolve_user_question",
                description="Record a user's answer to a pending question after it has been provided by the control plane.",
                func=lambda question_id, answer: questions.resolve(question_id, answer),
                args_schema=ResolveQuestionArgs,
            ),
            StructuredTool.from_function(
                name="create_schedule",
                description="创建生活日程记录，不发送通知；明确标记共同参与时才关联双方日历。",
                func=lambda schedule_id, title, due_at, end_at="", description="", purpose="",
                             category="agent", participants=None, place_id="", area_id="": context.store.create_schedule(
                    schedule_id or None, {
                        "title": title, "due_at": due_at, **({"end_at": end_at} if end_at else {}),
                        "description": description, "purpose": purpose, "category": category,
                        "participants": participants or (["agent", "user"] if category == "shared" else ["agent"]),
                        **({"place_id": place_id, "area_id": area_id, "scene_binding": True}
                           if place_id or area_id else {}),
                    }, actor="agent"
                ),
                args_schema=CreateScheduleArgs,
            ),
            StructuredTool.from_function(
                name="record_domain_event",
                description="将群聊、关系或工作流中的领域事件追加到 PyVDisk 事件日志。",
                func=lambda event_type, summary: context.store.append_event(
                    event_type, {"summary": summary}
                ),
                args_schema=AppendEventArgs,
            ),
        ]
