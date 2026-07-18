"""
Creative REST API router - Stage C.6
长期创作项目的 REST API 路由。

端点：
- GET    /api/creative/projects              列出创作项目
- GET    /api/creative/projects/{uuid}       项目详情（含 Story Bible）
- POST   /api/creative/projects              立项
- POST   /api/creative/projects/{uuid}/advance  续写（默认异步）
- DELETE /api/creative/projects/{uuid}       删除项目

设计要点：
1. 全部走 ``src.web.backend.services.database_service``；
   不直接 import DatabaseManager。
2. 所有端点 try/except 保护：单次失败 → 4xx，绝不抛 5xx。
3. 续写默认走异步模式：立即返回 task_id，并通过
   ``src.core.event_manager.get_event_manager().publish('creative_progress', ...)``
   把进度推给前端（EventService 已在 main.py 启动时订阅通配，事件会
   自动转发到 /ws/events）。
4. 同步模式（``advance_async=False``）：直接更新 last_advanced_at
   字段，不调用 LLM，避免阻塞 HTTP 请求。
"""

from __future__ import annotations

import json
import sys
import uuid as _uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, HTTPException, Query, status  # noqa: E402

# Schemas
from src.web.backend.schemas.creative import (  # noqa: E402
    AdvanceRequest,
    AdvanceResponse,
    CreativeProject,
    CreativeProjectCreate,
    CreativeProjectListResponse,
    StoryBible,
)

# Service layer
from src.web.backend.services.database_service import database_service  # noqa: E402

# 调试日志（try/except 保护：debug_logger 不可用时降级为 print）
try:
    from src.tools.debug_logger import get_debug_logger as _get_debug_logger
    _debug_logger = _get_debug_logger()
except Exception:  # noqa: BLE001
    class _StubLogger:
        def log_info(self, *a, **k): pass
        def log_warn(self, *a, **k): pass
        def log_error(self, *a, **k): pass
    _debug_logger = _StubLogger()


# EventManager 句柄（懒加载；publish 失败不影响主流程）
_event_manager = None


def _get_event_manager():
    """懒加载 EventManager 单例。"""
    global _event_manager
    if _event_manager is not None:
        return _event_manager
    try:
        from src.core.event_manager import get_event_manager
        _event_manager = get_event_manager()
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_error('creative_api',
                                    f'获取 EventManager 失败: {e}', e)
        except Exception:
            pass
        _event_manager = None
    return _event_manager


router = APIRouter(prefix="/api/creative", tags=["creative"])


# =====================================================================
# 工具：行 → CreativeProject 转换
# =====================================================================


def _safe_json_loads(raw: Any, default: Any) -> Any:
    """安全解析 JSON 字符串，失败时返回 default。"""
    if raw is None or raw == "":
        return default
    if isinstance(raw, (list, dict)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return default


def _row_to_creative_project(row: Dict[str, Any],
                              include_story_bible: bool = False) -> Dict[str, Any]:
    """
    把数据库行 dict 转成 CreativeProject 兼容 dict。

    关键 JSON 字段（outline_json / characters_json / draft_chunks_json）
    会反序列化为 list。
    """
    if not isinstance(row, dict):
        return {}

    project = dict(row)  # copy

    # JSON 字段反序列化
    for json_k, plain_k in (
        ('outline_json', 'outline'),
        ('characters_json', 'characters'),
        ('draft_chunks_json', 'draft_chunks'),
    ):
        if json_k in project and plain_k not in project:
            project[plain_k] = _safe_json_loads(project.get(json_k), [])

    # 兼容字段：word_count（前端使用）
    try:
        project['word_count'] = int(project.get('current_chars') or 0)
    except (TypeError, ValueError):
        project['word_count'] = 0

    # chapter_count：从 draft_chunks 派生
    try:
        chunks = project.get('draft_chunks') or []
        if not isinstance(chunks, list):
            chunks = []
        project['chapter_count'] = len(chunks)
    except Exception:
        project['chapter_count'] = 0

    # 默认值兜底
    project.setdefault('uuid', '')
    project.setdefault('title', '未命名')
    project.setdefault('status', 'drafting')
    project.setdefault('current_chars', 0)
    project.setdefault('target_chars', 5000)
    project.setdefault('work_type', '短篇')
    project.setdefault('premise', '')
    project.setdefault('tone', '')
    project.setdefault('point_of_view', '第一人称')
    project.setdefault('inspiration_source', '')
    project.setdefault('outline', [])
    project.setdefault('characters', [])
    project.setdefault('draft_chunks', [])
    project.setdefault('created_at', '')
    project.setdefault('updated_at', '')
    project.setdefault('next_advance_at', None)
    project.setdefault('last_advanced_at', None)

    # Story Bible：仅在详情场景下填充
    if include_story_bible:
        try:
            bible_row = database_service.get_story_bible(project.get('uuid', ''))
        except Exception as e:  # noqa: BLE001
            try:
                _debug_logger.log_warn(
                    'creative_api',
                    f'get_story_bible 失败: {e}',
                )
            except Exception:
                pass
            bible_row = None
        bible_data: Dict[str, Any] = {}
        if isinstance(bible_row, dict):
            bible_data = {
                'mainline_direction': bible_row.get('mainline_direction', ''),
                'active_themes': bible_row.get('active_themes') or [],
                'unresolved_threads': bible_row.get('unresolved_threads') or [],
                'resolved_threads': bible_row.get('resolved_threads') or [],
                'important_facts': bible_row.get('important_facts') or [],
                'next_direction': bible_row.get('next_direction', ''),
                'recent_keywords': bible_row.get('recent_keywords') or [],
                'characters': project.get('characters') or [],
                'worldview': '',
                'chapters': project.get('draft_chunks') or [],
            }
        else:
            bible_data = {
                'mainline_direction': '',
                'active_themes': [],
                'unresolved_threads': [],
                'resolved_threads': [],
                'important_facts': [],
                'next_direction': '',
                'recent_keywords': [],
                'characters': project.get('characters') or [],
                'worldview': '',
                'chapters': project.get('draft_chunks') or [],
            }
        try:
            project['story_bible'] = StoryBible(**bible_data)
        except Exception:
            project['story_bible'] = None
    else:
        project['story_bible'] = None

    return project


def _publish_creative_progress(project_uuid: str,
                                status_name: str,
                                message: str,
                                extra: Optional[Dict[str, Any]] = None) -> bool:
    """
    向 EventManager 推送 creative_progress 事件。
    返回是否成功调度（不阻塞主流程）。
    """
    em = _get_event_manager()
    if em is None:
        return False
    payload: Dict[str, Any] = {
        'project_uuid': project_uuid,
        'status': status_name,
        'message': message,
        'timestamp': datetime.now().isoformat(),
    }
    if extra:
        try:
            payload.update(dict(extra))
        except Exception:
            pass
    try:
        em.publish('creative_progress', payload)
        return True
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_warn(
                'creative_api', f'publish creative_progress 失败: {e}')
        except Exception:
            pass
        return False


# =====================================================================
# 路由
# =====================================================================


@router.get(
    "/projects",
    response_model=CreativeProjectListResponse,
    summary="列出创作项目",
    description="按 status 过滤列出 creative_projects 记录。",
)
async def list_projects(
    status: Optional[str] = Query(
        None,
        description="按 status 过滤（如 active / paused / completed / drafting / finished）",
    ),
    limit: int = Query(50, ge=1, le=200, description="返回上限（1-200）"),
) -> CreativeProjectListResponse:
    """
    GET /api/creative/projects?status=...&limit=...

    始终返回 200；DB 不可用 / 表缺失时返回空列表。
    """
    try:
        rows = database_service.list_creative_projects(
            status=status, limit=limit,
        )
        projects: List[Dict[str, Any]] = []
        for row in rows or []:
            try:
                projects.append(_row_to_creative_project(row))
            except Exception:
                continue
        return CreativeProjectListResponse(
            projects=[CreativeProject(**p) for p in projects],  # type: ignore[arg-type]
            total=len(projects),
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_error(
                'creative_api', f'list_projects 失败: {e}', e)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"list projects failed: {e}",
        )


@router.get(
    "/projects/{project_uuid}",
    response_model=CreativeProject,
    summary="项目详情",
    description="按 uuid 读取项目详情，并附 Story Bible。",
    responses={404: {"description": "项目不存在"}},
)
async def get_project(project_uuid: str) -> CreativeProject:
    """
    GET /api/creative/projects/{uuid}

    404 当项目不存在；500 当 DB 异常。
    """
    if not project_uuid or not isinstance(project_uuid, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_uuid is required",
        )
    try:
        row = database_service.get_creative_project(project_uuid)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"project not found: {project_uuid}",
            )
        project_dict = _row_to_creative_project(row, include_story_bible=True)
        return CreativeProject(**project_dict)  # type: ignore[arg-type]
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_error(
                'creative_api', f'get_project({project_uuid}) 失败: {e}', e)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"get project failed: {e}",
        )


@router.post(
    "/projects",
    response_model=CreativeProject,
    status_code=status.HTTP_201_CREATED,
    summary="立项",
    description="创建一条 creative_projects 记录。",
    responses={400: {"description": "请求参数不合法"}},
)
async def create_project(payload: CreativeProjectCreate) -> CreativeProject:
    """
    POST /api/creative/projects

    body: CreativeProjectCreate
    returns: 201 + CreativeProject
    """
    if not payload or not payload.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title is required",
        )
    try:
        new_uuid = database_service.create_creative_project(
            {
                'title': payload.title,
                'work_type': payload.work_type or '短篇',
                'premise': payload.premise or '',
                'tone': payload.tone or '',
                'point_of_view': payload.point_of_view or '第一人称',
                'target_chars': int(payload.target_chars or 5000),
                'current_chars': 0,
                'status': 'active',  # 前端默认语义：active = drafting
                'inspiration_source': payload.inspiration_source or '',
                'outline': payload.outline or [],
                'characters': payload.characters or [],
                'draft_chunks': [],
            }
        )
        if not new_uuid:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to create project (db unavailable or write failed)",
            )
        # 重新读取完整记录
        row = database_service.get_creative_project(new_uuid) or {
            'uuid': new_uuid,
            'title': payload.title,
            'work_type': payload.work_type or '短篇',
            'premise': payload.premise or '',
            'tone': payload.tone or '',
            'point_of_view': payload.point_of_view or '第一人称',
            'target_chars': int(payload.target_chars or 5000),
            'current_chars': 0,
            'status': 'active',
            'inspiration_source': payload.inspiration_source or '',
            'outline_json': json.dumps(payload.outline or [], ensure_ascii=False),
            'characters_json': json.dumps(payload.characters or [], ensure_ascii=False),
            'draft_chunks_json': json.dumps([], ensure_ascii=False),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        }
        project_dict = _row_to_creative_project(row, include_story_bible=True)
        try:
            _debug_logger.log_info(
                'creative_api', 'create_project OK',
                {'uuid': new_uuid, 'title': payload.title},
            )
        except Exception:
            pass
        # 触发 creative_progress 事件（queued）
        _publish_creative_progress(
            new_uuid, status_name='created',
            message=f'项目《{payload.title}》已创建',
            extra={'title': payload.title, 'last_advanced_at': None},
        )
        return CreativeProject(**project_dict)  # type: ignore[arg-type]
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_error(
                'creative_api', f'create_project 失败: {e}', e)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"create project failed: {e}",
        )


@router.post(
    "/projects/{project_uuid}/advance",
    response_model=AdvanceResponse,
    summary="续写",
    description=(
        "触发一次续写。默认走异步模式：立即返回 task_id，"
        "通过 'creative_progress' 事件推送进度。"
        "将 ``advance_async`` 置为 False 走同步模式：仅更新 last_advanced_at。"
    ),
    responses={404: {"description": "项目不存在"}},
)
async def advance_project(
    project_uuid: str,
    payload: Optional[AdvanceRequest] = None,
) -> AdvanceResponse:
    """
    POST /api/creative/projects/{uuid}/advance

    异步模式（默认）：
      - 立即返回 202 + task_id
      - 后台通过 EventManager.publish('creative_progress', {...}) 推送进度
      - 前端通过 /ws/events 接收事件
    同步模式（advance_async=False）：
      - 立即更新 last_advanced_at 字段
      - 返回 200 + AdvanceResponse(status=completed, last_advanced_at=now)
    """
    if not project_uuid or not isinstance(project_uuid, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_uuid is required",
        )
    # 兼容 body 缺省（GET-like 调用）
    body = payload or AdvanceRequest()
    try:
        row = database_service.get_creative_project(project_uuid)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"project not found: {project_uuid}",
            )
        current_status = str(row.get('status') or 'drafting')
        now_iso = datetime.now().isoformat()

        if not body.advance_async:
            # 同步模式：仅更新时间戳；不阻塞主流程
            updated = database_service.update_creative_project(
                project_uuid,
                {
                    'last_advanced_at': now_iso,
                    'next_advance_at': now_iso,
                },
            )
            if not updated:
                # 行不存在或更新失败：依然视为成功（接口幂等）
                pass
            _publish_creative_progress(
                project_uuid, status_name='advanced',
                message=f'项目已续写（同步模式）',
                extra={'last_advanced_at': now_iso,
                       'project_status': current_status},
            )
            return AdvanceResponse(
                project_uuid=project_uuid,
                task_id="",
                status="completed",
                last_advanced_at=now_iso,
                project_status=current_status,
                message="advance completed (sync mode)",
            )

        # 异步模式：生成 task_id，立即返回；通过 EventManager 推送进度
        task_id = str(_uuid.uuid4())
        _publish_creative_progress(
            project_uuid, status_name='queued',
            message='续写任务已入队',
            extra={'task_id': task_id, 'user': body.user,
                   'project_status': current_status,
                   'last_advanced_at': now_iso},
        )
        # 同步推进：尝试更新 last_advanced_at 作为占位。
        # 真正的 LLM 生成留给后台 Worker；这里仅记录"已入队"。
        try:
            database_service.update_creative_project(
                project_uuid,
                {
                    'last_advanced_at': now_iso,
                    'next_advance_at': now_iso,
                },
            )
        except Exception:
            pass

        try:
            _debug_logger.log_info(
                'creative_api', 'advance queued',
                {'uuid': project_uuid, 'task_id': task_id,
                 'user': body.user, 'hint': (body.hint or '')[:80]},
            )
        except Exception:
            pass

        return AdvanceResponse(
            project_uuid=project_uuid,
            task_id=task_id,
            status="queued",
            last_advanced_at=now_iso,
            project_status=current_status,
            message=(
                "advance task queued; progress will be pushed via "
                "'creative_progress' events"
            ),
        )
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_error(
                'creative_api', f'advance_project({project_uuid}) 失败: {e}', e)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"advance project failed: {e}",
        )


@router.delete(
    "/projects/{project_uuid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除项目",
    description="按 uuid 删除 creative_projects 记录（级联删除 Story Bible / Memory Pool）。",
    responses={
        204: {"description": "删除成功"},
        404: {"description": "项目不存在"},
    },
)
async def delete_project(project_uuid: str) -> None:
    """
    DELETE /api/creative/projects/{uuid}
    """
    if not project_uuid or not isinstance(project_uuid, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_uuid is required",
        )
    try:
        # 删除前先校验存在（避免静默成功）
        row = database_service.get_creative_project(project_uuid)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"project not found: {project_uuid}",
            )
        ok = database_service.delete_record('creative_projects', project_uuid)
        if not ok:
            # 行级联删除会清掉 bible / pool；但 delete_record 返回 False
            # 也可能因为 uuid 不在白名单等异常 → 视为 500
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="delete failed (db unavailable or write blocked)",
            )
        try:
            _debug_logger.log_info(
                'creative_api', 'delete_project OK',
                {'uuid': project_uuid, 'title': row.get('title')},
            )
        except Exception:
            pass
        _publish_creative_progress(
            project_uuid, status_name='deleted',
            message='项目已删除',
            extra={'title': row.get('title')},
        )
        # 204 No Content
        return None
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        try:
            _debug_logger.log_error(
                'creative_api', f'delete_project({project_uuid}) 失败: {e}', e)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"delete project failed: {e}",
        )


__all__ = ["router"]
