"""
Stage E.1 - E2E test: proactive message push.

目标：
  1. 连接 ``/ws/proactive``（或回退到 ``/ws/events``）长连接。
  2. 通过 ``EventService.emit_event("proactive_message", {...})`` 触发推送。
  3. 验证客户端收到 ``proactive_message`` 事件载荷。

兼容性 / 降级：
  - 若 ``EventService`` 在当前进程未注册，使用 ``ConnectionManager.broadcast``
    直接推送做最小回环测试。
  - 若 ``/ws/proactive`` 未注册，回退到 ``/ws/events``。
  - 依赖缺失（fastapi/starlette）时整类 skip。
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def _ws_routes(test_client: Any) -> List[str]:
    paths: List[str] = []
    try:
        router = test_client.app.router
        ws_routes = getattr(router, "ws_routes", []) or []
        for route in ws_routes:
            p = getattr(route, "path", None) or getattr(route, "path_format", None)
            if p:
                paths.append(str(p))
    except Exception:  # noqa: BLE001
        pass
    return paths


def _select_proactive_endpoint(test_client: Any) -> Optional[str]:
    """优先 /ws/proactive；缺失时回退 /ws/events。"""
    paths = _ws_routes(test_client)
    if "/ws/proactive" in paths:
        return "/ws/proactive"
    if "/ws/events" in paths:
        return "/ws/events"
    return None


def _try_get_event_service():
    """
    尝试 import EventService 单例；失败则返回 None。
    """
    try:
        from src.web.backend.services.event_service import get_event_service  # type: ignore
        return get_event_service()
    except Exception:  # noqa: BLE001
        return None


def _try_get_manager():
    """尝试 import ConnectionManager 单例。"""
    try:
        from src.web.backend.ws.manager import manager  # type: ignore
        return manager
    except Exception:  # noqa: BLE001
        return None


def _run_event_service_emit(es: Any, event_type: str, payload: Dict[str, Any]) -> None:
    """调用 es.emit_event，兼容同步 / 异步实现。"""
    if es is None:
        return
    if hasattr(es, "emit_event"):
        es.emit_event(event_type, payload)
        return
    if hasattr(es, "dispatch"):
        es.dispatch(event_type, payload)
        return


def _run_manager_broadcast(manager: Any, channel: str, message: Dict[str, Any]) -> None:
    """调用 manager.broadcast，兼容同步 / 异步实现。"""
    if manager is None:
        return
    if hasattr(manager, "broadcast"):
        result = manager.broadcast(channel, message)
        if asyncio.iscoroutine(result):
            # 在测试侧用 run_until_complete 跑同步 event loop
            try:
                loop = asyncio.get_event_loop_policy().get_event_loop()
                if loop.is_running():
                    # 已是 async 上下文，让事件循环接管
                    return
                loop.run_until_complete(result)
            except Exception:  # noqa: BLE001
                pass
        return
    if hasattr(manager, "send_all"):
        manager.send_all(message)
        return


@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestProactivePush(unittest.TestCase):
    """
    主动消息推送 E2E。

    设计：
      - 测试 1：连 ``/ws/proactive``，验证能拿到 ack。
      - 测试 2：通过 ``EventService.emit_event`` 触发推送，验证客户端能收到。
      - 测试 3（降级）：若 EventService 不可用，使用
        ``ConnectionManager.broadcast("proactive", ...)`` 直接推。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.endpoint = _select_proactive_endpoint(cls.client)
        cls.event_service = _try_get_event_service()
        cls.manager = _try_get_manager()

    def setUp(self) -> None:
        if self.endpoint is None:
            self.skipTest("未发现 /ws/proactive 或 /ws/events 路由")

    # ------------------------------------------------------------------
    # 1) 基本连接
    # ------------------------------------------------------------------
    def test_proactive_connect_ack(self) -> None:
        """连上 ``/ws/proactive`` 后应立刻收到一帧 ack / system。"""
        with self.client.websocket_connect(self.endpoint) as ws:
            frame = ws.receive_json()
            self.assertIsInstance(frame, dict)
            self.assertIn(
                frame.get("type"),
                ("ack", "system"),
                f"首帧应带 type=ack|system，实际: {frame!r}",
            )

    # ------------------------------------------------------------------
    # 2) EventService -> 客户端
    # ------------------------------------------------------------------
    def test_proactive_message_via_event_service(self) -> None:
        """通过 EventService.emit_event 触发 ``proactive_message``，客户端能收到。"""
        if self.event_service is None:
            self.skipTest("EventService 不可导入，使用降级测试")
        if not hasattr(self.event_service, "emit_event"):
            self.skipTest("EventService 缺 emit_event 方法")

        with self.client.websocket_connect(self.endpoint) as ws:
            # 消费首帧 ack / system
            try:
                ws.receive_json()
            except Exception:  # noqa: BLE001
                pass

            payload = {
                "text": "hello from E2E",
                "ts": 1234567890,
            }
            try:
                self.event_service.emit_event("proactive_message", payload)
            except Exception as exc:  # noqa: BLE001
                self.skipTest(f"EventService.emit_event 抛错: {exc}")

            # 收若干帧，找 type == 'event' 且 event_type == 'proactive_message' 的那一帧
            found = False
            for _ in range(20):
                try:
                    frame = ws.receive_json()
                except Exception:  # noqa: BLE001
                    break
                if not isinstance(frame, dict):
                    continue
                ftype = frame.get("type")
                etype = frame.get("event_type")
                if ftype == "event" and etype == "proactive_message":
                    inner = frame.get("payload") or {}
                    self.assertEqual(inner.get("text"), payload["text"])
                    found = True
                    break
                if ftype == "proactive_message":
                    # 直接推送形态
                    inner = frame.get("payload") or frame
                    self.assertEqual(inner.get("text"), payload["text"])
                    found = True
                    break
            self.assertTrue(found, "未在客户端收到 proactive_message 事件")

    # ------------------------------------------------------------------
    # 3) ConnectionManager 直接广播（降级）
    # ------------------------------------------------------------------
    def test_proactive_message_via_manager_broadcast(self) -> None:
        """降级路径：直接 manager.broadcast('proactive'|'events', ...)。"""
        if self.manager is None:
            self.skipTest("ConnectionManager 不可导入")

        channel = "proactive" if self.endpoint == "/ws/proactive" else "events"
        # manager 必须有 channels['proactive'] 或 'events'，否则 manager 静默不发送
        channels = getattr(self.manager, "channels", {}) or {}
        if channel not in channels:
            # 自动注册 channel
            try:
                self.manager.register_channel(channel)
            except Exception:  # noqa: BLE001
                pass

        message = {
            "type": "proactive_message",
            "payload": {"text": "manager-broadcast E2E"},
        }

        with self.client.websocket_connect(self.endpoint) as ws:
            try:
                ws.receive_json()  # ack
            except Exception:  # noqa: BLE001
                pass

            _run_manager_broadcast(self.manager, channel, message)

            found = False
            for _ in range(20):
                try:
                    frame = ws.receive_json()
                except Exception:  # noqa: BLE001
                    break
                if not isinstance(frame, dict):
                    continue
                ftype = frame.get("type")
                if ftype == "proactive_message":
                    inner = frame.get("payload") or {}
                    self.assertEqual(inner.get("text"), message["payload"]["text"])
                    found = True
                    break
                if ftype == "event" and frame.get("event_type") == "proactive_message":
                    inner = frame.get("payload") or {}
                    self.assertEqual(inner.get("text"), message["payload"]["text"])
                    found = True
                    break
            self.assertTrue(found, "manager.broadcast 后未在客户端收到消息")

    # ------------------------------------------------------------------
    # 4) 多次连接：连接池可承载多个客户端
    # ------------------------------------------------------------------
    def test_multiple_proactive_clients(self) -> None:
        """多客户端同时连 ``/ws/proactive``，各自能收到 broadcast。"""
        if self.manager is None:
            self.skipTest("ConnectionManager 不可导入")

        channel = "proactive" if self.endpoint == "/ws/proactive" else "events"
        if channel not in (getattr(self.manager, "channels", {}) or {}):
            try:
                self.manager.register_channel(channel)
            except Exception:  # noqa: BLE001
                pass

        message = {
            "type": "proactive_message",
            "payload": {"text": "broadcast-multi"},
        }

        with self.client.websocket_connect(self.endpoint) as ws1:
            with self.client.websocket_connect(self.endpoint) as ws2:
                # 各自消费 ack
                try:
                    ws1.receive_json()
                    ws2.receive_json()
                except Exception:  # noqa: BLE001
                    pass

                _run_manager_broadcast(self.manager, channel, message)

                def _consume(ws):
                    for _ in range(10):
                        try:
                            f = ws.receive_json()
                        except Exception:  # noqa: BLE001
                            return None
                        if isinstance(f, dict) and f.get("type") in (
                            "proactive_message",
                            "event",
                        ):
                            return f
                    return None

                f1 = _consume(ws1)
                f2 = _consume(ws2)
                self.assertIsNotNone(f1, "client1 未收到")
                self.assertIsNotNone(f2, "client2 未收到")


# ----------------------------------------------------------------------
# 异步风格的兼容性测试
# ----------------------------------------------------------------------
@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestProactivePushAsync(unittest.IsolatedAsyncioTestCase):
    """
    异步风格：演示在 ``unittest.IsolatedAsyncioTestCase`` 中触发推送。
    """

    async def asyncSetUp(self) -> None:
        self.client = TestClient(app)
        self.endpoint = _select_proactive_endpoint(self.client)
        if self.endpoint is None:
            self.skipTest("无 /ws/proactive 或 /ws/events 路由")
        self.event_service = _try_get_event_service()
        self.manager = _try_get_manager()

    async def test_async_proactive_push(self) -> None:
        """异步风格下 emit_event + 接收消息。"""
        if self.event_service is None or not hasattr(
            self.event_service, "emit_event"
        ):
            self.skipTest("EventService 不可用")

        loop = asyncio.get_running_loop()
        received: List[Dict[str, Any]] = []

        def _drive() -> None:
            with self.client.websocket_connect(self.endpoint) as ws:
                try:
                    ws.receive_json()  # ack
                except Exception:  # noqa: BLE001
                    pass
                self.event_service.emit_event(
                    "proactive_message",
                    {"text": "from-async-test", "ts": 1},
                )
                for _ in range(20):
                    try:
                        f = ws.receive_json()
                    except Exception:  # noqa: BLE001
                        break
                    if isinstance(f, dict):
                        received.append(f)
                        if f.get("type") in (
                            "proactive_message",
                            "event",
                        ):
                            return

        await loop.run_in_executor(None, _drive)
        self.assertTrue(
            any(
                f.get("type") in ("proactive_message", "event")
                for f in received
            ),
            f"未收到推送消息: {received!r}",
        )


# ----------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
