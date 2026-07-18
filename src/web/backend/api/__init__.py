"""
REST API routers package
聚合 debug / knowledge / schedule 等 router，统一挂载到 FastAPI app。

Stage B.5 / C.1 / C.2: 三个核心 CRUD 模块聚合入口。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter

# 子模块 routers（用 try/except 保护，避免单个模块失败影响整体导入）
_routers = []
_loaded = {}

try:
    from src.web.backend.api.debug import router as _debug_router
    _routers.append(_debug_router)
    _loaded['debug'] = True
except Exception as e:  # noqa: BLE001
    _loaded['debug'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('api', f'failed to import debug router: {e}')
    except Exception:
        pass

# Stage C.1: knowledge router 不在此聚合（main.py 用 prefix='/api/knowledge' 单独挂载）
# 如果在这里 include，会在没有 prefix 的情况下注册 ""、"/search"、"/{uuid}" 等相对路径，
# 与 /api/knowledge/* 冲突。注释保留以示缘由。
# try:
#     from src.web.backend.api.knowledge import router as _knowledge_router
#     _routers.append(_knowledge_router)
#     _loaded['knowledge'] = True
# except Exception as e:  # noqa: BLE001
#     _loaded['knowledge'] = False
#     try:
#         from src.tools.debug_logger import get_debug_logger
#         get_debug_logger().log_warn('api', f'failed to import knowledge router: {e}')
#     except Exception:
#         pass

try:
    from src.web.backend.api.schedule import router as _schedule_router
    _routers.append(_schedule_router)
    _loaded['schedule'] = True
except Exception as e:  # noqa: BLE001
    _loaded['schedule'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('api', f'failed to import schedule router: {e}')
    except Exception:
        pass

# 额外聚合（与 main.py 中的 include_router 行为一致；不重复挂载则 no-op）
for _name in ('creative', 'database', 'emotion', 'memory'):
    try:
        mod = __import__(f'src.web.backend.api.{_name}', fromlist=['router'])
        _routers.append(mod.router)
        _loaded[_name] = True
    except Exception as e:  # noqa: BLE001
        _loaded[_name] = False
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_warn('api', f'failed to import {_name} router: {e}')
        except Exception:
            pass

# 统一 router（保留空 router 以便 main.py 无脑 include_router）
router = APIRouter()
for r in _routers:
    try:
        router.include_router(r)
    except Exception:
        pass


def get_loaded_status() -> dict:
    """返回各子模块加载状态（调试/健康检查用）。"""
    return dict(_loaded)


__all__ = ["router", "get_loaded_status"]
