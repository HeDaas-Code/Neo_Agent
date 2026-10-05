"""Three-stage conversational runtime: cognition, governed actions, persona reply."""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from neo_agent.storage import DiskStore
from neo_agent.plugins import PluginRegistry
from neo_agent.runtime.cognition import (
    ActionResult, CognitionDecision, CognitionService, risk_for_tool,
    safe_result_summary,
)


from neo_agent.runtime.auto_creation import AutoCreationService
from neo_agent.runtime.relationship import RelationshipService
from neo_agent.runtime.daily_itinerary import DailyItineraryService
from neo_agent.runtime.scene_generation import SceneGenerationService


class AgentRuntime:
    """One character runtime with a hard boundary around tool execution.

    The final language model call is always unbound (no tools) and receives only
    normalized action summaries, not tool messages, arguments, or hidden traces.
    """

    def __init__(self, store: DiskStore, model: Any | None = None, *,
                 max_tool_rounds: int = 6, plugin_registry: PluginRegistry | None = None,
                 language_model: Any | None = None):
        self.store = store
        self.model = model or self._build_model()
        self.language_model = language_model or self.model
        self.plugin_registry = plugin_registry or PluginRegistry(store, model=self.model)
        if getattr(self.plugin_registry, "model", None) is None:
            self.plugin_registry.model = self.model
        self.tools = self.plugin_registry.tools()
        self._tool_by_name = {tool.name: tool for tool in self.tools}
        self.max_tool_rounds = max_tool_rounds
        self.cognition = CognitionService(self.model)
        self.relationship_service = RelationshipService(store)

    @staticmethod
    def _build_model() -> Any:
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError("Install langchain-openai to enable model-backed conversations") from exc
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        if not base_url:
            endpoint = os.getenv("SILICONFLOW_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
            base_url = endpoint.removesuffix("/chat/completions").rstrip("/")
        model_name = os.getenv("OPENAI_MODEL") or os.getenv("MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")
        if not api_key:
            raise RuntimeError("Configure OPENAI_API_KEY or SILICONFLOW_API_KEY in the environment")
        # Explicit network bounds keep a disconnected model endpoint from
        # retaining runtime workers indefinitely (the TUI can remain usable
        # while requests are in flight).
        return ChatOpenAI(
            model=model_name, api_key=api_key, base_url=base_url,
            temperature=0.7, timeout=30, max_retries=0,
        )

    def chat(self, message: str, *, conversation_id: str = "default", system_prompt: str = "") -> str:
        if not message.strip():
            raise ValueError("message must not be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", conversation_id):
            raise ValueError("conversation_id may contain only letters, digits, '_' and '-' (max 80)")
        storage_id = conversation_id if len(conversation_id) <= 22 else hashlib.sha256(conversation_id.encode()).hexdigest()[:20]
        history_path = f"/runtime/conversations/{storage_id}.json"
        transcript = self.store.read_json(history_path, default=[])
        context_parts = [system_prompt] if system_prompt else []
        from neo_agent.runtime.itinerary import SceneService
        scene_context = SceneService(self.store).current_context()
        if scene_context:
            context_parts.append(scene_context)
        pending_decisions = [row for row in self.store.list_documents("schedule_decisions")
                             if row.get("status") == "applied" and row.get("explanation_pending")]
        if pending_decisions:
            summaries = [str(row.get("summary", "")) for row in pending_decisions[-3:] if row.get("summary")]
            if summaries:
                context_parts.append("最近自主协调的共同日程变化（若对话自然相关，可诚实简要说明）：" + "；".join(summaries))
        from neo_agent.runtime.expression import ExpressionService
        expression_service = ExpressionService(self.store)
        for prompt in (expression_service.prompt(), expression_service.user_habit_prompt()):
            if prompt:
                context_parts.append(prompt)
        short_term = self.store.short_term_messages(storage_id, limit=20)
        if short_term:
            context_parts.append("近期对话片段：\n" + "\n".join(f"{item['role']}: {item['content']}" for item in short_term))
        try:
            memories = self.store.search_memories(message, character_id=storage_id, limit=3)
        except Exception:
            memories = []
        if memories:
            context_parts.append("相关长期记忆（供角色理解使用）：\n" + "\n".join(f"- {item.get('text', '')}" for item in memories))
        try:
            relationship = self.store.get_document("relationships", storage_id)
        except Exception:
            relationship = None
        if relationship:
            context_parts.append("当前关系状态摘要：" + json.dumps({k: relationship.get(k) for k in ("score", "stage", "impression", "dimensions") if k in relationship}, ensure_ascii=False))
        context = "\n\n".join(context_parts)
        history = []
        for turn in transcript[-20:]:
            history.extend((HumanMessage(content=turn["user"]), AIMessage(content=turn["assistant"])))
        recent_context = "\n".join(f"{turn['user']} → {turn['assistant']}" for turn in transcript[-10:])

        # Stage 1: the structured gate sees persona, context, memories and relationship
        # state, but has no tools. Only an explicit action_needed decision can proceed.
        actions: list[ActionResult] = []
        decision = self.cognition.assess(message=message, context=context + "\n" + recent_context,
                                         personality=system_prompt, direct_chat=True)
        # The affect label is a per-turn observation. Durable relationship state
        # is separately gated by distinct, repeated high-confidence evidence.
        from neo_agent.runtime.emotion import EmotionService
        EmotionService(self.store).record_cognitive_state(
            storage_id, signal=decision.relationship_signal,
            affective_state=decision.affective_state, confidence=decision.confidence,
            round_id=f"{storage_id}:{len(transcript) + 1}",
        )

        # Stage 2: proposals are generated only after the gate allows an action.
        # Tool calls are still checked against the enabled manifest at execution.
        if decision.action_needed and self.tools:
            planner_messages = [
                SystemMessage(content=("Propose only the minimum tool calls needed for the user's explicit request. "
                                      "Use only supplied tools; do not write a user-facing reply. If required details "
                                      "are missing, return no tool call.")),
                *history,
                HumanMessage(content=f"角色与状态摘要：\n{context}\n\n用户请求：{message}"),
            ]
            planned = self.model.bind_tools(self.tools).invoke(planner_messages)
            for call in (getattr(planned, "tool_calls", None) or [])[:self.max_tool_rounds]:
                actions.append(self._execute_tool(call))
            if not actions:
                decision = CognitionDecision.from_mapping({**decision.__dict__, "reply_strategy": "clarify"})
        elif decision.action_needed and not self.tools:
            actions.append(ActionResult("unavailable", "undeclared", "denied", "low", "当前没有启用可用能力。"))

        self.store.append_event("cognition.decision", {
            "conversation_id": conversation_id, "intent": decision.intent,
            "action_needed": decision.action_needed, "reply_strategy": decision.reply_strategy,
            "confidence": decision.confidence, "relationship_signal": decision.relationship_signal,
            "affective_state": decision.affective_state,
        })
        self.store.write_json("/runtime/cognition/latest.json", {
            "conversation_id": conversation_id, "decision": {"intent": decision.intent, "action_needed": decision.action_needed, "reply_strategy": decision.reply_strategy, "confidence": decision.confidence, "relationship_signal": decision.relationship_signal, "affective_state": decision.affective_state},
            "actions": [item.__dict__ for item in actions],
        })

        # Stage 3: persona language generation has no tool binding and receives
        # only curated action facts. Failed actions are explicitly non-success.
        action_facts = [item.public_dict() for item in actions]
        language_system = (context + "\n\n你正在和对方自然交谈。保持角色设定，不描述内部工具调用、审计或推理。"
                           "只基于已确认事实作答；失败操作不得声称成功。")
        language_user = (f"用户消息：{message}\n\n已确认的操作结果（可能为空）："
                         f"{json.dumps(action_facts, ensure_ascii=False)}\n"
                         f"认知策略：{decision.reply_strategy}。如需澄清，请用角色口吻自然提问。")
        response = self.language_model.invoke([
            SystemMessage(content=language_system), *history, HumanMessage(content=language_user),
        ])
        answer = str(getattr(response, "content", response))
        transcript.append({"user": message, "assistant": answer})
        self.store.write_json(history_path, transcript[-100:])
        expression_service = ExpressionService(self.store)
        expression_service.record_usage(answer)
        self._maybe_learn_user_expressions(storage_id, transcript, ExpressionService(
            self.store, learner=self._expression_learner()))
        self.store.add_short_term_message("user", message, conversation_id=storage_id)
        self.store.add_short_term_message("assistant", answer, conversation_id=storage_id)
        self.store.save_memory(
            hashlib.sha256(f"{storage_id}:{len(transcript)}".encode()).hexdigest()[:20],
            f"用户：{message}\n助手：{answer}", character_id=storage_id,
            metadata={"kind": "conversation-turn", "conversation_id": storage_id},
        )
        self.store.append_event("conversation.turn.completed", {
            "conversation_id": conversation_id, "user_chars": len(message), "assistant_chars": len(answer),
        })
        for decision in pending_decisions:
            self.store.save_document("schedule_decisions", decision["id"], {"explanation_pending": False, "last_contextualized_at": __import__("datetime").datetime.now().astimezone().isoformat()})
        
        # 自动创作功能：根据对话自动创建实体
        try:
            auto_creation = AutoCreationService(self.store, self.model)
            
            # 提取并创建日程
            schedules = auto_creation.extract_schedule_intent(
                message, answer, {"current_scene": self.store.read_json("/runtime/scene/current.json", default={})}
            )
            if schedules:
                self.store.append_event("agent.auto_creation.schedules", {
                    "count": len(schedules),
                    "activities": [s["activity"] for s in schedules]
                })
            
            # 提取关系信号
            rel_signal = auto_creation.extract_relationship_updates(message, answer, storage_id)

            # 记录关系信号到 RelationshipService
            if rel_signal and rel_signal.get("entity"):
                try:
                    result = self.relationship_service.record_signal(
                        entity=rel_signal["entity"],
                        signal_type=rel_signal["signal"],
                        confidence=rel_signal["confidence"],
                        score_delta=rel_signal["score_delta"],
                        reason=rel_signal["reason"],
                        conversation_id=f"{storage_id}:{len(transcript) + 1}"
                    )
                    if result.get("persisted"):
                        self.store.append_event("relationship.persisted", {
                            "entity": rel_signal["entity"],
                            "new_score": result["new_score"],
                            "evidence_count": result["evidence_count"]
                        })
                except Exception as exc:
                    self.store.append_event("relationship.record_failed", {
                        "error": type(exc).__name__,
                        "message": str(exc)
                    })
            
            # 提取知识条目
            knowledge = auto_creation.maybe_create_knowledge_entry(message, answer)
            
        except Exception as exc:
            self.store.append_event("agent.auto_creation.error", {
                "error": type(exc).__name__,
                "message": str(exc)
            })

        return answer

    def _execute_tool(self, call: dict[str, Any]) -> ActionResult:
        name = str(call.get("name", "unknown"))
        tool = self._tool_by_name.get(name)
        capabilities = self.plugin_registry.capabilities_for_tool(name)
        risk = risk_for_tool(name, capabilities)
        if tool is None or not capabilities:
            status, summary = "denied", "未找到启用且声明能力的插件，调用已拒绝。"
        else:
            try:
                result = tool.invoke(call.get("args", {}))
                summary = safe_result_summary(result)
                status = "failed" if "未能完成" in summary else "succeeded"
            except Exception as exc:
                status, summary = "failed", "操作未能完成。"
                self.store.append_event("agent.action.exception", {"tool": name, "error_type": type(exc).__name__})
        action = ActionResult(name, ",".join(capabilities) or "undeclared", status, risk, summary)
        self.store.append_event("agent.action.audit", {
            "tool": action.tool_name, "capability": action.capability, "status": action.status,
            "risk": action.risk, "summary": action.summary,
            "enhanced": action.risk == "high",
            "audit_level": "enhanced" if action.risk == "high" else "standard",
            "execution": "automatic_no_human_approval",
        })
        return action

    def _expression_learner(self):
        from neo_agent.runtime.expression import langchain_expression_learner
        return langchain_expression_learner(self.model)

    def _maybe_learn_user_expressions(self, conversation_id: str, transcript: list[dict[str, str]], service: Any) -> None:
        cursor_path = f"/runtime/expression-learning/{conversation_id}.json"
        cursor = self.store.read_json(cursor_path, default={"last_round": 0})
        last_round = int(cursor.get("last_round", 0))
        current_round = len(transcript)
        if current_round - last_round < 10:
            return
        try:
            service.learn([{"role": "user", "content": turn.get("user", "")} for turn in transcript], current_round=current_round)
            self.store.write_json(cursor_path, {"last_round": current_round})
        except Exception as exc:
            self.store.append_event("expression.habits.learning_failed", {
                "conversation_id": conversation_id, "round": current_round,
                "error": type(exc).__name__,
            })
