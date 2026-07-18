"""
Phase 6 集成测试：验证 Web 后端通过 neo_bridge 调用 v4 神经系统。

测试范围：
- /api/health 返回 v4 模块状态
- /api/v4/gateway/{target}/{channel} 能路由到 cortex.echo
- 对未知模块返回错误响应而不是崩溃
- /api/emotion/latest 在 v4 可用时走 AmygdalaModule 并返回兼容格式
"""

import pytest
from fastapi.testclient import TestClient

from src.web.backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_includes_v4_modules(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert isinstance(data["v4_modules"], list)
    assert "cortex.echo" in data["v4_modules"]


def test_v4_gateway_echo_chat(client):
    response = client.post(
        "/api/v4/gateway/cortex.echo/chat",
        json={"content": "你好"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "trace_id" in data
    assert "data" in data
    assert data["data"]["role"] == "assistant"
    assert "你好" in data["data"]["content"]


def test_v4_gateway_unknown_module(client):
    response = client.post(
        "/api/v4/gateway/unknown.module/test",
        json={"content": "test"},
    )
    # router 返回 ERROR Packet，网关统一转 500
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert "trace_id" in data


def test_emotion_latest_compatible_with_v4(client):
    """
    /api/emotion/latest 应优先尝试 v4 Amygdala，并返回前端雷达图兼容格式。
    即使 Amygdala 没有历史数据，也应返回 200 + 8 维字典（而不是 5xx）。
    """
    response = client.get("/api/emotion/latest?user_id=default")
    assert response.status_code == 200
    data = response.json()
    expected_keys = {"cumulative", "plutchik", "last_message", "timestamp", "user_id", "historical_max"}
    assert expected_keys.issubset(set(data.keys()))
    assert data["user_id"] == "default"
    for dim in ("joy", "trust", "fear", "surprise", "sadness", "disgust", "anger", "anticipation"):
        assert dim in data["cumulative"]
        assert dim in data["plutchik"]
