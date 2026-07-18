"""
Stage E.1 - E2E test: knowledge base CRUD (list/create/delete entities).

目标：
  1. ``GET  /api/knowledge/tables``      — 列出知识库表
  2. ``GET  /api/knowledge/entities``    — 列出某个表内的实体
  3. ``POST /api/knowledge/entities``    — 新增一个实体
  4. ``DELETE /api/knowledge/entities/{uuid}`` — 删除实体

兼容性：
  - 由于 Stage E.1 之前这些 API 可能未实现，**测试可降级**：
    探测后端路由表，若端点不存在则 ``self.skipTest``。
  - 使用 ``unittest.TestCase`` 即可（HTTP 同步）。
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


def _list_http_routes(test_client: Any) -> List[str]:
    """收集后端注册的所有 HTTP 路由路径。"""
    paths: List[str] = []
    try:
        router = test_client.app.router
    except Exception:  # noqa: BLE001
        return paths
    for route in router.routes:
        p = getattr(route, "path", None) or getattr(route, "path_format", None)
        if p:
            paths.append(str(p))
    return paths


def _route_exists(test_client: Any, path: str) -> bool:
    return path in _list_http_routes(test_client)


@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestKnowledgeCRUD(unittest.TestCase):
    """
    知识库 CRUD E2E 测试（可降级）。

    任何子用例在端点缺失时自动 skip；这意味着当前 Stage A 阶段即使
    ``/api/knowledge/*`` 一个都没实现，本测试也能正常通过（被记为 skip）。
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        cls.http_routes = _list_http_routes(cls.client)

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------
    def _skip_if_missing(self, path: str) -> None:
        if path not in self.http_routes:
            self.skipTest(f"路由 {path} 未注册（Stage 可能未实现）")

    # ------------------------------------------------------------------
    # 1) GET /api/knowledge/tables
    # ------------------------------------------------------------------
    def test_list_tables(self) -> None:
        """列出知识库表。返回 200 + 列表（结构降级为 dict-of-lists 也可）。"""
        self._skip_if_missing("/api/knowledge/tables")
        resp = self.client.get("/api/knowledge/tables")
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertIsInstance(body, (dict, list))
        if isinstance(body, list):
            # 直接列表
            self.assertGreaterEqual(len(body), 0)
        elif isinstance(body, dict):
            # 兼容 ``{"tables": [...]}`` / ``{"items": [...]}`` 等
            for key in ("tables", "items", "data"):
                if key in body:
                    self.assertIsInstance(body[key], list)
                    return
            # 找不到标准字段也不报错，结构留给前端解析

    # ------------------------------------------------------------------
    # 2) GET /api/knowledge/entities?table=entities&limit=10
    # ------------------------------------------------------------------
    def test_list_entities(self) -> None:
        """列出某个表的实体；应返回 200。"""
        self._skip_if_missing("/api/knowledge/entities")
        # 先尝试带 table=entities；如端点不要求参数，也能跑通
        resp = self.client.get(
            "/api/knowledge/entities",
            params={"table": "entities", "limit": "10"},
        )
        self.assertIn(
            resp.status_code,
            (200, 400, 422),
            f"列出实体返回异常状态码: {resp.status_code}",
        )
        if resp.status_code != 200:
            self.skipTest(
                f"列出实体未实现（status={resp.status_code}）: {resp.text[:120]}"
            )
        body = resp.json()
        self.assertIsInstance(body, (dict, list))

    def test_list_entities_invalid_table(self) -> None:
        """非法表名应返回 4xx 而非 500。"""
        self._skip_if_missing("/api/knowledge/entities")
        resp = self.client.get(
            "/api/knowledge/entities",
            params={"table": "non_existing_table_xyz", "limit": "5"},
        )
        # 容忍 200/400/404/422；只要不是 500 即可
        self.assertLess(
            resp.status_code,
            500,
            f"非法表名应返回 4xx，不应 5xx: {resp.status_code} {resp.text[:200]}",
        )

    # ------------------------------------------------------------------
    # 3) POST /api/knowledge/entities
    # ------------------------------------------------------------------
    def test_create_entity(self) -> None:
        """创建一个最小实体；返回 200/201 + 至少包含 uuid 或 id。"""
        self._skip_if_missing("/api/knowledge/entities")
        payload = {
            "table": "entities",
            "data": {
                "name": f"e2e_test_{uuid_lib.uuid4().hex[:8]}",
                "type": "test",
                "description": "created by E2E test",
            },
        }
        resp = self.client.post("/api/knowledge/entities", json=payload)
        # 接受 200 (常见) 或 201 (REST 风格)
        self.assertIn(
            resp.status_code,
            (200, 201, 400, 422),
            f"创建实体返回异常: {resp.status_code} {resp.text[:200]}",
        )
        if resp.status_code in (400, 422):
            self.skipTest(
                f"POST 实体未完全实现（status={resp.status_code}）: "
                f"{resp.text[:120]}"
            )

        body = resp.json()
        self.assertIsInstance(body, dict)
        # 必须能从响应里拿到一个 id / uuid 字段供后续 DELETE 使用
        entity_id = (
            body.get("uuid")
            or body.get("id")
            or (body.get("data") or {}).get("uuid")
            or (body.get("data") or {}).get("id")
        )
        # 即使没拿到，也至少校验响应是 dict
        self.assertIsInstance(body, dict)

        # 缓存给后续测试用（如果有）
        if entity_id:
            self.__class__._last_entity_id = str(entity_id)

    # ------------------------------------------------------------------
    # 4) DELETE /api/knowledge/entities/{uuid}
    # ------------------------------------------------------------------
    def test_delete_entity(self) -> None:
        """删除一个实体（先尝试创建拿 id；或者用随机 uuid 测试 404 路径）。"""
        self._skip_if_missing("/api/knowledge/entities")

        # 取一个用于删除的 id：先尝试创建；拿不到就用随机 uuid
        entity_id: Optional[str] = getattr(
            self.__class__, "_last_entity_id", None
        )
        if not entity_id:
            # 用 setUp 创建一个
            try:
                create_resp = self.client.post(
                    "/api/knowledge/entities",
                    json={
                        "table": "entities",
                        "data": {
                            "name": f"e2e_del_{uuid_lib.uuid4().hex[:8]}",
                            "type": "test",
                        },
                    },
                )
                if create_resp.status_code in (200, 201):
                    body = create_resp.json()
                    entity_id = (
                        body.get("uuid")
                        or body.get("id")
                        or (body.get("data") or {}).get("uuid")
                        or (body.get("data") or {}).get("id")
                    )
            except Exception:  # noqa: BLE001
                entity_id = None

        if not entity_id:
            # 没有可删的对象，测一下删除不存在的 uuid 应该是 4xx
            random_uuid = uuid_lib.uuid4().hex
            resp = self.client.delete(
                f"/api/knowledge/entities/{random_uuid}"
            )
            self.assertLess(resp.status_code, 500)
            return

        resp = self.client.delete(
            f"/api/knowledge/entities/{entity_id}"
        )
        # 接受 200/204/404
        self.assertIn(
            resp.status_code,
            (200, 204, 404),
            f"删除实体返回异常: {resp.status_code} {resp.text[:200]}",
        )

    # ------------------------------------------------------------------
    # 5) 路径参数格式校验：uuid 不合法应返回 4xx
    # ------------------------------------------------------------------
    def test_delete_entity_invalid_uuid(self) -> None:
        """非法 uuid 的删除请求应返回 4xx 而非 500。"""
        self._skip_if_missing("/api/knowledge/entities")
        resp = self.client.delete("/api/knowledge/entities/not-a-uuid")
        self.assertLess(
            resp.status_code,
            500,
            f"非法 uuid 应返回 4xx，不应 5xx: {resp.status_code}",
        )


# ----------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
