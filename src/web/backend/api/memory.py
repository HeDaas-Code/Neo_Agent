"""
Memory API router
话题时间线后端路由 - Stage B.4

提供两个端点（合并到本文件，按 spec 可选拆分为 memory_context.py）：

- ``GET /api/memory/timeline?days=7``
    从 ``open_loops`` 表查询最近 N 天的未完话题，构造
    ``TimelineResponse({nodes, links, days, total})``。
- ``GET /api/memory/loop/{uuid}/context``
    根据 open_loops.uuid 返回相关对话上下文（来自 ``short_term_memory``
    关联消息 / open_loop 的 context 字段）。

设计要点：
1. 数据源用 ``database_service`` 单例（白名单防御 + 失败降级空 list）。
2. 所有 SQL 路径 ``try/except`` 保护，失败返回空响应。
3. ``days`` / ``limit`` 边界保护，避免外部参数异常拖死 DB。
4. 不修改 LongTermMemoryManager / DatabaseManager 既有签名。
5. ``app.include_router(memory.router)`` 由 main.py 完成。
"""

from __future__ import annotations

import json
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path as PathLib  # noqa: F401  # 重命名避免与 fastapi.Path 冲突
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, status

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = PathLib(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.web.backend.schemas.memory import (  # noqa: E402
    LoopContextItem,
    LoopContextResponse,
    TimelineLink,
    TimelineNode,
    TimelineResponse,
)
from src.web.backend.services.database_service import (  # noqa: E402
    database_service,
)


router = APIRouter(prefix="/api/memory", tags=["memory"])


# ----------------------------------------------------------------------
# 内部：日期 / 边界保护
# ----------------------------------------------------------------------
_MIN_DAYS = 1
_MAX_DAYS = 365
_DEFAULT_DAYS = 7
_DEFAULT_LIMIT = 200
_MAX_LIMIT = 1000


def _coerce_days(raw: Any) -> int:
    """把 Query 传入的 days 规整到 [1, 365]，失败回退 7。"""
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_DAYS
    if v < _MIN_DAYS:
        return _MIN_DAYS
    if v > _MAX_DAYS:
        return _MAX_DAYS
    return v


def _coerce_limit(raw: Any) -> int:
    """把 limit 规整到 [1, 1000]，失败回退 200。"""
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    if v < 1:
        return 1
    if v > _MAX_LIMIT:
        return _MAX_LIMIT
    return v


def _iso_to_date(iso: Optional[str]) -> str:
    """把 ISO 8601 字符串截成 YYYY-MM-DD；失败返回空串。"""
    if not iso or not isinstance(iso, str):
        return ""
    s = iso.strip()
    if len(s) >= 10 and s[4:5] == "-" and s[7:8] == "-":
        return s[:10]
    return ""


def _parse_keywords(raw: Any) -> List[str]:
    """
    把 ``related_keywords_json`` / list / str 规整为 List[str]。
    失败时返回 []。
    """
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw if x]
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return []
        # 尝试 json.loads（库内以 json 形式存储）
        if s.startswith("[") or s.startswith("{"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed if x]
            except Exception:  # noqa: BLE001
                pass
        # 退化：逗号 / 空格切分
        parts = [p.strip() for p in s.replace(",", " ").split() if p.strip()]
        return parts
    return []


def _normalize_status(raw: Any) -> str:
    """
    把 open_loops.status 规整为 ``open`` / ``closed`` 之一。
    数据库里常用 'open' / 'resolved' / 'closed'。前端 TimelineCanvas
    看到 'open'/'closed' 即可按需上色。
    """
    s = str(raw or "").strip().lower()
    if not s:
        return "open"
    if s in ("resolved", "closed", "done", "finished"):
        return "closed"
    if s in ("open", "pending", "active"):
        return "open"
    return s


def _normalize_node(row: Dict[str, Any]) -> Optional[TimelineNode]:
    """
    把 open_loops 的一行 dict 转换为 TimelineNode。
    字段缺失 / 解析失败 → 返回 None（让上层跳过）。
    """
    try:
        uuid_val = str(row.get("uuid") or "").strip()
        if not uuid_val:
            return None
        topic_val = str(row.get("topic") or "未命名话题")
        date_val = _iso_to_date(row.get("raised_at") or row.get("created_at"))
        if not date_val:
            # 兜底：取 created_at 或今天
            date_val = _iso_to_date(row.get("created_at")) or datetime.now().strftime("%Y-%m-%d")
        status_val = _normalize_status(row.get("status"))
        try:
            mention_count = int(row.get("mention_count") or 0)
        except (TypeError, ValueError):
            mention_count = 0
        keywords = _parse_keywords(row.get("related_keywords_json") or row.get("related_keywords"))
        return TimelineNode(
            uuid=uuid_val,
            topic=topic_val,
            date=date_val,
            status=status_val,
            category="其他",
            mention_count=mention_count,
            keywords=keywords,
        )
    except Exception:  # noqa: BLE001
        return None


# ----------------------------------------------------------------------
# 1) GET /api/memory/timeline?days=7
# ----------------------------------------------------------------------
@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    days: int = Query(
        _DEFAULT_DAYS,
        ge=_MIN_DAYS,
        le=_MAX_DAYS,
        description="查询最近 N 天的未完话题（默认 7，最大 365）",
    ),
    limit: int = Query(
        _DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description="返回节点数上限（默认 200，最大 1000）",
    ),
) -> TimelineResponse:
    """
    话题时间线后端。

    响应：``TimelineResponse({nodes, links, days, total})``
        - ``nodes`` 每个节点来自 ``open_loops`` 一行；
        - ``links`` 由共享 related_keywords 推导（>= 2 个节点共享至少一个关键词时建链）。

    失败降级：DB 不可用 / 表不存在 / 解析失败 → 返回 ``{nodes:[], links:[]}``。
    """
    safe_days = _coerce_days(days)
    safe_limit = _coerce_limit(limit)

    # 截止时间
    try:
        cutoff_iso = (datetime.now() - timedelta(days=safe_days)).isoformat()
    except Exception:  # noqa: BLE001
        cutoff_iso = datetime.now().isoformat()

    # 1) 拉 open_loops
    raw_rows: List[Dict[str, Any]] = []
    try:
        raw_rows = database_service.query_table("open_loops", limit=safe_limit, offset=0) or []
    except ValueError as exc:
        # 理论上不会发生（白名单内），但万一也兜底
        try:
            warnings.warn(
                f"[memory] query_table('open_loops') 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        except Exception:
            pass
        raw_rows = []
    except Exception as exc:  # noqa: BLE001
        try:
            warnings.warn(
                f"[memory] query_table('open_loops') 异常: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
        except Exception:
            pass
        raw_rows = []

    # 2) 规整为节点 + 时间过滤
    nodes: List[TimelineNode] = []
    for row in raw_rows:
        node = _normalize_node(row)
        if node is None:
            continue
        # 时间窗口过滤：raised_at < cutoff 则丢弃
        try:
            raised_iso = str(row.get("raised_at") or row.get("created_at") or "")
            if raised_iso and raised_iso < cutoff_iso:
                continue
        except Exception:
            pass
        nodes.append(node)

    # 3) 构造 links：共享至少一个 keyword 的两个节点建链
    links: List[TimelineLink] = []
    try:
        n = len(nodes)
        kw_index: Dict[str, List[str]] = {}
        for nd in nodes:
            for kw in nd.keywords:
                if not kw:
                    continue
                kw_index.setdefault(kw, []).append(nd.uuid)
        seen: set = set()
        for kw, uuids in kw_index.items():
            if len(uuids) < 2:
                continue
            for i in range(len(uuids)):
                for j in range(i + 1, len(uuids)):
                    a, b = uuids[i], uuids[j]
                    key = (a, b) if a < b else (b, a)
                    if key in seen:
                        continue
                    seen.add(key)
                    links.append(TimelineLink(source=key[0], target=key[1], relation="keyword"))
    except Exception:  # noqa: BLE001
        links = []

    return TimelineResponse(
        nodes=nodes,
        links=links,
        days=safe_days,
        total=len(nodes),
    )


# ----------------------------------------------------------------------
# 2) GET /api/memory/loop/{uuid}/context
# ----------------------------------------------------------------------
def _query_short_term_by_keywords(
    keywords: List[str],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    辅助：在 short_term_memory 中按关键词粗匹配（LIKE）。
    注意：这是简单实现，不做 join / ranking。
    失败 → []。
    """
    if not keywords:
        return []
    db = database_service.get_db()
    if db is None:
        return []
    safe_limit = _coerce_limit(limit)
    rows: List[Dict[str, Any]] = []
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            for kw in keywords:
                if not kw:
                    continue
                pattern = f"%{kw}%"
                try:
                    cur.execute(
                        "SELECT id, role, content, timestamp FROM short_term_memory "
                        "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                        (pattern, safe_limit),
                    )
                except Exception:
                    continue
                fetched = cur.fetchall() or []
                for r in fetched:
                    try:
                        if isinstance(r, dict):
                            rows.append(dict(r))
                        else:
                            rows.append({k: r[k] for k in r.keys()})
                    except Exception:
                        try:
                            rows.append(dict(r))
                        except Exception:
                            continue
    except Exception:  # noqa: BLE001
        return []
    # 去重（按 id）
    dedup: Dict[Any, Dict[str, Any]] = {}
    for r in rows:
        rid = r.get("id")
        if rid is None:
            continue
        if rid not in dedup:
            dedup[rid] = r
    merged = list(dedup.values())
    try:
        merged.sort(key=lambda x: x.get("id") or 0, reverse=True)
    except Exception:
        pass
    return merged[:safe_limit]


def _find_open_loop_by_uuid(uuid_val: str) -> Optional[Dict[str, Any]]:
    """
    在 open_loops 中按 uuid 查找一行。
    找不到 / 失败 → None。
    """
    if not uuid_val or not isinstance(uuid_val, str):
        return None
    db = database_service.get_db()
    if db is None:
        return None
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT uuid, topic, status, raised_at, resolved_at, "
                    "related_keywords_json, context, mention_count, "
                    "created_at, updated_at "
                    "FROM open_loops WHERE uuid = ?",
                    (uuid_val,),
                )
            except Exception:
                # 兜底：SELECT *
                cur.execute(
                    "SELECT * FROM open_loops WHERE uuid = ?",
                    (uuid_val,),
                )
            row = cur.fetchone()
            if row is None:
                return None
            try:
                if isinstance(row, dict):
                    return dict(row)
                return {k: row[k] for k in row.keys()}
            except Exception:
                try:
                    return dict(row)
                except Exception:
                    return None
    except Exception:  # noqa: BLE001
        return None


@router.get("/loop/{uuid}/context", response_model=LoopContextResponse)
async def get_loop_context(
    uuid: str = Path(..., min_length=1, description="话题 UUID（open_loops.uuid）"),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="返回的上下文消息条数上限（默认 50）",
    ),
) -> LoopContextResponse:
    """
    话题上下文（按 open_loops.uuid 关联 short_term_memory）。

    响应：``LoopContextResponse({uuid, topic, status, items, total})``。
    失败 / 未找到 → items=[]。
    """
    safe_uuid = (uuid or "").strip()
    if not safe_uuid:
        # 空 uuid 视为 4xx 输入
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="uuid 不能为空",
        )

    safe_limit = _coerce_limit(limit)
    if safe_limit > 200:
        safe_limit = 200

    # 1) 找 open_loop
    loop_row: Optional[Dict[str, Any]] = None
    try:
        loop_row = _find_open_loop_by_uuid(safe_uuid)
    except Exception:  # noqa: BLE001
        loop_row = None

    if loop_row is None:
        # 未找到（也可能 DB 不可用） → 返回空上下文
        return LoopContextResponse(uuid=safe_uuid, items=[], total=0)

    topic_text = str(loop_row.get("topic") or "")
    status_text = _normalize_status(loop_row.get("status"))
    keywords = _parse_keywords(
        loop_row.get("related_keywords_json") or loop_row.get("related_keywords")
    )

    items: List[LoopContextItem] = []

    # 2) 先放 open_loop.context（兜底 / 锚点）
    fallback_context = str(loop_row.get("context") or "").strip()
    if fallback_context:
        items.append(
            LoopContextItem(
                role="system",
                content=fallback_context,
                timestamp=_iso_to_date(loop_row.get("raised_at")) or None,
                source="open_loop_context",
            )
        )

    # 3) 再按关键词找 short_term_memory 关联消息
    if keywords:
        try:
            matched = _query_short_term_by_keywords(keywords, limit=safe_limit) or []
        except Exception:  # noqa: BLE001
            matched = []
        for m in matched:
            try:
                items.append(
                    LoopContextItem(
                        role=str(m.get("role") or "user"),
                        content=str(m.get("content") or ""),
                        timestamp=(str(m.get("timestamp")) if m.get("timestamp") else None),
                        source="short_term_memory",
                    )
                )
            except Exception:  # noqa: BLE001
                continue

    # 4) 截断
    if len(items) > safe_limit:
        items = items[:safe_limit]

    return LoopContextResponse(
        uuid=safe_uuid,
        topic=topic_text,
        status=status_text,
        items=items,
        total=len(items),
    )


__all__ = ["router"]
