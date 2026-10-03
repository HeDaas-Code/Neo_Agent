"""Bounded LangChain tool-calling loop backed exclusively by PyVDisk."""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from neo_agent.storage import DiskStore
from neo_agent.plugins import PluginRegistry


class AgentRuntime:
    """One virtual character's conversational execution boundary.

    The model can only invoke LangChain tools generated from the active
    PyVDisk AgentSandbox capabilities. Transcript records are persisted as
    PyVDisk documents; model output is never executed as Python on the host.
    """

    def __init__(
        self, store: DiskStore, model: Any | None = None, *,
        max_tool_rounds: int = 6, plugin_registry: PluginRegistry | None = None,
    ):
        self.store = store
        self.model = model or self._build_model()
        self.plugin_registry = plugin_registry or PluginRegistry(store, model=self.model)
        if getattr(self.plugin_registry, "model", None) is None:
            self.plugin_registry.model = self.model
        self.tools = self.plugin_registry.tools()
        self._tool_by_name = {tool.name: tool for tool in self.tools}
        self.max_tool_rounds = max_tool_rounds

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
        return ChatOpenAI(model=model_name, api_key=api_key, base_url=base_url, temperature=0.7)

    def chat(self, message: str, *, conversation_id: str = "default", system_prompt: str = "") -> str:
        if not message.strip():
            raise ValueError("message must not be empty")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", conversation_id):
            raise ValueError("conversation_id may contain only letters, digits, '_' and '-' (max 80)")
        # VFS components have a stricter byte limit than public conversation IDs.
        # Keep readable IDs when possible and map long IDs deterministically.
        storage_id = conversation_id if len(conversation_id) <= 22 else hashlib.sha256(conversation_id.encode()).hexdigest()[:20]
        history_path = f"/runtime/conversations/{storage_id}.json"
        transcript = self.store.read_json(history_path, default=[])
        messages = []
        prompt_parts = [system_prompt] if system_prompt else []
        # Operator-authored expression guidance is first-class runtime context.
        from neo_agent.runtime.expression import ExpressionService
        expression_prompt = ExpressionService(self.store).prompt()
        if expression_prompt:
            prompt_parts.append(expression_prompt)
        habit_prompt = ExpressionService(self.store).user_habit_prompt()
        if habit_prompt:
            prompt_parts.append(habit_prompt)
        short_term = self.store.short_term_messages(storage_id, limit=20)
        if short_term:
            prompt_parts.append("近期对话片段：\n" + "\n".join(f"{item['role']}: {item['content']}" for item in short_term))
        try:
            memories = self.store.search_memories(message, character_id=storage_id, limit=3)
        except Exception:
            memories = []
        if memories:
            prompt_parts.append("可能相关的长期记忆（仅作参考）：\n" + "\n".join(f"- {item.get('text', '')}" for item in memories))
        if prompt_parts:
            messages.append(SystemMessage(content="\n\n".join(prompt_parts)))
        # Keep persisted history portable and framework-version independent.
        for turn in transcript[-20:]:
            messages.extend((HumanMessage(content=turn["user"]), AIMessage(content=turn["assistant"])))
        messages.append(HumanMessage(content=message))

        model = self.model.bind_tools(self.tools) if self.tools else self.model
        for _ in range(self.max_tool_rounds + 1):
            response = model.invoke(messages)
            messages.append(response)
            if not getattr(response, "tool_calls", None):
                answer = str(response.content)
                transcript.append({"user": message, "assistant": answer})
                self.store.write_json(history_path, transcript[-100:])
                from neo_agent.runtime.expression import langchain_expression_learner
                expression_service = ExpressionService(self.store, learner=langchain_expression_learner(self.model))
                expression_service.record_usage(answer)
                self._maybe_learn_user_expressions(storage_id, transcript, expression_service)
                self.store.add_short_term_message("user", message, conversation_id=storage_id)
                self.store.add_short_term_message("assistant", answer, conversation_id=storage_id)
                self.store.save_memory(
                    hashlib.sha256(f"{storage_id}:{len(transcript)}".encode()).hexdigest()[:20],
                    f"用户：{message}\n助手：{answer}", character_id=storage_id,
                    metadata={"kind": "conversation-turn", "conversation_id": storage_id},
                )
                self.store.append_event("conversation.turn.completed", {
                    "conversation_id": conversation_id,
                    "user_chars": len(message),
                    "assistant_chars": len(answer),
                })
                return answer
            for call in response.tool_calls:
                name = call["name"]
                tool = self._tool_by_name.get(name)
                if tool is None:
                    output = f"ToolError: {name} is not an available capability"
                else:
                    try:
                        output = str(tool.invoke(call.get("args", {})))
                    except Exception as exc:  # errors are returned to the model as tool output
                        output = f"ToolError: {type(exc).__name__}: {exc}"
                messages.append(ToolMessage(content=output, tool_call_id=call["id"]))
        raise RuntimeError(f"agent exceeded the {self.max_tool_rounds}-round tool limit")

    def _maybe_learn_user_expressions(self, conversation_id: str, transcript: list[dict[str, str]], service: Any) -> None:
        """Run the legacy ten-turn learning cadence, with durable per-chat cursor."""
        cursor_path = f"/runtime/expression-learning/{conversation_id}.json"
        cursor = self.store.read_json(cursor_path, default={"last_round": 0})
        last_round = int(cursor.get("last_round", 0))
        current_round = len(transcript)
        if current_round - last_round < 10:
            return
        try:
            service.learn([{"role": "user", "content": turn.get("user", "")} for turn in transcript],
                          current_round=current_round)
            self.store.write_json(cursor_path, {"last_round": current_round})
        except Exception as exc:
            # Learning is advisory and must never fail the user's chat turn. Keep
            # the cursor unchanged so the operator can retry on a later turn.
            self.store.append_event("expression.habits.learning_failed", {
                "conversation_id": conversation_id, "round": current_round,
                "error": f"{type(exc).__name__}: {exc}",
            })
