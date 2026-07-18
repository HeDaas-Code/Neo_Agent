"""
CerebellumModule - 小脑模块（v4.0 神经系统接入层）。

将 src.cerebellum.vision、src.cerebellum.intent、src.cerebellum.interrupt、
src.cerebellum.nps、src.cerebellum.style 中的工具能力包装为 BaseModule，
使其可以通过 CentralRouter 被其他模块调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from src.cerebellum.vision.agent_vision import AgentVisionTool
from src.cerebellum.intent.schedule_intent_tool import ScheduleIntentTool
from src.cerebellum.interrupt.interrupt_question_tool import InterruptQuestionTool
from src.cerebellum.nps.bridge_tool import NPSBridgeTool
from src.cerebellum.style.expression_style import ExpressionStyleManager
from src.core.database_manager import DatabaseManager
from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter


class CerebellumModule(BaseModule):
    """
    小脑模块。

    负责工具调用、视觉处理、快速反射等认知功能。
    """

    module_id = "cerebellum.toolkit"
    module_type = "cerebellum"

    def __init__(
        self,
        router: "CentralRouter",
        db_manager: Optional[DatabaseManager] = None,
        nps_invoker: Optional[Any] = None,
    ) -> None:
        super().__init__(router)
        self._db = db_manager or DatabaseManager()
        self._vision_tool = AgentVisionTool(self._db)
        self._schedule_intent_tool = ScheduleIntentTool()
        self._interrupt_tool = InterruptQuestionTool()
        self._nps_bridge = NPSBridgeTool(nps_invoker)
        self._expression_manager = ExpressionStyleManager(self._db)

    async def handle(self, packet: Packet) -> Packet:
        """
        处理小脑相关请求。

        Channels:
            - vision_should_use: 判断是否需要使用视觉
            - vision_context: 获取视觉上下文
            - vision_summary: 获取视觉上下文摘要
            - vision_switch: 切换环境
            - schedule_intent: 识别日程意图
            - interrupt_ask: 向用户中断提问
            - nps_call: 调用 NPS 工具
            - nps_list: 列出可用 NPS 工具
            - expression_agent_add: 添加智能体表达
            - expression_agent_list: 列出智能体表达
            - expression_user_learn: 学习用户表达习惯
            - expression_stats: 获取表达风格统计
        """
        channel = packet.channel
        payload = packet.payload

        try:
            if channel == "vision_should_use":
                return self._handle_vision_should_use(packet, payload)
            if channel == "vision_context":
                return self._handle_vision_context(packet, payload)
            if channel == "vision_summary":
                return self._handle_vision_summary(packet, payload)
            if channel == "vision_switch":
                return self._handle_vision_switch(packet, payload)
            if channel == "schedule_intent":
                return self._handle_schedule_intent(packet, payload)
            if channel == "interrupt_ask":
                return self._handle_interrupt_ask(packet, payload)
            if channel == "nps_call":
                return self._handle_nps_call(packet, payload)
            if channel == "nps_list":
                return self._handle_nps_list(packet, payload)
            if channel == "expression_agent_add":
                return self._handle_expression_agent_add(packet, payload)
            if channel == "expression_agent_list":
                return self._handle_expression_agent_list(packet, payload)
            if channel == "expression_user_learn":
                return self._handle_expression_user_learn(packet, payload)
            if channel == "expression_stats":
                return self._handle_expression_stats(packet, payload)
        except Exception as exc:  # noqa: BLE001
            return Packet.error(packet, str(exc), code="INTERNAL_ERROR")

        return packet.response({
            "status": "unknown_channel",
            "channel": channel,
        })

    def _handle_vision_should_use(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        query = payload.get("query", "")
        use_llm = payload.get("use_llm", True)
        should_use = self._vision_tool.should_use_vision(query, use_llm=use_llm)
        return packet.response({"should_use": should_use})

    def _handle_vision_context(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        query = payload.get("query", "")
        use_llm = payload.get("use_llm", True)
        context = self._vision_tool.get_vision_context(query)
        summary = self._vision_tool.get_vision_summary(context)
        return packet.response({"context": context, "summary": summary})

    def _handle_vision_summary(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        context = payload.get("context")
        summary = self._vision_tool.get_vision_summary(context)
        return packet.response({"summary": summary})

    def _handle_vision_switch(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        to_env_uuid = payload.get("to_env_uuid", "")
        if not to_env_uuid:
            return Packet.error(packet, "to_env_uuid required", code="INVALID_REQUEST")
        success = self._vision_tool.switch_environment(to_env_uuid)
        return packet.response({"success": success})

    def _handle_schedule_intent(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        user_input = payload.get("user_input", "")
        character_name = payload.get("character_name", "智能体")
        context = payload.get("context", "")
        result = self._schedule_intent_tool.recognize_intent(
            user_input=user_input,
            character_name=character_name,
            context=context,
        )
        return packet.response(result)

    def _handle_interrupt_ask(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        question = payload.get("question", "")
        context = payload.get("context", "")
        callback = payload.get("callback")

        if not callable(callback):
            return Packet.error(packet, "callback must be callable", code="INVALID_REQUEST")

        self._interrupt_tool.set_question_callback(callback)
        answer = self._interrupt_tool.ask_user(question, context=context)
        return packet.response({"answer": answer})

    def _handle_nps_call(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        tool_name = payload.get("tool_name", "")
        query = payload.get("query", "")
        kwargs = payload.get("kwargs", {})
        if not tool_name:
            return Packet.error(packet, "tool_name required", code="INVALID_REQUEST")
        result = self._nps_bridge.call_nps_tool(tool_name, query, **kwargs)
        return packet.response(result)

    def _handle_nps_list(
        self, packet: Packet, _payload: Dict[str, Any]
    ) -> Packet:
        result = self._nps_bridge.get_available_tools()
        return packet.response(result)

    def _handle_expression_agent_add(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        expression = payload.get("expression", "")
        meaning = payload.get("meaning", "")
        category = payload.get("category", "通用")
        if not expression or not meaning:
            return Packet.error(
                packet, "expression and meaning required", code="INVALID_REQUEST"
            )
        uuid = self._expression_manager.add_agent_expression(
            expression=expression, meaning=meaning, category=category
        )
        return packet.response({"uuid": uuid})

    def _handle_expression_agent_list(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        active_only = payload.get("active_only", True)
        expressions = self._expression_manager.get_agent_expressions(
            active_only=active_only
        )
        return packet.response({"expressions": expressions})

    def _handle_expression_user_learn(
        self, packet: Packet, payload: Dict[str, Any]
    ) -> Packet:
        messages = payload.get("messages", [])
        current_round = payload.get("current_round", 0)
        habits = self._expression_manager.learn_user_expressions(
            messages=messages, current_round=current_round
        )
        return packet.response({"habits": habits})

    def _handle_expression_stats(
        self, packet: Packet, _payload: Dict[str, Any]
    ) -> Packet:
        stats = self._expression_manager.get_statistics()
        return packet.response(stats)


__all__ = ["CerebellumModule"]
