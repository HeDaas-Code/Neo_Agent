"""
Creative service module.
长期创作项目服务模块 - 包装 CreativeProjectManager + DatabaseManager，
为 Web 后端提供 list / detail / advance 等安全入口。

Stage C.6 设计要点：
1. 复用现有方法签名（``list_creative_projects`` / ``get_creative_project`` /
   ``_advance_one``），不修改 ``CreativeProjectManager`` 既有方法。
2. 失败路径返回 ``None`` / ``[]`` / ``(False, reason)``，由 API 层映射到 4xx。
3. 懒加载 ``CreativeProjectManager``：避免 Web 启动时强制 LLM 初始化。
4. 全局单例 ``creative_service``。
"""

from __future__ import annotations

import sys
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


class CreativeService:
    """
    创作项目服务（Web 后端侧）

    Attributes:
        _manager: 懒加载的 ``CreativeProjectManager`` 实例
    """

    def __init__(self) -> None:
        self._manager: Optional[Any] = None
        self._db: Optional[Any] = None

    # ------------------------------------------------------------------
    # 内部：懒加载 manager / db
    # ------------------------------------------------------------------
    def _try_init_manager(self) -> Optional[Any]:
        if self._manager is not None:
            return self._manager
        try:
            from src.core.creative_writer import CreativeProjectManager  # type: ignore
            self._manager = CreativeProjectManager()
            return self._manager
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[CreativeService] CreativeProjectManager 初始化失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            self._manager = None
            return None

    def _get_db(self) -> Optional[Any]:
        """
        获取 DatabaseManager（来自 manager 或独立懒加载）。
        优先使用 manager 自带的 db；否则懒加载 DatabaseManager。
        """
        mgr = self._try_init_manager()
        if mgr is not None and getattr(mgr, 'db', None) is not None:
            return mgr.db
        if self._db is not None:
            return self._db
        try:
            from src.core.database_manager import DatabaseManager  # type: ignore
            self._db = DatabaseManager()
            return self._db
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[CreativeService] DatabaseManager 懒加载失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return None

    # ------------------------------------------------------------------
    # 列表
    # ------------------------------------------------------------------
    def list_projects(
        self,
        user_id: str = "default",
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        列出创作项目。

        - ``user_id``: 当前保留参数（数据库无 user_id 字段，所有项目视为同一用户）。
        - ``status``: 业务状态过滤（drafting / finished / paused 等）。
        - ``limit``: 返回上限。

        Returns:
            标准化为 ``CreativeProjectSummary`` 兼容字段的项目列表。
        """
        db = self._get_db()
        if db is None:
            return []
        try:
            raw = db.list_creative_projects(status=status, limit=max(1, int(limit)))
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[CreativeService] list_projects 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return []
        out: List[Dict[str, Any]] = []
        for item in raw or []:
            try:
                out.append(self._normalize_summary(item))
            except Exception:
                continue
        return out

    # ------------------------------------------------------------------
    # 详情
    # ------------------------------------------------------------------
    def get_project(self, project_uuid: str) -> Optional[Dict[str, Any]]:
        """
        获取项目详情（含 Story Bible / 章节 / 记忆池摘要）。
        不存在 → None。
        """
        if not project_uuid or not isinstance(project_uuid, str):
            return None
        db = self._get_db()
        if db is None:
            return None
        try:
            project = db.get_creative_project(project_uuid)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[CreativeService] get_project({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return None
        if not project:
            return None

        detail = self._normalize_detail(project)

        # 拉取 Story Bible
        try:
            bible = db.get_story_bible(project_uuid) or {}
        except Exception:
            bible = {}
        detail['story_bible'] = bible or {}

        # 章节：优先 draft_chunks；fallback 到 outline 的伪章节
        try:
            chunks = project.get('draft_chunks') or []
        except Exception:
            chunks = []
        chapters: List[Dict[str, Any]] = []
        for idx, ch in enumerate(chunks or []):
            try:
                chapters.append({
                    'uuid': f"{project_uuid}-ch-{idx + 1:02d}",
                    'chapter_title': f"Draft Chapter {idx + 1}",
                    'word_count': int(ch.get('char_count', 0) or 0),
                    'content': ch.get('content', '') or '',
                    'created_at': ch.get('created_at', '') or '',
                })
            except Exception:
                continue
        if not chapters:
            outlines = project.get('outline') or []
            for idx, line in enumerate(outlines or []):
                chapters.append({
                    'uuid': f"{project_uuid}-outline-{idx + 1:02d}",
                    'chapter_title': f"Outline {idx + 1}",
                    'word_count': 0,
                    'content': str(line) if line else '',
                    'created_at': '',
                })
        detail['chapters'] = chapters
        detail['chapter_count'] = len(chapters)

        # 记忆池摘要
        try:
            pool = db.get_creative_memory_pool(project_uuid, limit=50) or []
        except Exception:
            pool = []
        detail['memory_pool_summary'] = {
            'count': len(pool),
            'latest': [
                {
                    'memory_type': m.get('memory_type', ''),
                    'content': (m.get('content', '') or '')[:200],
                    'importance': m.get('importance', 0.0),
                    'created_at': m.get('created_at', ''),
                }
                for m in (pool[:5] if isinstance(pool, list) else [])
            ],
        }

        return detail

    # ------------------------------------------------------------------
    # 续写
    # ------------------------------------------------------------------
    def advance(self, project_uuid: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        触发续写。

        Returns:
            (ok, reason, new_chapter_dict or None)
            - ok=True 时 new_chapter 必有值
            - ok=False 时 reason 描述原因（disabled / not_found / internal_error / not_drafting / quality_fail）
        """
        if not project_uuid or not isinstance(project_uuid, str):
            return False, "invalid_uuid", None

        mgr = self._try_init_manager()
        if mgr is None:
            return False, "manager_unavailable", None
        if not getattr(mgr, 'enabled', False):
            return False, "disabled", None

        db = self._get_db()
        if db is None:
            return False, "db_unavailable", None

        try:
            project = db.get_creative_project(project_uuid)
        except Exception:
            project = None
        if not project:
            return False, "not_found", None
        if (project.get('status') or '').lower() == 'finished':
            return False, "already_finished", None

        try:
            # 复用 _advance_one(project, now) 既有方法
            now = datetime.now()
            ok = bool(mgr._advance_one(project, now))
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[CreativeService] advance({project_uuid}) 失败: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            return False, f"internal_error: {exc}", None

        if not ok:
            return False, "quality_fail_or_skip", None

        # 重新拉取最新章节
        try:
            updated = db.get_creative_project(project_uuid) or {}
        except Exception:
            updated = {}
        chunks = updated.get('draft_chunks') or []
        new_chapter: Optional[Dict[str, Any]] = None
        if chunks:
            try:
                last = chunks[-1]
                new_chapter = {
                    'uuid': f"{project_uuid}-ch-{len(chunks):02d}",
                    'chapter_title': f"Draft Chapter {len(chunks)}",
                    'word_count': int(last.get('char_count', 0) or 0),
                    'content': last.get('content', '') or '',
                    'created_at': last.get('created_at', '') or '',
                }
            except Exception:
                new_chapter = None

        return True, "ok", new_chapter

    # ------------------------------------------------------------------
    # 标准化
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_summary(item: Dict[str, Any]) -> Dict[str, Any]:
        try:
            chunks = item.get('draft_chunks') or []
            chapter_count = len(chunks)
        except Exception:
            chapter_count = 0
        return {
            'uuid': str(item.get('uuid', '')),
            'title': str(item.get('title', '') or ''),
            'status': str(item.get('status', 'drafting') or 'drafting'),
            'chapter_count': int(chapter_count),
            'created_at': str(item.get('created_at', '') or ''),
            'updated_at': str(item.get('updated_at', '') or ''),
        }

    @staticmethod
    def _normalize_detail(item: Dict[str, Any]) -> Dict[str, Any]:
        base = CreativeService._normalize_summary(item)
        base.update({
            'story_bible': {},
            'chapters': [],
            'memory_pool_summary': {},
        })
        return base


# 全局单例
creative_service = CreativeService()


__all__ = ["CreativeService", "creative_service"]
