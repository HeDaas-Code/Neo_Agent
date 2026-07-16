"""
WebSocket routers
聚合所有 ws/* 子模块的 router，统一挂载到 FastAPI app。

Stage A.2 / D.3: 端点骨架与跨端事件分发。
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
    from src.web.backend.ws.chat import router as _chat_router
    _routers.append(_chat_router)
    _loaded['chat'] = True
except Exception as e:  # noqa: BLE001
    _loaded['chat'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('ws', f'failed to import chat router: {e}')
    except Exception:
        pass

try:
    from src.web.backend.ws.debug import router as _debug_router
    _routers.append(_debug_router)
    _loaded['debug'] = True
except Exception as e:  # noqa: BLE001
    _loaded['debug'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('ws', f'failed to import debug router: {e}')
    except Exception:
        pass

try:
    from src.web.backend.ws.events import router as _events_router
    _routers.append(_events_router)
    _loaded['events'] = True
except Exception as e:  # noqa: BLE001
    _loaded['events'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('ws', f'failed to import events router: {e}')
    except Exception:
        pass

# 兼容旧版 /ws/event 单数端点（前端 EmotionPanel/TimelineCanvas 仍引用）。
# docs/api.md 标记为"已弃用，请用 /ws/events"，但需要保持可达以做向后兼容。
try:
    from src.web.backend.ws.event import router as _event_router
    _routers.append(_event_router)
    _loaded['event'] = True
except Exception as e:  # noqa: BLE001
    _loaded['event'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('ws', f'failed to import event router: {e}')
    except Exception:
        pass

try:
    from src.web.backend.ws.proactive import router as _proactive_router
    _routers.append(_proactive_router)
    _loaded['proactive'] = True
except Exception as e:  # noqa: BLE001
    _loaded['proactive'] = False
    try:
        from src.tools.debug_logger import get_debug_logger
        get_debug_logger().log_warn('ws', f'failed to import proactive router: {e}')
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
    return dict(_loaded)


__all__ = ["router", "get_loaded_status"]
