"""
Packet 单元测试。
"""

import pytest

from src.nervous_system.router.packet import Packet, PacketType, Priority


class TestPacket:
    def test_create_request_packet(self):
        packet = Packet(
            source="cortex.echo",
            target="limbic.hippocampus",
            packet_type=PacketType.REQUEST,
            channel="memory_query",
            payload={"query": "今天天气如何"},
        )
        assert packet.source == "cortex.echo"
        assert packet.target == "limbic.hippocampus"
        assert packet.channel == "memory_query"
        assert packet.is_request()
        assert not packet.is_event()

    def test_error_packet(self):
        origin = Packet(
            source="http.gateway",
            target="unknown.module",
            packet_type=PacketType.REQUEST,
            channel="chat",
            payload={},
        )
        error = Packet.error(origin, "module not found", code="MODULE_NOT_FOUND")
        assert error.is_error()
        assert error.trace_id == origin.trace_id
        assert error.target == origin.source
        assert error.payload["code"] == "MODULE_NOT_FOUND"

    def test_response_packet(self):
        request = Packet(
            source="http.gateway",
            target="cortex.echo",
            packet_type=PacketType.REQUEST,
            channel="chat",
            payload={"content": "你好"},
        )
        response = request.response({"role": "assistant", "content": "你好！"})
        assert response.is_response()
        assert response.source == request.target
        assert response.target == request.source
        assert response.trace_id == request.trace_id
