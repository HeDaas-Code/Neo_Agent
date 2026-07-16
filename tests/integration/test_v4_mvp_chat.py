"""
v4.0 MVP 集成测试。

验证：
- /api/v4/health 返回模块列表
- /api/v4/chat 能走通 HTTP Gateway -> Central Router -> EchoCortex -> SimpleHippocampus
- 第二次聊天能回忆起之前的记忆
- 路由延迟 < 50ms
"""

import time

import pytest
from fastapi.testclient import TestClient

from src.nervous_system.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_v4(client):
    response = client.get("/api/v4/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "cortex.echo" in data["modules"]
    assert "limbic.hippocampus" in data["modules"]


def test_chat_v4_first_message(client):
    response = client.post("/api/v4/chat", json={"content": "你好"})
    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert data["data"]["role"] == "assistant"
    assert "你好" in data["data"]["content"]
    assert data["data"]["memory_count"] == 0


def test_chat_v4_recalls_memory(client):
    # 第一条消息
    client.post("/api/v4/chat", json={"content": "我叫 Alice"})

    # 第二条消息应回忆起第一条
    response = client.post("/api/v4/chat", json={"content": "我叫什么名字？"})
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["memory_count"] > 0


def test_chat_v4_latency(client):
    """
    端到端请求延迟应小于 50ms（MVP 目标）。
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
