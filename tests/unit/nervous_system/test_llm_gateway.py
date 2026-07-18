"""
LLMGateway 单元测试。
"""

import asyncio

import pytest

from src.nervous_system.gateway.llm_gateway import LLMGateway
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class FakeLLMCore:
    """
    模拟 LLMCore 模块。
    """

    module_id = "cortex.llm_core"

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def handle(self, packet: Packet) -> Packet:
        return packet.response({"role": "assistant", "content": "fake-llm-reply"})


def test_llm_gateway_handle():
    """
    测试 LLMGateway 将请求转发给 cortex.llm_core。
    """
    router = CentralRouter()
    llm_gateway = LLMGateway(router)
    fake_core = FakeLLMCore()

    try:
        router.register_module(llm_gateway.module_id, llm_gateway)
        router.register_module(fake_core.module_id, fake_core)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="nervous_system.gateway.llm",
            packet_type=PacketType.REQUEST,
            channel="llm_chat",
            payload={"messages": [{"role": "user", "content": "你好"}]},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["content"] == "fake-llm-reply"
    finally:
        asyncio.run(router.shutdown())


def test_llm_gateway_chat_method():
    """
    测试 LLMGateway.chat 简化接口。
    """
    router = CentralRouter()
    llm_gateway = LLMGateway(router)
    fake_core = FakeLLMCore()

    try:
        router.register_module(llm_gateway.module_id, llm_gateway)
        router.register_module(fake_core.module_id, fake_core)
        asyncio.run(router.initialize())

        reply = asyncio.run(llm_gateway.chat([{"role": "user", "content": "你好"}]))
        assert reply == "fake-llm-reply"
    finally:
        asyncio.run(router.shutdown())


def test_llm_gateway_unknown_channel():
    """
    测试 LLMGateway 处理未知通道返回错误。
    """
    router = CentralRouter()
    llm_gateway = LLMGateway(router)

    try:
        router.register_module(llm_gateway.module_id, llm_gateway)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="nervous_system.gateway.llm",
            packet_type=PacketType.REQUEST,
            channel="unknown_channel",
            payload={},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_error()
        assert response.payload["code"] == "UNKNOWN_LLM_CHANNEL"
    finally:
        asyncio.run(router.shutdown())
