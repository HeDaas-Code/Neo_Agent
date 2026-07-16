"""
CentralRouter 单元测试。
"""

import asyncio
import time

import pytest

from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.packet import Packet, PacketType


class EchoModule(BaseModule):
    module_id = "test.echo"
    module_type = "test"

    async def handle(self, packet: Packet) -> Packet:
        return packet.response({"echo": packet.payload})


class SlowModule(BaseModule):
    module_id = "test.slow"
    module_type = "test"

    async def handle(self, packet: Packet) -> Packet:
        await asyncio.sleep(0.01)
        return packet.response({"slow": True})


def test_register_and_route():
    router = CentralRouter()
    try:
        module = EchoModule(router)
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="test.echo",
            packet_type=PacketType.REQUEST,
            channel="chat",
            payload={"msg": "hello"},
        )
        response = asyncio.run(router.route(packet))

        assert response.is_response()
        assert response.payload["echo"]["msg"] == "hello"
    finally:
        asyncio.run(router.shutdown())


def test_route_to_unknown_module():
    router = CentralRouter()
    try:
        packet = Packet(
            source="test.client",
            target="test.unknown",
            packet_type=PacketType.REQUEST,
            channel="chat",
            payload={},
        )
        response = asyncio.run(router.route(packet))
        assert response.is_error()
        assert "未找到" in response.payload["error"]
    finally:
        asyncio.run(router.shutdown())


def test_router_latency_under_1ms():
    """
    路由开销应小于 1ms（MVP 质量目标）。
    """
    router = CentralRouter()
    try:
        module = EchoModule(router)
        router.register_module(module.module_id, module)
        asyncio.run(router.initialize())

        packet = Packet(
            source="test.client",
            target="test.echo",
            packet_type=PacketType.REQUEST,
            channel="chat",
            payload={"msg": "hello"},
        )

        times = []
        for _ in range(100):
            start = time.perf_counter()
            asyncio.run(router.route(packet))
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        print(f"平均路由耗时: {avg_ms:.3f}ms, 最大: {max_ms:.3f}ms")
        assert avg_ms < 1.0, f"平均路由耗时 {avg_ms:.3f}ms 超过 1ms"
    finally:
        asyncio.run(router.shutdown())


def test_event_publish_and_subscribe():
    router = CentralRouter()
    received = []

    async def handler(packet: Packet):
        received.append(packet.payload)

    router.subscribe("test_channel", handler)

    packet = Packet(
        source="test.publisher",
        target="",
        packet_type=PacketType.EVENT,
        channel="test_channel",
        payload={"event": "test"},
    )

    async def _run():
        await router.initialize()
        await router.publish(packet)
        await asyncio.sleep(0.05)

    try:
        asyncio.run(_run())
        assert len(received) == 1
        assert received[0]["event"] == "test"
    finally:
        asyncio.run(router.shutdown())
