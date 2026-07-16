"""
Schedule REST API Router
- /api/schedule/ (GET): 按日期查询日程
- /api/schedule/ (POST): 新建日程
- /api/schedule/{schedule_id} (PUT): 更新日程
- /api/schedule/{schedule_id} (DELETE): 删除日程
- /api/schedule/{schedule_id}/confirm (POST): 协作日程确认（双方确认后才生效）

Stage C.2:
- 复用 database_service 提供的 schedule_* 表查询/写入接口
- 失败路径：HTTPException(status_code=4xx)，不抛 5xx
- 协作确认：调用 database_service.confirm_schedule_item
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.web.backend.services.database_service import database_service
    from src.web.backend.schemas.schedule import (
        ScheduleCreate,
        ScheduleUpdate,
    )
except Exception as exc:  # noqa: BLE001
    database_service = None  # type: ignore
    _IMPORT_ERROR = exc


# 协作确认请求体（Stage C.2 扩展）
class ScheduleConfirmRequest(BaseModel):
    user_id: str = "default"
    note: Optional[str] = None


# ----------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------
def _row_to_dto(row: Dict[str, Any]) -> Dict[str, Any]:
    """把数据库行映射为前端 ScheduleDTO 兼容结构。"""
    if not isinstance(row, dict):
        try:
            row = dict(row)
        except Exception:
            return {}
    return {
        "id": row.get("id"),
        "uuid": str(row.get("id") or row.get("uuid") or ""),
        "title": str(row.get("title") or ""),
        "description": row.get("description"),
        "start_time": str(row.get("start_time") or ""),
        "end_time": row.get("end_time"),
        "priority": str(row.get("priority") or "normal"),
        "status": str(row.get("status") or "pending"),
        "schedule_type": str(row.get("schedule_type") or "personal"),
    }


def _parse_iso_date(value: Optional[str], field: str) -> str:
    """YYYY-MM-DD 校验（失败 400）。"""
    import re
    if not value or not isinstance(value, str):
        raise HTTPException(status_code=400, detail=f"{field} 必填")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        raise HTTPException(
            status_code=400,
            detail=f"{field} 格式必须为 YYYY-MM-DD, 收到: {value!r}",
        )
    return value


# ----------------------------------------------------------------------
# 路由
# ----------------------------------------------------------------------
router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("")
async def list_schedule(
    date: Optional[str] = Query(
        default=None,
        description="单日查询 YYYY-MM-DD",
    ),
    from_date: Optional[str] = Query(
        default=None,
        alias="from",
        description="区间起始 YYYY-MM-DD（与 to 一起使用）",
    ),
    to_date: Optional[str] = Query(
        default=None,
        alias="to",
        description="区间结束 YYYY-MM-DD（与 from 一起使用）",
    ),
    user_id: str = Query(default="default"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """
    按日期查询日程。
    - 兼容 date=YYYY-MM-DD 单日查询
    - 兼容 from / to 区间查询
    - 失败路径：返回空列表（表不存在时也不抛 5xx）
    """
    if database_service is None:
        return {"items": [], "total": 0, "date": date, "range": None}

    try:
        if date:
            _parse_iso_date(date, "date")
            rows = database_service.get_schedule_by_date(date) or []
            return {
                "items": [_row_to_dto(r) for r in rows[:limit]],
                "total": min(len(rows), limit),
                "date": date,
                "range": None,
            }

        if from_date or to_date:
            if not (from_date and to_date):
                raise HTTPException(
                    status_code=400,
                    detail="from 与 to 必须成对出现",
                )
            _parse_iso_date(from_date, "from")
            _parse_iso_date(to_date, "to")
            if from_date > to_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"from ({from_date}) 不能晚于 to ({to_date})",
                )
            rows = database_service.get_schedule_by_range(from_date, to_date) or []
            return {
                "items": [_row_to_dto(r) for r in rows[:limit]],
                "total": min(len(rows), limit),
                "date": None,
                "range": {"from": from_date, "to": to_date},
            }

        # 未指定过滤：直接读 schedules 表前 limit 条
        try:
            tables = database_service.get_tables() or []
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"DatabaseService 不可用: {exc}") from exc
        if "schedules" not in tables and "schedule_entries" not in tables:
            return {
                "items": [],
                "total": 0,
                "date": None,
                "range": None,
                "warning": "schedule_* 表未在数据库中创建, 当前返回空列表",
            }
        table = "schedules" if "schedules" in tables else "schedule_entries"
        rows = database_service.query_table(table, limit=limit, offset=0) or []
        return {
            "items": [_row_to_dto(r) for r in rows],
            "total": len(rows),
            "date": None,
            "range": None,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        warnings.warn(
            f"[schedule_api] list_schedule 失败: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return {"items": [], "total": 0, "date": date, "range": None, "error": str(exc)}


@router.post("")
async def create_schedule(payload: ScheduleCreate) -> dict:
    """
    新建日程。
    - 复用 database_service.add_schedule_item 走白名单 INSERT 路径
    - 失败路径：400/503（不抛 5xx）
    """
    if database_service is None:
        raise HTTPException(status_code=503, detail="database_service 不可用")

    # 校验：表是否存在
    try:
        tables = database_service.get_tables() or []
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"DatabaseService 不可用: {exc}") from exc
    if "schedules" not in tables and "schedule_entries" not in tables:
        raise HTTPException(
            status_code=400,
            detail="schedule_* 表未在数据库中创建, 无法新增日程",
        )

    item: Dict[str, Any] = {
        "title": payload.title,
        "description": payload.description,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "priority": payload.priority or "normal",
        "status": "pending",
        "schedule_type": payload.schedule_type or "personal",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    try:
        new_id = database_service.add_schedule_item(item)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"新增日程失败: {exc}") from exc
    if not new_id:
        raise HTTPException(status_code=400, detail="新增日程失败: 数据库写入异常")

    return {
        "id": int(new_id),
        "uuid": str(new_id),
        "item": _row_to_dto({**item, "id": int(new_id)}),
        "message": "ok",
    }


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: int, payload: ScheduleUpdate) -> dict:
    """
    更新日程（部分字段）。
    - 复用 database_service.update_schedule_item
    """
    if database_service is None:
        raise HTTPException(status_code=503, detail="database_service 不可用")

    if schedule_id <= 0:
        raise HTTPException(status_code=400, detail="schedule_id 必须为正整数")

    if payload.id and payload.id != schedule_id:
        raise HTTPException(
            status_code=400,
            detail=f"URL id ({schedule_id}) 与 body.id ({payload.id}) 不一致",
        )

    updates: Dict[str, Any] = {}
    for field in (
        "title", "description", "start_time", "end_time",
        "priority", "status",
    ):
        value = getattr(payload, field, None)
        if value is not None:
            updates[field] = value
    if not updates:
        raise HTTPException(status_code=400, detail="没有可更新的字段")
    updates["updated_at"] = datetime.now().isoformat()

    try:
        ok = database_service.update_schedule_item(schedule_id, updates)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"更新失败: {exc}") from exc
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 id={schedule_id} 的日程, 或写入失败",
        )

    return {
        "id": schedule_id,
        "updated_fields": list(updates.keys()),
        "message": "ok",
    }


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: int) -> dict:
    """
    删除日程。
    """
    if database_service is None:
        raise HTTPException(status_code=503, detail="database_service 不可用")

    if schedule_id <= 0:
        raise HTTPException(status_code=400, detail="schedule_id 必须为正整数")

    try:
        ok = database_service.delete_schedule_item(schedule_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"删除失败: {exc}") from exc
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 id={schedule_id} 的日程, 或删除失败",
        )

    return {
        "id": schedule_id,
        "deleted": True,
        "message": "ok",
    }


@router.post("/{schedule_id}/confirm")
async def confirm_schedule(
    schedule_id: int,
    confirmed: bool = Query(default=True, description="true=确认, false=取消确认"),
    payload: Optional[ScheduleConfirmRequest] = None,
) -> dict:
    """
    协作日程确认（双方确认后才生效）。
    - 复用 database_service.confirm_schedule_item 写入 confirmed 字段
    - 失败路径：404/400（不抛 5xx）
    """
    if database_service is None:
        raise HTTPException(status_code=503, detail="database_service 不可用")

    if schedule_id <= 0:
        raise HTTPException(status_code=400, detail="schedule_id 必须为正整数")

    try:
        ok = database_service.confirm_schedule_item(schedule_id, bool(confirmed))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"确认失败: {exc}") from exc
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 id={schedule_id} 的日程, 或更新失败",
        )

    return {
        "id": schedule_id,
        "confirmed": bool(confirmed),
        "status": "confirmed" if confirmed else "pending",
        "message": "ok",
    }


__all__ = ["router"]
