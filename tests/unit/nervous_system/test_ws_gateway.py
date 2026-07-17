"""
WebSocketGateway 单元测试。

验证 WebSocketGateway 能把 /ws/chat 消息路由到 CentralRouter，
并正确返回流式 Packet（chunk / done / error）。
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from src.nervous_system.gateway.base_gateway import GatewayRequest
from src.nervous_system.gateway.ws_gateway import WebSocketGateway
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class FakeWorkflowModule:
    """模拟 prefrontal.workflow 模块。"""

    module_id = "prefrontal.workflow"
    module_type = "prefrontal"

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass

    async def handle(self, packet: Packet) -> Packet:
        return packet.response({"role": "assistant", "content": "fake-sync-reply"})

    async def handle_stream(self, packet: Packet) -> AsyncIterator[Packet]:
        if packet.channel == "chat_workflow":
            yield packet.stream_chunk({"role": "assistant", "content": "hello"})
            yield packet.stream_chunk({"role": "assistant", "content": " world"})
            yield packet.stream_done()
        else:
            response = await self.handle(packet)
            if response.is_error():
                yield response
                return
            yield packet.stream_chunk(response.payload)
            yield packet.stream_done()


@pytest.fixture
def router_with_ws_gateway():
    """构造已注册 fake workflow 与 WebSocketGateway 实例。"""
    router = CentralRouter()
    ws_gateway = WebSocketGateway(router)
    fake_workflow = FakeWorkflowModule()

    # WebSocketGateway 是网关，不作为 BaseModule 注册到 router
    router.register_module(fake_workflow.module_id, fake_workflow)

    asyncio.run(router.initialize())
    asyncio.run(ws_gateway.start())
    yield router, ws_gateway
    asyncio.run(ws_gateway.stop())
    asyncio.run(router.shutdown())


def test_ws_gateway_handle_routes_to_workflow(router_with_ws_gateway):
    """测试同步 handle 将 /ws/chat 路由到 prefrontal.workflow。"""
    _router, ws_gateway = router_with_ws_gateway

    request = GatewayRequest(
        method="WS_MESSAGE",
        path="/ws/chat",
        body={"user_input": "你好"},
        metadata={"user_id": "test-user", "conn_id": "conn-1"},
    )
    response = asyncio.run(ws_gateway.handle(request))

    assert response.status_code == 200
    assert response.body["type"] == "message"
    assert response.body["data"]["content"] == "fake-sync-reply"


def test_ws_gateway_handle_stream_for_chat(router_with_ws_gateway):
    """测试流式 handle_stream 将 /ws/chat 路由到 workflow 的流式通道。"""
    _router, ws_gateway = router_with_ws_gateway

    request = GatewayRequest(
        method="WS_MESSAGE",
        path="/ws/chat",
        body={"user_input": "你好"},
        metadata={"user_id": "test-user", "conn_id": "conn-1"},
    )

    chunks = []
    done_seen = False

    async def _collect():
        nonlocal done_seen
        async for packet in ws_gateway.handle_stream(request):
            if packet.packet_type == PacketType.STREAM:
                event = packet.payload.get("stream_event")
                if event == "chunk":
                    chunks.append(packet.payload.get("content", ""))
                elif event == "done":
                    done_seen = True

    asyncio.run(_collect())

    assert "".join(chunks) == "hello world"
    assert done_seen is True


def test_ws_gateway_register_and_push(router_with_ws_gateway):
    """测试连接注册与 push 方法。"""
    _router, ws_gateway = router_with_ws_gateway

    class FakeWebSocket:
        def __init__(self):
            self.sent: list = []

        async def send_json(self, data):
            self.sent.append(data)

    ws = FakeWebSocket()
    asyncio.run(ws_gateway.register_connection("conn-1", ws))
    asyncio.run(ws_gateway.push("conn-1", {"type": "test"}))

    assert len(ws.sent) == 1
    assert ws.sent[0]["type"] == "test"

    asyncio.run(ws_gateway.unregister_connection("conn-1"))
    assert "conn-1" not in ws_gateway._connections


def test_ws_gateway_push_unknown_connection(router_with_ws_gateway):
    """测试向未知连接 push 不抛异常。"""
    _router, ws_gateway = router_with_ws_gateway
    # 不应抛异常
    asyncio.run(ws_gateway.push("unknown", {"type": "test"}))
