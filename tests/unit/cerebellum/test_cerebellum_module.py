"""
CerebellumModule 单元测试。

使用 fake 工具类避免真实 LLM / 数据库调用。
"""

import asyncio

import pytest

from src.cerebellum.module import CerebellumModule
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class FakeDatabaseManager:
    """模拟数据库管理器。"""

    def __init__(self, *args, **kwargs):
        pass


class FakeAgentVisionTool:
    """模拟视觉工具。"""

    def __init__(self, db_manager=None):
        self.db = db_manager

    def should_use_vision(self, user_query: str, use_llm: bool = True) -> bool:
        return "视觉" in user_query

    def get_vision_context(self, user_query: str):
        if not self.should_use_vision(user_query):
            return None
        return {
            "environment": {"name": "测试房间"},
            "object_count": 2,
        }

    def get_vision_summary(self, context):
        if not context:
            return "未获取到视觉信息"
        return f"👁️ [视觉感知] 环境: {context['environment']['name']}"

    def switch_environment(self, to_env_uuid: str) -> bool:
        return to_env_uuid == "valid-env-uuid"


class FakeScheduleIntentTool:
    """模拟日程意图识别工具。"""

    def __init__(self):
        pass

    def recognize_intent(self, user_input: str, character_name: str = "智能体", context: str = ""):
        return {
            "has_schedule_intent": True,
            "schedule_type": "appointment",
            "title": "测试日程",
            "confidence": 0.95,
        }


class FakeInterruptQuestionTool:
    """模拟中断提问工具。"""

    def __init__(self):
        self.question_callback = None

    def set_question_callback(self, callback):
        self.question_callback = callback

    def ask_user(self, question: str, context: str = "") -> str:
        if self.question_callback is None:
            return "【系统错误】提问功能未配置"
        return self.question_callback(question)


class FakeNPSBridgeTool:
    """模拟 NPS 桥接工具。"""

    def __init__(self, nps_invoker=None):
        self.nps_invoker = nps_invoker

    def call_nps_tool(self, tool_name: str, query: str, **kwargs):
        return {"success": True, "tool_name": tool_name, "query": query}

    def get_available_tools(self):
        return {"success": True, "tools": [{"tool_id": "systime", "name": "系统时间"}], "count": 1}


class FakeExpressionStyleManager:
    """模拟表达风格管理器。"""

    def __init__(self, db_manager=None):
        self.db = db_manager

    def add_agent_expression(self, expression: str, meaning: str, category: str = "通用") -> str:
        return "expr-uuid-123"

    def get_agent_expressions(self, active_only: bool = True):
        return [{"expression": "wc", "meaning": "表示惊讶"}]

    def learn_user_expressions(self, messages: list, current_round: int = 0):
        return [{"expression_pattern": "hhh", "meaning": "笑声"}]

    def get_statistics(self):
        return {
            "agent_expressions": {"total": 1, "active": 1, "total_usage": 0},
            "user_habits": {"total": 2, "high_confidence": 1, "medium_confidence": 1},
        }


@pytest.fixture
def cerebellum_module(monkeypatch):
    """使用 fake 工具类构造 CerebellumModule 实例。"""
    monkeypatch.setattr("src.cerebellum.module.DatabaseManager", FakeDatabaseManager)
    monkeypatch.setattr("src.cerebellum.module.AgentVisionTool", FakeAgentVisionTool)
    monkeypatch.setattr("src.cerebellum.module.ScheduleIntentTool", FakeScheduleIntentTool)
    monkeypatch.setattr("src.cerebellum.module.InterruptQuestionTool", FakeInterruptQuestionTool)
    monkeypatch.setattr("src.cerebellum.module.NPSBridgeTool", FakeNPSBridgeTool)
    monkeypatch.setattr("src.cerebellum.module.ExpressionStyleManager", FakeExpressionStyleManager)

    router = CentralRouter()
    module = CerebellumModule(router)
    router.register_module(module.module_id, module)
    yield module


def test_cerebellum_module_vision_should_use(cerebellum_module):
    """测试 vision_should_use 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="vision_should_use",
            payload={"query": "开启视觉", "use_llm": False},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["should_use"] is True
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_vision_context(cerebellum_module):
    """测试 vision_context 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="vision_context",
            payload={"query": "视觉上下文", "use_llm": False},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["context"]["environment"]["name"] == "测试房间"
        assert "测试房间" in response.payload["summary"]
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_vision_summary(cerebellum_module):
    """测试 vision_summary 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="vision_summary",
            payload={"context": {"environment": {"name": "会议室"}}},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert "会议室" in response.payload["summary"]
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_vision_switch(cerebellum_module):
    """测试 vision_switch 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="vision_switch",
            payload={"to_env_uuid": "valid-env-uuid"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["success"] is True
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_vision_switch_missing_uuid(cerebellum_module):
    """测试 vision_switch 通道缺少 to_env_uuid 时返回错误。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="vision_switch",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_error()
        assert response.payload["code"] == "INVALID_REQUEST"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_schedule_intent(cerebellum_module):
    """测试 schedule_intent 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="schedule_intent",
            payload={
                "user_input": "明天下午开会",
                "character_name": "Neo",
                "context": "",
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["has_schedule_intent"] is True
        assert response.payload["title"] == "测试日程"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_interrupt_ask(cerebellum_module):
    """测试 interrupt_ask 通道。"""
    module = cerebellum_module
    router = module.router

    def fake_callback(question: str) -> str:
        return "是的"

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="interrupt_ask",
            payload={
                "question": "需要继续吗？",
                "context": "任务执行中",
                "callback": fake_callback,
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["answer"] == "是的"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_interrupt_ask_missing_callback(cerebellum_module):
    """测试 interrupt_ask 通道缺少 callback 时返回错误。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="interrupt_ask",
            payload={"question": "需要继续吗？"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_error()
        assert response.payload["code"] == "INVALID_REQUEST"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_nps_call(cerebellum_module):
    """测试 nps_call 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="nps_call",
            payload={"tool_name": "systime", "query": "", "kwargs": {}},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["success"] is True
        assert response.payload["tool_name"] == "systime"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_nps_call_missing_tool_name(cerebellum_module):
    """测试 nps_call 通道缺少 tool_name 时返回错误。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="nps_call",
            payload={"query": "", "kwargs": {}},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_error()
        assert response.payload["code"] == "INVALID_REQUEST"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_nps_list(cerebellum_module):
    """测试 nps_list 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="nps_list",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["success"] is True
        assert response.payload["count"] == 1
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_expression_agent_add(cerebellum_module):
    """测试 expression_agent_add 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="expression_agent_add",
            payload={"expression": "wc", "meaning": "表示惊讶", "category": "感叹词"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["uuid"] == "expr-uuid-123"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_expression_agent_add_missing_field(cerebellum_module):
    """测试 expression_agent_add 通道缺少字段时返回错误。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="expression_agent_add",
            payload={"expression": "wc"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_error()
        assert response.payload["code"] == "INVALID_REQUEST"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_expression_agent_list(cerebellum_module):
    """测试 expression_agent_list 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="expression_agent_list",
            payload={"active_only": True},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert len(response.payload["expressions"]) == 1
        assert response.payload["expressions"][0]["expression"] == "wc"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_expression_user_learn(cerebellum_module):
    """测试 expression_user_learn 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="expression_user_learn",
            payload={
                "messages": [{"role": "user", "content": "hhh"}],
                "current_round": 5,
            },
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert len(response.payload["habits"]) == 1
        assert response.payload["habits"][0]["expression_pattern"] == "hhh"
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_expression_stats(cerebellum_module):
    """测试 expression_stats 通道。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="expression_stats",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["agent_expressions"]["total"] == 1
        assert response.payload["user_habits"]["total"] == 2
    finally:
        asyncio.run(router.shutdown())


def test_cerebellum_module_unknown_channel(cerebellum_module):
    """测试未知通道处理。"""
    module = cerebellum_module
    router = module.router

    try:
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cerebellum.toolkit",
            packet_type=PacketType.REQUEST,
            channel="unknown_channel",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "unknown_channel"
    finally:
        asyncio.run(router.shutdown())
