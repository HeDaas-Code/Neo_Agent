"""
NPS REST API router - Stage C.4 / 验收 P0 3.2
NPS 插件（Neo Plugin System）的 REST API 路由。

端点：
  GET    /api/nps                 列出所有 NPS 工具（含 enabled / disabled）
  POST   /api/nps/register        手动注册一个新的 NPS 工具
  POST   /api/nps/invoke          调用指定 NPS 工具并返回结果

设计要点：
1. 复用 ``src.nps.nps_registry.NPSRegistry`` 与
   ``src.nps.nps_invoker.NPSInvoker``，Web 层仅做参数透传与序列化。
2. 进程内懒加载单例：NPSRegistry / NPSInvoker 各保持一份；
   NPSInvoker 构造时自动 scan_and_register，扫描失败不抛 5xx。
3. 所有路由 try/except 包裹，失败返回 4xx + {"error": str(e)}，
   绝不冒 5xx（验收硬约束）。
4. Pydantic v2 schema（NPSRegisterRequest / NPSInvokeRequest）做
   body 校验，非法 body 由 FastAPI 自动返回 422。
5. 数据库 / 配置目录不可用时返回空列表 / 默认响应（graceful degradation）。
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Body, HTTPException, status  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

# 调试日志（try/except 保护：debug_logger 不可用时降级为 stub）
try:
    from src.tools.debug_logger import get_debug_logger as _get_debug_logger
    _debug_logger = _get_debug_logger()
except Exception:  # noqa: BLE001
    class _StubLogger:
        def log_info(self, *a, **k): pass
        def log_warn(self, *a, **k): pass
        def log_error(self, *a, **k): pass
    _debug_logger = _StubLogger()


# ---------------------------------------------------------------------
# NPSRegistry / NPSInvoker 懒加载（try/except 保护）
# ---------------------------------------------------------------------
_registry: Optional[Any] = None
_invoker: Optional[Any] = None
_NPS_IMPORT_OK: bool = False
_NPS_IMPORT_ERROR: Optional[BaseException] = None

try:
    from src.nps.nps_registry import NPSRegistry, NPSTool  # noqa: E402
    from src.nps.nps_invoker import NPSInvoker  # noqa: E402
    _NPS_IMPORT_OK = True
except Exception as _exc:  # noqa: BLE001
    NPSRegistry = None  # type: ignore
    NPSTool = None  # type: ignore
    NPSInvoker = None  # type: ignore
    _NPS_IMPORT_ERROR = _exc


def _get_registry() -> Optional[Any]:
    """
    懒加载 NPSRegistry 单例。
    - 失败时返回 None（路由层兜底为 503 / 空列表）。
    """
    global _registry
    if _registry is not None:
        return _registry
    if not _NPS_IMPORT_OK or NPSRegistry is None:
        return None
    try:
        _registry = NPSRegistry()
        # 尝试自动扫描；失败不抛
        try:
            _registry.scan_and_register()
        except Exception as scan_exc:  # noqa: BLE001
            _debug_logger.log_warn(
                'nps_api',
                f'自动扫描 NPS 工具失败（不影响路由）: {scan_exc}',
            )
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('nps_api', f'创建 NPSRegistry 失败: {exc}', exc)
        _registry = None
    return _registry


def _get_invoker() -> Optional[Any]:
    """
    懒加载 NPSInvoker 单例。
    - 失败时返回 None（路由层兜底）。
    """
    global _invoker
    if _invoker is not None:
        return _invoker
    if not _NPS_IMPORT_OK or NPSInvoker is None:
        return None
    try:
        _invoker = NPSInvoker(registry=_get_registry())
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('nps_api', f'创建 NPSInvoker 失败: {exc}', exc)
        _invoker = None
    return _invoker


# ---------------------------------------------------------------------
# Pydantic v2 Schemas（强类型契约）
# ---------------------------------------------------------------------
class NPSRegisterRequest(BaseModel):
    """
    手动注册 NPS 工具的请求体。
    Attributes:
        tool_id: 工具唯一标识符（必填）
        name: 工具名称（必填）
        description: 工具功能描述（必填）
        keywords: 触发关键词列表（可选）
        enabled: 是否启用（默认 True）
        version: 版本号（默认 "1.0.0"）
        author: 作者（默认 "Unknown"）
    """
    tool_id: str = Field(..., min_length=1, max_length=128, description="工具唯一标识符")
    name: str = Field(..., min_length=1, max_length=256, description="工具名称")
    description: str = Field("", description="工具功能描述（用于LLM判断相关性）")
    keywords: List[str] = Field(default_factory=list, description="触发关键词列表")
    enabled: bool = Field(True, description="是否启用")
    version: str = Field("1.0.0", description="版本号")
    author: str = Field("Unknown", description="作者")


class NPSInvokeRequest(BaseModel):
    """
    调用 NPS 工具的请求体。
    Attributes:
        tool_name: 工具名称或 tool_id（必填）
        context: 执行上下文 dict（默认空）
        use_llm: 是否使用 LLM 判断相关性（保留字段；此处按名称直接调用）
    """
    tool_name: str = Field(..., min_length=1, description="工具名称或 tool_id")
    context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")
    use_llm: bool = Field(False, description="是否使用 LLM（直接调用时无效）")


# ---------------------------------------------------------------------
# 工具：NPSTool → dict 序列化
# ---------------------------------------------------------------------
def _tool_to_dict(tool: Any) -> Dict[str, Any]:
    """
    把 NPSTool 序列化为前端兼容的 dict。
    """
    if tool is None:
        return {}
    try:
        if hasattr(tool, 'to_dict') and callable(getattr(tool, 'to_dict')):
            return dict(tool.to_dict())
    except Exception:  # noqa: BLE001
        pass
    # fallback：手动拼装
    return {
        'tool_id': getattr(tool, 'tool_id', ''),
        'name': getattr(tool, 'name', ''),
        'description': getattr(tool, 'description', ''),
        'keywords': list(getattr(tool, 'keywords', []) or []),
        'version': getattr(tool, 'version', '1.0.0'),
        'author': getattr(tool, 'author', 'Unknown'),
        'enabled': bool(getattr(tool, 'enabled', True)),
    }


def _fail(message: str, code: int = status.HTTP_400_BAD_REQUEST) -> Dict[str, Any]:
    """统一兜底响应。"""
    return {"error": message, "status_code": code}


# ---------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------
router = APIRouter(prefix="/api/nps", tags=["nps"])


# =====================================================================
# GET /api/nps
# =====================================================================
@router.get("")
async def list_nps() -> Dict[str, Any]:
    """
    列出所有已注册的 NPS 工具。

    包含 enabled / disabled 全部工具。
    registry 不可用时返回空列表（graceful degradation）。

    Returns:
        {"items": [...], "total": int, "enabled": int, "disabled": int}
    """
    try:
        registry = _get_registry()
        if registry is None:
            return {
                "items": [],
                "total": 0,
                "enabled": 0,
                "disabled": 0,
                "warning": "NPSRegistry 不可用：导入或初始化失败",
            }

        tools = registry.get_all_tools() or []
        items: List[Dict[str, Any]] = []
        enabled_count = 0
        for t in tools:
            d = _tool_to_dict(t)
            if d:
                items.append(d)
                if d.get('enabled', True):
                    enabled_count += 1
        return {
            "items": items,
            "total": len(items),
            "enabled": enabled_count,
            "disabled": max(0, len(items) - enabled_count),
        }
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('nps_api', f'list_nps 失败: {exc}', exc)
        warnings.warn(
            f"[nps_api] list_nps 失败: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return _fail(f"列出 NPS 工具失败: {exc}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# POST /api/nps/register
# =====================================================================
@router.post("/register")
async def register_nps(payload: NPSRegisterRequest = Body(...)) -> Dict[str, Any]:
    """
    手动注册一个新的 NPS 工具。

    复用 NPSRegistry.register_tool；tool_id 已存在时返回 409。
    由于 NPSTool 需要 execute_func，本接口仅做"元数据记录"：
    - 把工具元信息写入 NPSConfigManager（configs/nps_plugins/）。
    - 若 registry 中已存在该 tool_id，返回 409。
    - 若不存在，把元信息持久化为可被下次启动读取的条目。

    Returns:
        {"tool_id": str, "name": str, "registered": true, "persisted": bool}
    """
    try:
        registry = _get_registry()
        if registry is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NPSRegistry 不可用：导入或初始化失败",
            )

        # 检查是否已存在
        try:
            existing = registry.get_tool(payload.tool_id)
        except Exception:  # noqa: BLE001
            existing = None
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"工具已存在: {payload.tool_id}",
            )

        # 把元数据持久化到 NPSConfigManager（graceful：失败不抛 5xx）
        persisted = False
        try:
            from src.nps.nps_config_manager import NPSConfigManager  # type: ignore
            cm = NPSConfigManager()
            cm.set_plugin_config(
                payload.tool_id,
                {
                    'name': payload.name,
                    'description': payload.description,
                    'keywords': list(payload.keywords or []),
                    'enabled': bool(payload.enabled),
                    'version': payload.version,
                    'author': payload.author,
                },
            )
            persisted = True
        except Exception as persist_exc:  # noqa: BLE001
            _debug_logger.log_warn(
                'nps_api',
                f'持久化 NPS 配置失败（仅元信息）: {persist_exc}',
            )
            persisted = False

        # 同步把"占位"工具注册到当前进程 registry（无 execute_func，仅元数据）
        if NPSTool is not None:
            try:
                placeholder = NPSTool(
                    tool_id=payload.tool_id,
                    name=payload.name,
                    description=payload.description,
                    keywords=list(payload.keywords or []),
                    execute_func=lambda *a, **k: {
                        'success': False,
                        'error': '此工具未实现 execute_func（仅元数据已注册）',
                    },
                    version=payload.version,
                    author=payload.author,
                    enabled=bool(payload.enabled),
                )
                registry.register_tool(placeholder)
            except Exception as reg_exc:  # noqa: BLE001
                _debug_logger.log_warn(
                    'nps_api',
                    f'把工具注册到当前进程 registry 失败: {reg_exc}',
                )

        return {
            "tool_id": payload.tool_id,
            "name": payload.name,
            "registered": True,
            "persisted": persisted,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('nps_api', f'register_nps 失败: {exc}', exc)
        return _fail(f"注册 NPS 工具失败: {exc}", code=status.HTTP_400_BAD_REQUEST)


# =====================================================================
# POST /api/nps/invoke
# =====================================================================
@router.post("/invoke")
async def invoke_nps(payload: NPSInvokeRequest = Body(...)) -> Dict[str, Any]:
    """
    调用指定 NPS 工具。

    复用 NPSInvoker.invoke_tool_by_name。
    工具不存在 / 未启用 → 返回 4xx + 友好错误。

    Returns:
        {"success": bool, "tool_id": str, "tool_name": str,
         "result": Any | None, "error": str | None}
    """
    try:
        invoker = _get_invoker()
        if invoker is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NPSInvoker 不可用：导入或初始化失败",
            )

        # 直接按名称调用（不走 LLM 判相关性）
        out = invoker.invoke_tool_by_name(
            tool_name=payload.tool_name,
            context=payload.context or {},
        )
        # out 形如 {"success": bool, "tool_id": ..., "tool_name": ...,
        #           "result": ..., "error": ...}
        if not isinstance(out, dict):
            return _fail(
                f"调用结果非 dict: {type(out).__name__}",
                code=status.HTTP_400_BAD_REQUEST,
            )

        if not out.get('success', False):
            # 工具不存在 / 未启用 / 执行失败
            return {
                "success": False,
                "tool_id": out.get('tool_id', payload.tool_name),
                "tool_name": out.get('tool_name', payload.tool_name),
                "result": None,
                "error": out.get('error', '调用失败'),
                "status_code": status.HTTP_404_NOT_FOUND
                if '未找到' in (out.get('error') or '')
                else status.HTTP_400_BAD_REQUEST,
            }

        return {
            "success": True,
            "tool_id": out.get('tool_id', payload.tool_name),
            "tool_name": out.get('tool_name', payload.tool_name),
            "result": out.get('result'),
            "error": None,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        _debug_logger.log_error('nps_api', f'invoke_nps 失败: {exc}', exc)
        return _fail(f"调用 NPS 工具失败: {exc}", code=status.HTTP_400_BAD_REQUEST)


__all__ = ["router"]
