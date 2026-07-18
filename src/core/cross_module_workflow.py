"""
CrossModuleWorkflow - 跨模块复杂工作流核心逻辑。

实现典型认知闭环：
    对话输入 → 记忆存取 → LLM 流式生成 → 情感分析 → 日程意图识别 →
    日程创建 → 主动消息确认决策。

本模块位于 src/core/，符合项目硬约束：新增核心逻辑统一放在 src/core/ 下，
并复用 DatabaseManager、PromptManager（通过 CharacterProfile）等现有基础设施。
神经系统接入层由 src.prefrontal.workflow_module.WorkflowModule 承担。
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from src.core.chat_agent import CharacterProfile
from src.core.database_manager import DatabaseManager
from src.limbic.hippocampus.memory_store import LongTermMemoryManager
from src.nervous_system.router.packet import Packet, PacketType


class ChatWorkflow:
    """
    聊天工作流核心。

    不直接调用其他模块的 Python 方法，而是通过 CentralRouter 发送 Packet，
    从而真正实现模块间解耦与可追踪的跨模块协作。
    """

    def __init__(
        self,
        router,
        db_manager: Optional[DatabaseManager] = None,
    ) -> None:
        self.router = router
        self.db = db_manager or DatabaseManager()
        self.memory_manager = LongTermMemoryManager(db_manager=self.db)
        self.character = CharacterProfile()

    async def run_stream(
        self,
        user_input: str,
        user_id: str = "default",
        session_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        执行完整聊天工作流并异步生成事件。

        Yields:
            dict 事件：
            - {"event": "chunk", "content": str}
            - {"event": "done", "full_content": str}
            - {"event": "workflow_result",
               "emotion": ..., "schedule": ..., "proactive": ...}
        """
        trace_id = uuid.uuid4().hex
        metadata: Dict[str, Any] = {
            "user_id": user_id,
            "trace_id": trace_id,
            "session_id": session_id,
        }
        context = context or {}
        metadata["context"] = context

        # 1. 持久化用户消息
        await self._store_message("user", user_input, metadata)

        # 2. 组装带上下文的 messages
        messages = await self._build_messages(user_input, metadata)

        # 3. 流式调用 LLM 生成回复
        full_reply = ""
        async for chunk in self._stream_llm(messages, metadata):
            full_reply += chunk
            yield {"event": "chunk", "content": chunk}

        yield {"event": "done", "full_content": full_reply}

        # 4. 持久化助手回复
        if full_reply:
            await self._store_message("assistant", full_reply, metadata)

        # 5. 后台并行执行：情感分析、日程意图、主动决策
        emotion, schedule, proactive = await self._run_post_workflow(
            user_input, full_reply, metadata
        )
        yield {
            "event": "workflow_result",
            "emotion": emotion,
            "schedule": schedule,
            "proactive": proactive,
        }

    # ------------------------------------------------------------------
    # 内部 helpers
    # ------------------------------------------------------------------
    async def _store_message(
        self,
        role: str,
        content: str,
        metadata: Dict[str, Any],
    ) -> None:
        """通过 hippocampus 存储一条消息。"""
        packet = Packet(
            source="prefrontal.workflow",
            target="limbic.hippocampus.full",
            packet_type=PacketType.REQUEST,
            channel="memory_store",
            payload={"role": role, "content": content},
            metadata=metadata,
        )
        try:
            await self.router.route(packet)
        except Exception:
            # 记忆存储失败不应阻断主流程
            pass

    async def _build_messages(
        self,
        user_input: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """查询历史记忆与情感语气，组装 LLM messages。"""
        memories: List[Dict[str, str]] = []
        try:
            query_packet = Packet(
                source="prefrontal.workflow",
                target="limbic.hippocampus.full",
                packet_type=PacketType.REQUEST,
                channel="memory_query",
                payload={"limit": 20},
                metadata=metadata,
            )
            response = await self.router.route(query_packet)
            if response.is_response():
                memories = response.payload.get("memories", []) or []
        except Exception:
            memories = []

        emotion_context = ""
        try:
            tone_packet = Packet(
                source="prefrontal.workflow",
                target="limbic.amygdala",
                packet_type=PacketType.REQUEST,
                channel="emotion_tone",
                payload={},
                metadata=metadata,
            )
            tone_response = await self.router.route(tone_packet)
            if tone_response.is_response():
                emotion_context = tone_response.payload.get("tone_prompt", "")
        except Exception:
            emotion_context = ""

        system_prompt = self.character.get_system_prompt(
            emotion_relationship=emotion_context or "初次见面"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]
        for msg in memories:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            })
        messages.append({"role": "user", "content": user_input})
        return messages

    async def _stream_llm(
        self,
        messages: List[Dict[str, str]],
        metadata: Dict[str, Any],
    ) -> AsyncIterator[str]:
        """通过 cortex.llm_core 的 llm_stream 通道流式生成回复。"""
        packet = Packet(
            source="prefrontal.workflow",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="llm_stream",
            payload={"messages": messages, "task_type": "main"},
            metadata=metadata,
        )
        try:
            async for response_packet in self.router.route_stream(packet):
                if response_packet.is_error():
                    yield f"[错误: {response_packet.payload.get('error', 'unknown error')}]"
                    break

                if response_packet.packet_type != PacketType.STREAM:
                    continue

                stream_event = response_packet.payload.get("stream_event")
                if stream_event == "chunk":
                    content = response_packet.payload.get("content", "")
                    if content:
                        yield content
                elif stream_event == "error":
                    error_msg = response_packet.payload.get("error", "unknown stream error")
                    yield f"[流式错误: {error_msg}]"
                    break
                elif stream_event == "done":
                    break
        except Exception as exc:
            yield f"[工作流异常: {exc}]"

    async def _run_post_workflow(
        self,
        user_input: str,
        assistant_reply: str,
        metadata: Dict[str, Any],
    ):
        """并行执行情感分析、日程意图、主动决策。"""
        import asyncio

        results = await asyncio.gather(
            self._analyze_emotion(user_input, assistant_reply, metadata),
            self._check_schedule_intent(user_input, metadata),
            self._check_proactive(metadata.get("user_id", "default"), metadata),
            return_exceptions=True,
        )

        emotion = results[0] if not isinstance(results[0], Exception) else {}
        schedule = results[1] if not isinstance(results[1], Exception) else {}
        proactive = results[2] if not isinstance(results[2], Exception) else {}
        return emotion, schedule, proactive

    async def _analyze_emotion(
        self,
        user_input: str,
        assistant_reply: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """通过 limbic.amygdala 分析本轮对话情感。"""
        packet = Packet(
            source="prefrontal.workflow",
            target="limbic.amygdala",
            packet_type=PacketType.REQUEST,
            channel="emotion_analyze",
            payload={
                "messages": [
                    {"role": "user", "content": user_input},
                    {"role": "assistant", "content": assistant_reply},
                ],
                "character_name": self.character.name,
            },
            metadata=metadata,
        )
        try:
            response = await self.router.route(packet)
            if response.is_response():
                return response.payload
        except Exception:
            pass
        return {}

    async def _check_schedule_intent(
        self,
        user_input: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """通过 cerebellum.toolkit 识别日程意图，并在必要时创建日程。"""
        packet = Packet(
            source="prefrontal.workflow",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="schedule_intent",
            payload={
                "user_input": user_input,
                "character_name": self.character.name,
            },
            metadata=metadata,
        )
        try:
            response = await self.router.route(packet)
            if not response.is_response():
                return {}

            intent = response.payload
            confidence = float(intent.get("confidence", 0) or 0)
            has_intent = bool(intent.get("has_schedule_intent")) and confidence > 0.6
            if not has_intent:
                return {"intent": intent, "created": None}

            created = await self._create_schedule(intent, metadata)
            return {"intent": intent, "created": created}
        except Exception:
            return {}

    async def _create_schedule(
        self,
        intent_result: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """通过 prefrontal.planner 创建日程。"""
        packet = Packet(
            source="prefrontal.workflow",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="schedule_add",
            payload={
                "title": intent_result.get("title") or "日程",
                "description": intent_result.get("description", ""),
                "start_time": intent_result.get("start_time"),
                "end_time": intent_result.get("end_time"),
                "schedule_type": intent_result.get("schedule_type", "appointment"),
            },
            metadata=metadata,
        )
        try:
            response = await self.router.route(packet)
            if response.is_response():
                return response.payload
        except Exception:
            pass
        return {}

    async def _check_proactive(
        self,
        user_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """通过 prefrontal.planner 决策是否应发送主动确认消息。"""
        packet = Packet(
            source="prefrontal.workflow",
            target="prefrontal.planner",
            packet_type=PacketType.REQUEST,
            channel="proactive_should_send",
            payload={"user": user_id},
            metadata=metadata,
        )
        try:
            response = await self.router.route(packet)
            if response.is_response():
                return response.payload
        except Exception:
            pass
        return {}


__all__ = ["ChatWorkflow"]
