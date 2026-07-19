"""
LLMCore 单元测试。

通过 monkeypatch 替换 LangChainLLM，避免真实 LLM 调用。
"""

import asyncio

import pytest

from src.cortex.llm_core import LLMCore
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


def test_llm_core_chat():
    """
    测试 LLMCore 处理 llm_chat 请求。
    """
    router = CentralRouter()
    llm_core = LLMCore(router)

    # 模拟 LangChainLLM.chat 直接返回固定字符串
    def _mock_chat(messages, tools=None):
        return "mock-reply"

    def _mock_get_model_info():
        return {"model_type": "main", "model_name": "mock-model"}

    try:
        asyncio.run(router.initialize())
        router.register_module(llm_core.module_id, llm_core)

        # 延迟初始化后替换 chat 方法
        llm_core._get_model_router().main_llm.chat = _mock_chat
        llm_core._get_model_router().main_llm.get_model_info = _mock_get_model_info

        packet = Packet(
            source="test.client",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="llm_chat",
            payload={"messages": [{"role": "user", "content": "你好"}], "task_type": "main"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["content"] == "mock-reply"
        assert response.payload["role"] == "assistant"
    finally:
        asyncio.run(router.shutdown())


def test_llm_core_template():
    """
    测试 LLMCore 处理 llm_template 请求。
    """
    router = CentralRouter()
    llm_core = LLMCore(router)

    def _mock_chat_with_template(template, variables, history=None, tools=None):
        return f"template-reply: {variables.get('name')}"

    try:
        asyncio.run(router.initialize())
        router.register_module(llm_core.module_id, llm_core)
        llm_core._get_model_router().main_llm.chat_with_template = _mock_chat_with_template

        packet = Packet(
            source="test.client",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="llm_template",
            payload={"template": "你好 {name}", "variables": {"name": "Neo"}, "task_type": "main"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["content"] == "template-reply: Neo"
    finally:
        asyncio.run(router.shutdown())


def test_llm_core_unknown_channel():
    """
    测试 LLMCore 处理未知通道。
    """
    router = CentralRouter()
    llm_core = LLMCore(router)

    try:
        router.register_module(llm_core.module_id, llm_core)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="unknown",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["status"] == "unknown_channel"
    finally:
        asyncio.run(router.shutdown())


def test_llm_core_tools_channel():
    """
    测试 LLMCore 返回已注册工具列表。
    """
    router = CentralRouter()
    llm_core = LLMCore(router)

    try:
        router.register_module(llm_core.module_id, llm_core)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="tools",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert "tools" in response.payload
        tool_names = {t["name"] for t in response.payload["tools"]}
        assert "system_time" in tool_names
    finally:
        asyncio.run(router.shutdown())


def test_llm_core_tool_call_channel():
    """
    测试 LLMCore 执行指定工具调用。
    """
    router = CentralRouter()
    llm_core = LLMCore(router)

    try:
        router.register_module(llm_core.module_id, llm_core)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="tool_call",
            payload={"tool_name": "system_time", "tool_args": {}},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["tool_name"] == "system_time"
        assert "output" in response.payload["result"]
        assert "错误" not in response.payload["result"].get("output", "")
    finally:
        asyncio.run(router.shutdown())


def test_llm_core_tool_call_not_found():
    """
    测试 LLMCore 对未注册工具返回错误。
    """
    router = CentralRouter()
    llm_core = LLMCore(router)

    try:
        router.register_module(llm_core.module_id, llm_core)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="cortex.llm_core",
            packet_type=PacketType.REQUEST,
            channel="tool_call",
            payload={"tool_name": "non_existent_tool", "tool_args": {}},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["tool_name"] == "non_existent_tool"
        assert "TOOL_NOT_FOUND" == response.payload["result"].get("code")
    finally:
        asyncio.run(router.shutdown())
