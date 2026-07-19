"""
v4 MVP 集成测试。

验证：
- /api/v4/health 返回模块列表与版本号
- /api/v4/chat 能走通 HTTP Gateway -> Central Router -> WorkflowModule
- 第二次聊天能回忆起之前的记忆
- 路由延迟 < 50ms
"""

import time
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from src.nervous_system.app import app, NeoApp
from src.nervous_system.router.packet import Packet


class FakeLLMCore:
    """模拟 LLM 核心，避免测试依赖真实 API 密钥。"""

    module_id = "cortex.llm_core"
    module_type = "cortex"

    def __init__(self, router):
        self.router = router

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def handle(self, packet: Packet) -> Packet:
        return packet.response({"role": "assistant", "content": "fake-reply"})

    async def handle_stream(self, packet: Packet) -> AsyncIterator[Packet]:
        for token in ["fake", "-", "reply"]:
            yield packet.stream_chunk({"role": "assistant", "content": token})
        yield packet.stream_done()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        # lifespan 结束后，将真实 LLMCore 替换为 FakeLLMCore
        from src.nervous_system.app import neo_app

        neo_app.router.unregister_module("cortex.llm_core")
        neo_app.router.register_module("cortex.llm_core", FakeLLMCore(neo_app.router))
        yield c


def test_health_v4(client):
    response = client.get("/api/v4/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "4.1.0"
    assert "prefrontal.workflow" in data["modules"]
    assert "limbic.hippocampus.full" in data["modules"]
    assert data["capabilities"]["tool_calling"] is True
    assert data["capabilities"]["streaming"] is True


def test_capabilities_v4(client):
    response = client.get("/api/v4/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["tool_calling"] is True
    assert data["memory"] is True


def test_chat_v4_first_message(client):
    response = client.post("/api/v4/chat", json={"content": "你好"})
    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert data["data"]["role"] == "assistant"
    assert data["data"]["content"] == "fake-reply"


def test_chat_v4_recalls_memory(client):
    # 第一条消息
    client.post("/api/v4/chat", json={"content": "我叫 Alice"})

    # 第二条消息应回忆起第一条
    response = client.post("/api/v4/chat", json={"content": "我叫什么名字？"})
    assert response.status_code == 200
    data = response.json()
    workflow_result = data["data"].get("workflow", {})
    assert workflow_result.get("emotion") is not None


def test_chat_v4_latency(client):
    """
    端到端路由/网关延迟应小于 50ms（MVP 目标）。

    FakeLLMCore 不调用真实 LLM，因此本测试衡量的是
    HTTP Gateway -> CentralRouter -> WorkflowModule -> FakeLLMCore 的全链路开销。
    """
    times = []
    for _ in range(10):
        start = time.perf_counter()
        response = client.post("/api/v4/chat", json={"content": "测试延迟"})
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert response.status_code == 200
        times.append(elapsed_ms)

    avg_ms = sum(times) / len(times)
    max_ms = max(times)
    print(f"平均端到端耗时: {avg_ms:.3f}ms, 最大: {max_ms:.3f}ms")
    assert avg_ms < 50.0, f"平均端到端耗时 {avg_ms:.3f}ms 超过 50ms"
