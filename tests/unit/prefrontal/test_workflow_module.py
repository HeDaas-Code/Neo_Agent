"""
WorkflowModule 单元测试。

验证跨模块聊天工作流（对话 → 情感分析 → 日程创建 → 主动确认）
能通过 CentralRouter 正确编排多个神经系统模块。
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List

import pytest

from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType
from src.prefrontal.workflow_module import WorkflowModule


class FakeLLMCore:
    """模拟 LLM 核心，支持流式返回。"""

    module_id = "cortex.llm_core"
    module_type = "cortex"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def handle(self, packet: Packet) -> Packet:
        return packet.response({"role": "assistant", "content": "fake-reply"})

    async def handle_stream(self, packet: Packet) -> AsyncIterator[Packet]:
        if packet.channel == "llm_stream":
            for token in ["fake", "-", "reply"]:
                yield packet.stream_chunk({"role": "assistant", "content": token})
            yield packet.stream_done()
        else:
            response = await self.handle(packet)
            if response.is_error():
                yield response
                return
            yield packet.stream_chunk(response.payload)
            yield packet.stream_done()


class FakeHippocampus:
    """模拟海马体，记录 memory_store 调用。"""

    module_id = "limbic.hippocampus.full"
    module_type = "limbic"

    def __init__(self) -> None:
        self.stored_messages: List[Dict[str, str]] = []

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def handle(self, packet: Packet) -> Packet:
        if packet.channel == "memory_store":
            self.stored_messages.append({
                "role": packet.payload.get("role", "user"),
                "content": packet.payload.get("content", ""),
            })
            return packet.response({"status": "stored"})
        if packet.channel == "memory_query":
            return packet.response({
                "memories": [{"role": "user", "content": "previous"}],
                "total": 1,
            })
        if packet.channel == "memory_context":
            return packet.response({"context": "previous context"})
        return packet.response({"status": "ok"})


class FakeAmygdala:
    """模拟杏仁核情感分析。"""

    module_id = "limbic.amygdala"
    module_type = "limbic"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def handle(self, packet: Packet) -> Packet:
        if packet.channel == "emotion_analyze":
            return packet.response({"overall_score": 42, "joy": 0.5})
        if packet.channel == "emotion_tone":
            return packet.response({"tone_prompt": "温柔"})
        return packet.response({"status": "ok"})


class FakeCerebellum:
    """模拟小脑工具。"""

    module_id = "cerebellum.toolkit"
    module_type = "cerebellum"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def handle(self, packet: Packet) -> Packet:
        if packet.channel == "schedule_intent":
            return packet.response({
                "has_schedule_intent": True,
                "schedule_type": "appointment",
                "title": "测试日程",
                "start_time": "2026-07-18T10:00:00",
                "end_time": "2026-07-18T11:00:00",
                "confidence": 0.85,
            })
        return packet.response({"status": "ok"})


class FakePlanner:
    """模拟前额叶规划模块。"""

    module_id = "prefrontal.planner"
    module_type = "prefrontal"

    def __init__(self) -> None:
        self.schedules: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def handle(self, packet: Packet) -> Packet:
        if packet.channel == "schedule_add":
            self.schedules.append(packet.payload)
            return packet.response({
                "success": True,
                "schedule": packet.payload,
                "message": "created",
            })
        if packet.channel == "proactive_should_send":
            return packet.response({"should_send": True, "reason": "test"})
        return packet.response({"status": "ok"})


@pytest.fixture
def router_with_workflow():
    """构造已注册全部 fake 模块的 CentralRouter。"""
    router = CentralRouter()
    workflow = WorkflowModule(router)
    fake_llm = FakeLLMCore()
    fake_hippo = FakeHippocampus()
    fake_amy = FakeAmygdala()
    fake_cere = FakeCerebellum()
    fake_planner = FakePlanner()

    router.register_module(workflow.module_id, workflow)
    router.register_module(fake_llm.module_id, fake_llm)
    router.register_module(fake_hippo.module_id, fake_hippo)
    router.register_module(fake_amy.module_id, fake_amy)
    router.register_module(fake_cere.module_id, fake_cere)
    router.register_module(fake_planner.module_id, fake_planner)

    asyncio.run(router.initialize())
    yield router, workflow, fake_hippo, fake_planner
    asyncio.run(router.shutdown())


def test_chat_workflow_sync(router_with_workflow):
    """测试同步 chat_workflow 返回完整回复与工作流结果。"""
    router, _workflow, fake_hippo, fake_planner = router_with_workflow

    packet = Packet(
        source="test.client",
        target="prefrontal.workflow",
        packet_type=PacketType.REQUEST,
        channel="chat_workflow",
        payload={"user_input": "明天下午三点开会"},
    )
    response = asyncio.run(router.route(packet))

    assert response.is_response()
    assert response.payload["content"] == "fake-reply"
    assert response.payload["role"] == "assistant"

    workflow_result = response.payload.get("workflow", {})
    assert workflow_result.get("emotion", {}).get("overall_score") == 42
    assert workflow_result.get("schedule", {}).get("created", {}).get("success") is True
    assert workflow_result.get("proactive", {}).get("should_send") is True

    # 验证用户与助手消息都已落库
    roles = [m["role"] for m in fake_hippo.stored_messages]
    assert "user" in roles
    assert "assistant" in roles

    # 验证日程已创建
    assert len(fake_planner.schedules) == 1
    assert fake_planner.schedules[0]["title"] == "测试日程"


def test_chat_workflow_stream(router_with_workflow):
    """测试流式 chat_workflow 逐 token 返回 chunk 与 done。"""
    router, _workflow, fake_hippo, _fake_planner = router_with_workflow

    packet = Packet(
        source="test.client",
        target="prefrontal.workflow",
        packet_type=PacketType.REQUEST,
        channel="chat_workflow",
        payload={"user_input": "你好"},
    )

    chunks = []
    done_seen = False

    async def _collect():
        nonlocal done_seen
        async for response_packet in router.route_stream(packet):
            if response_packet.packet_type == PacketType.STREAM:
                event = response_packet.payload.get("stream_event")
                if event == "chunk":
                    chunks.append(response_packet.payload.get("content", ""))
                elif event == "done":
                    done_seen = True

    asyncio.run(_collect())

    assert "".join(chunks) == "fake-reply"
    assert done_seen is True
    assert len(fake_hippo.stored_messages) >= 1


def test_chat_workflow_missing_input(router_with_workflow):
    """测试缺少 user_input 时返回错误。"""
    router, _workflow, _fake_hippo, _fake_planner = router_with_workflow

    packet = Packet(
        source="test.client",
        target="prefrontal.workflow",
        packet_type=PacketType.REQUEST,
        channel="chat_workflow",
        payload={},
    )
    response = asyncio.run(router.route(packet))

    assert response.is_error()
    assert response.payload["code"] == "INVALID_REQUEST"