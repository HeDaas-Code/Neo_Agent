"""
Stage E.1 - E2E test: chat flow (send message -> receive streaming reply).

目标：
  1. 启动 FastAPI app（直接 import 单例；用 ``starlette.testclient.TestClient``
     同步驱动 WebSocket / HTTP 协议）。
  2. 通过 WebSocket ``/ws/chat`` 连接。
  3. 发送 ``{"type": "message", "content": "..."}``。
  4. 接收回复（当前为 echo 形态；未来 chat_stream 接入后会得到多个 chunk + done）。
  5. 验证聚合后的回复非空。

兼容性：
  - 使用 ``unittest`` + ``unittest.IsolatedAsyncioTestCase``，不依赖 pytest。
  - ``starlette.testclient.TestClient`` 是 FastAPI 自带依赖。
  - 当 ``fastapi`` / ``starlette`` 未安装时，整个测试类被 skip。
  - 当 ``/ws/chat`` 仅实现 echo（Stage A.2 现状）时，断言只校验
    "ack/echo/chunk" 中的一种，**不**强制要求 chunk/done 协议。
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

# 让 tests/e2e/*.py 能 import src.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 依赖检查：fastapi / starlette
try:
    from starlette.testclient import TestClient  # type: ignore
    from src.web.backend.main import app  # type: ignore
    _DEPS_OK = True
    _IMPORT_ERROR: Optional[BaseException] = None
except Exception as exc:  # noqa: BLE001
    TestClient = None  # type: ignore
    app = None  # type: ignore
    _DEPS_OK = False
    _IMPORT_ERROR = exc


_SKIP_REASON = (
    f"缺少 fastapi/starlette 或 app 不可导入: {_IMPORT_ERROR}"
    if not _DEPS_OK else ""
)


def _route_exists(test_client: Any, path: str) -> bool:
    """探测后端是否注册了某个 HTTP 路由。"""
    try:
        router = test_client.app.router
    except Exception:  # noqa: BLE001
        return True  # 无法判断时默认存在，让 HTTP 404 决定
    for route in router.routes:
        # starlette >=0.29: route.path; 老版本用 route.path
        route_path = getattr(route, "path", None) or getattr(route, "path_format", None)
        if route_path == path:
            return True
    return False


def _ws_route_exists(test_client: Any, ws_path: str) -> bool:
    """探测后端是否注册了某个 WebSocket 路由。"""
    try:
        router = test_client.app.router
    except Exception:  # noqa: BLE001
        return False
    ws_routes = getattr(router, "ws_routes", []) or []
    for route in ws_routes:
        route_path = getattr(route, "path", None) or getattr(route, "path_format", None)
        if route_path == ws_path:
            return True
    return False


@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestChatFlow(unittest.TestCase):
    """
    ``/ws/chat`` 端点的最小可运行 E2E 测试。

    本类用同步 ``TestClient``，因此继承 ``unittest.TestCase`` 即可。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health_endpoint(self) -> None:
        """健康检查端点应返回 ``status == ok``。"""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200, f"health 状态码异常: {resp.text}")
        body = resp.json()
        self.assertEqual(body.get("status"), "ok")
        self.assertIn("version", body)
        self.assertIn("timestamp", body)

    def test_chat_endpoint_placeholder(self) -> None:
        """``/api/chat`` 占位端点应可访问（Stage A.3 存在）。"""
        if not _route_exists(self.client, "/api/chat"):
            self.skipTest("/api/chat 路由未注册（可能在更早阶段）")
        resp = self.client.get("/api/chat")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIsInstance(body, dict)

    def test_ws_chat_send_and_receive(self) -> None:
        """主流程：连上 ``/ws/chat`` → 发送消息 → 收到非空响应。"""
        if not _ws_route_exists(self.client, "/ws/chat"):
            self.skipTest("/ws/chat WebSocket 路由未注册")

        with self.client.websocket_connect("/ws/chat") as websocket:
            # 当前实现下，服务器 accept 后立刻发 ``ack``；
            # 无论 ack / echo 谁先到，第一帧都应带 ``type`` 字段。
            websocket.send_json({"type": "message", "content": "你好"})
            first = websocket.receive_json()
            self.assertIsInstance(first, dict)
            self.assertIn("type", first)
            self.assertIn(first.get("type"), ["ack", "echo", "chunk"])

            # 至少再收一帧（echo / chunk / done）来形成最小回环
            second = websocket.receive_json()
            self.assertIsInstance(second, dict)
            self.assertIn("type", second)
            self.assertIn(
                second.get("type"),
                ["ack", "echo", "chunk", "done"],
                f"非预期的第二帧类型: {second!r}",
            )

    def test_ws_chat_aggregate_response_non_empty(self) -> None:
        """聚合接收到的所有 chunk / echo，验证最终回复非空。"""
        if not _ws_route_exists(self.client, "/ws/chat"):
            self.skipTest("/ws/chat WebSocket 路由未注册")

        aggregated_chunks: List[str] = []
        with self.client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"type": "message", "content": "hello world"})

            # 收若干帧（带超时兜底），直到遇到 done 或超时
            deadline_loops = 20
            for _ in range(deadline_loops):
                try:
                    frame = websocket.receive_json()
                except Exception:  # noqa: BLE001
                    break
                if not isinstance(frame, dict):
                    continue
                ftype = frame.get("type")
                if ftype == "chunk":
                    chunk = frame.get("chunk") or frame.get("data") or ""
                    if isinstance(chunk, str):
                        aggregated_chunks.append(chunk)
                elif ftype == "echo":
                    data = frame.get("data") or {}
                    content = (
                        data.get("content")
                        if isinstance(data, dict)
                        else str(data)
                    )
                    if content:
                        aggregated_chunks.append(str(content))
                elif ftype == "done":
                    break
                elif ftype == "ack":
                    # ack 不计入聚合，但允许继续收
                    continue
                else:
                    # 未知类型不报错
                    continue

        aggregated = "".join(aggregated_chunks)
        # 即便只是 echo，content 应当被聚合到非空字符串里
        self.assertTrue(
            aggregated.strip(),
            "聚合后的回复内容为空（send/receive 回环未生效）",
        )


@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestChatFlowAsync(unittest.IsolatedAsyncioTestCase):
    """
    异步风格 E2E：演示 ``unittest.IsolatedAsyncioTestCase`` 用法，
    未来 Stage B.2 替换 echo 为真 chat_stream 时可直接复用。
    """

    async def asyncSetUp(self) -> None:
        self.client = TestClient(app)
        if not _ws_route_exists(self.client, "/ws/chat"):
            self.skipTest("/ws/chat WebSocket 路由未注册")

    async def test_async_chat_send_and_receive(self) -> None:
        """
        在事件循环中跑一遍 send/receive，验证 async 路径通畅。
        """
        loop = asyncio.get_running_loop()

        def _drive() -> Dict[str, Any]:
            with self.client.websocket_connect("/ws/chat") as ws:
                ws.send_json({"type": "message", "content": "ping"})
                # 阻塞调用 OK：在子线程中跑
                first = ws.receive_json()
                second = ws.receive_json()
                return {"first": first, "second": second}

        result = await loop.run_in_executor(None, _drive)
        self.assertIn("first", result)
        self.assertIn("second", result)
        for k in ("first", "second"):
            frame = result[k]
            self.assertIsInstance(frame, dict)
            self.assertIn("type", frame)


# ----------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
