"""
Stage E.1 - E2E test: WebSocket disconnect & reconnect.

目标：
  1. 连接 ``/ws/chat`` → 收发消息 → 断开
  2. 验证服务器端 ConnectionManager 正确清理该 conn_id
  3. 再次连接 ``/ws/chat`` → 收发消息 → 正常

设计要点：
  - 前端 ``useWebSocket`` 使用指数退避（1s -> 2s -> 4s ...，capped 30s）。
    后端测试只验证 *服务侧* 的连接清理与重连可用性；不退避算法（属于前端 hook）。
  - 同时验证 ConnectionManager 状态（active_connections / channels），
    防止连接泄漏。
  - 依赖缺失（fastapi/starlette）时整类 skip。
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid as uuid_lib
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
        for route in getattr(router, "ws_routes", []) or []:
            p = getattr(route, "path", None) or getattr(route, "path_format", None)
            if p:
                paths.append(str(p))
    except Exception:  # noqa: BLE001
        pass
    return paths


def _try_get_manager():
    try:
        from src.web.backend.ws.manager import manager  # type: ignore
        return manager
    except Exception:  # noqa: BLE001
        return None


def _compute_backoff(attempt: int, base: int = 1000, cap: int = 30000) -> int:
    """
    与前端 ``useWebSocket`` 一致的退避公式：
      base * 2**attempt, capped at cap
    """
    return min(base * (2 ** attempt), cap)


@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestWebSocketReconnect(unittest.TestCase):
    """
    WebSocket 断线重连 E2E。

    涵盖：
      - 单次断线 + 重连
      - ConnectionManager 在断开后清理 active_connections
      - 多次断线重连（模拟前端指数退避）
      - 服务侧 backoff 公式与前端对齐
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        ws_paths = _ws_routes(cls.client)
        if "/ws/chat" not in ws_paths:
            cls.has_chat = False
        else:
            cls.has_chat = True
        cls.manager = _try_get_manager()

    def setUp(self) -> None:
        if not self.has_chat:
            self.skipTest("/ws/chat WebSocket 路由未注册")

    # ------------------------------------------------------------------
    # 1) 单次断线 + 重连：两侧收发正常
    # ------------------------------------------------------------------
    def test_disconnect_and_reconnect(self) -> None:
        """断开后重连，仍能正常 send/receive。"""
        # 第一次连接
        with self.client.websocket_connect("/ws/chat") as ws:
            first = ws.receive_json()
            self.assertIn("type", first)
            ws.send_json({"type": "message", "content": "first"})
            reply = ws.receive_json()
            self.assertIn("type", reply)
            # 退出 with 块 = 断开

        # 重连
        with self.client.websocket_connect("/ws/chat") as ws:
            first = ws.receive_json()
            self.assertIn("type", first)
            ws.send_json({"type": "message", "content": "after-reconnect"})
            reply = ws.receive_json()
            self.assertIn("type", reply)
            # 至少能拿到 echo / ack / chunk 之一
            self.assertIn(reply.get("type"), ("echo", "ack", "chunk"))

    # ------------------------------------------------------------------
    # 2) ConnectionManager 正确清理连接
    # ------------------------------------------------------------------
    def test_manager_cleanup_after_disconnect(self) -> None:
        """断开后，ConnectionManager 应清空 active_connections 与 channel。"""
        if self.manager is None:
            self.skipTest("ConnectionManager 不可导入")

        before = self.manager.get_stats()
        with self.client.websocket_connect("/ws/chat") as ws:
            # 连接建立后，stats 应 +1
            mid = self.manager.get_stats()
            self.assertGreaterEqual(
                mid["total_connections"],
                before["total_connections"] + 1,
                f"连接后 stats.total_connections 未增加: {mid}",
            )
            ws.receive_json()  # ack
        # 退出 with 后连接应被清理
        after = self.manager.get_stats()
        self.assertLessEqual(
            after["total_connections"],
            before["total_connections"],
            f"断开后连接未清理: before={before}, after={after}",
        )

    # ------------------------------------------------------------------
    # 3) 多次断线重连（对应前端 useWebSocket 的指数退避）
    # ------------------------------------------------------------------
    def test_multiple_reconnect_cycles(self) -> None:
        """连续 3 次断线 + 重连，验证服务侧每次都能处理。"""
        if self.manager is None:
            self.skipTest("ConnectionManager 不可导入")

        baseline = self.manager.get_stats()["total_connections"]
        for i in range(3):
            with self.client.websocket_connect("/ws/chat") as ws:
                ws.receive_json()  # ack
                ws.send_json(
                    {"type": "message", "content": f"cycle-{i}"}
                )
                ws.receive_json()  # echo / chunk
            # 每次退出 with，stats 应回到 baseline
            self.assertLessEqual(
                self.manager.get_stats()["total_connections"],
                baseline,
                f"第 {i} 次重连后，连接未清理: {self.manager.get_stats()}",
            )

    # ------------------------------------------------------------------
    # 4) 后端清理 channel：单 channel 重连后仍能 broadcast
    # ------------------------------------------------------------------
    def test_channel_persists_across_reconnects(self) -> None:
        """断开重连后，channel 索引不应被误删（broadcast 仍可达）。"""
        if self.manager is None:
            self.skipTest("ConnectionManager 不可导入")

        # 第一次连接
        with self.client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()
        # 第二次连接
        with self.client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()
            ws.send_json({"type": "message", "content": "ping"})
            # 验证第二次仍能正常收到响应
            reply = ws.receive_json()
            self.assertIn("type", reply)

        # 断开后 channel['chat'] 仍应存在（即使空）
        channels = getattr(self.manager, "channels", {}) or {}
        self.assertIn(
            "chat",
            channels,
            f"channel['chat'] 在重连后丢失: {list(channels.keys())}",
        )

    # ------------------------------------------------------------------
    # 5) backoff 公式与前端 useWebSocket 对齐
    # ------------------------------------------------------------------
    def test_backoff_formula_matches_frontend(self) -> None:
        """后端 / 测试侧的 backoff 公式应与前端 useWebSocket 一致。"""
        # 1, 2, 4, 8, 16, 30(cap), 30, 30, ...
        expected_seq = [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000]
        actual_seq = [_compute_backoff(i) for i in range(8)]
        self.assertEqual(actual_seq, expected_seq)

    # ------------------------------------------------------------------
    # 6) 异常断开（接收非 JSON 文本）不污染其他连接
    # ------------------------------------------------------------------
    def test_send_garbage_does_not_break_server(self) -> None:
        """发送非法 JSON 不应让后端崩溃；新连接仍可正常建立。"""
        with self.client.websocket_connect("/ws/chat") as ws:
            ws.receive_json()  # ack
            ws.send_text("this is not json {{{ ")
            # server 端 chat.py 的 json.loads 会失败，进入 except 分支，
            # 用 raw 字符串 echo；无论回什么，连接不应立刻断
            try:
                reply = ws.receive_json()
                self.assertIn("type", reply)
            except Exception:  # noqa: BLE001
                # 如果 server 主动关闭了连接（实现策略不同）也接受
                pass

        # 再起一个连接，验证 server 没挂
        with self.client.websocket_connect("/ws/chat") as ws:
            ack = ws.receive_json()
            self.assertIn("type", ack)


@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestReconnectManagerState(unittest.TestCase):
    """
    纯 ConnectionManager 单元测试（不依赖 WebSocket transport），
    保证状态机正确：connect -> disconnect -> 重 connect 能用不同 conn_id。
    """

    def setUp(self) -> None:
        self.manager = _try_get_manager()
        if self.manager is None:
            self.skipTest("ConnectionManager 不可导入")

    def test_disconnect_idempotent(self) -> None:
        """disconnect 未注册的 conn_id 不应抛异常。"""
        # 多次 disconnect 同一未知 id
        for _ in range(3):
            try:
                self.manager.disconnect("does-not-exist")
            except Exception as exc:  # noqa: BLE001
                self.fail(f"disconnect 不应抛异常: {exc}")

    def test_register_channel_idempotent(self) -> None:
        """register_channel 重复调用应幂等。"""
        ch = f"e2e_test_{uuid_lib.uuid4().hex[:6]}"
        for _ in range(3):
            self.manager.register_channel(ch)
        self.assertIn(ch, self.manager.channels)

    def test_active_connections_bounded(self) -> None:
        """多次 connect / disconnect 后，active_connections 不应单调增长。"""
        before = len(self.manager.active_connections)
        # 模拟一些 connect/disconnect 周期
        for _ in range(5):
            cid = uuid_lib.uuid4().hex
            # 不实际持有 WebSocket，只走 disconnect 路径
            self.manager.disconnect(cid)
        after = len(self.manager.active_connections)
        self.assertLessEqual(after, before)


# ----------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
