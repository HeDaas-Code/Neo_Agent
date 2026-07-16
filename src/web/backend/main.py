#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo Agent Web Backend - FastAPI Entry Point
Neo Agent Web 后端 - FastAPI 入口

Stage A.1: 基础框架与健康检查
Stage D.3: EventService 启动 + WebSocket 路由挂载
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Python 路径处理：确保从项目根目录（Neo_Agent/）能正确导入 src.* 模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# FastAPI 应用实例
app = FastAPI(
    title="Neo Agent Web",
    version="3.0.0",
    description="Neo Agent Web GUI 后端服务",
)

# CORS 中间件配置（开发态允许本地 Vite/后端端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check() -> dict:
    """
    健康检查端点
    Health check endpoint.

    返回服务状态、版本号与当前时间戳（ISO 8601, UTC）。
    """
    return {
        "status": "ok",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/chat")
async def chat_placeholder() -> dict:
    """
    占位聊天端点（Stage A.3 替换为真实实现）
    """
    return {"message": "chat endpoint placeholder"}


# =====================================================================
# Stage D.3: EventService 单例 + WebSocket 路由
# =====================================================================
# 启动时创建单例 EventService 并订阅 EventManager；
# 之后 ws/* 路由通过 EventService 把事件广播到 /ws/events / /ws/debug 等。
_event_service = None
_event_service_started = False
_debug_broadcaster_started = False


def _get_event_service():
    """懒加载 EventService 单例。"""
    global _event_service
    if _event_service is None:
        try:
            from src.web.backend.services.event_service import get_event_service
            _event_service = get_event_service()
        except Exception as e:  # noqa: BLE001
            try:
                from src.tools.debug_logger import get_debug_logger
                get_debug_logger().log_error('main', f'创建 EventService 失败: {e}', e)
            except Exception:
                pass
            _event_service = None
    return _event_service


@app.on_event("startup")
async def _on_startup() -> None:
    """应用启动钩子：启动 EventService + 挂载 ws 路由 + 启动 DebugBroadcaster。"""
    global _event_service_started, _debug_broadcaster_started
    es = _get_event_service()
    if es is not None and not _event_service_started:
        try:
            es.start()
            _event_service_started = True
        except Exception as e:  # noqa: BLE001
            try:
                from src.tools.debug_logger import get_debug_logger
                get_debug_logger().log_error('main', f'EventService.start 失败: {e}', e)
            except Exception:
                pass

    # Stage C.1: 挂载 Knowledge REST API
    try:
        from src.web.backend.api.knowledge import router as knowledge_router
        app.include_router(knowledge_router, prefix="/api/knowledge")
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 knowledge 路由失败: {e}', e)
        except Exception:
            pass

    # 挂载 ws 路由（每个进程只挂一次）
    try:
        from src.web.backend.ws import router as ws_router, get_loaded_status
        # 挂载到 /ws/* 子路径（chat/debug/events 的 router 已包含完整路径）
        app.include_router(ws_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 ws 路由失败: {e}', e)
        except Exception:
            pass

    # Stage C.2: 挂载 /api/schedule 路由
    try:
        from src.web.backend.api.schedule import router as schedule_router
        app.include_router(schedule_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 schedule 路由失败: {e}', e)
        except Exception:
            pass

    # 挂载 REST API 路由（debug / knowledge / schedule）
    try:
        from src.web.backend.api import router as api_router
        # 聚合 router 自身为空；子模块 router 内部已定义 prefix='/api/...'
        app.include_router(api_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 api 路由失败: {e}', e)
        except Exception:
            pass

    # Stage C.5 / C.6: 挂载 REST 路由
    try:
        from src.web.backend.api.database import router as database_router
        app.include_router(database_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 database 路由失败: {e}', e)
        except Exception:
            pass

    try:
        from src.web.backend.api.creative import router as creative_router
        app.include_router(creative_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 creative 路由失败: {e}', e)
        except Exception:
            pass

    # Stage B.3 + B.4: 情感雷达 + 话题时间线路由
    try:
        from src.web.backend.api.emotion import router as emotion_router
        app.include_router(emotion_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 emotion 路由失败: {e}', e)
        except Exception:
            pass

    try:
        from src.web.backend.api.memory import router as memory_router
        app.include_router(memory_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 memory 路由失败: {e}', e)
        except Exception:
            pass

    # Stage C.3 / C.4 / 验收 P0 3.2: 挂载 NPS + Events REST 路由
    try:
        from src.web.backend.api.nps import router as nps_router
        app.include_router(nps_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 nps 路由失败: {e}', e)
        except Exception:
            pass

    try:
        from src.web.backend.api.event import router as event_router
        app.include_router(event_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 event 路由失败: {e}', e)
        except Exception:
            pass

    # v3.1.0: 挂载 LLM 路由（GET /api/llm/config, POST /api/llm/test）
    # 注：router 自身已带 prefix="/api/llm"，main.py 不再叠加
    try:
        from src.web.backend.api.llm import router as llm_router
        app.include_router(llm_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 llm 路由失败: {e}', e)
        except Exception:
            pass

    # v3.1.0: 挂载 chat_sessions 路由（GET/POST/PATCH/DELETE /api/chat/sessions）
    # 注：router 自身已带 prefix="/api/chat/sessions"，main.py 不再叠加
    try:
        from src.web.backend.api.chat_sessions import router as chat_sessions_router
        app.include_router(chat_sessions_router)
    except Exception as e:  # noqa: BLE001
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'挂载 chat_sessions 路由失败: {e}', e)
        except Exception:
            pass

    # Stage D.4: 启动 DebugBroadcaster，把 DebugLogger 推送到 /ws/debug
    if not _debug_broadcaster_started:
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            from src.web.backend.ws.manager import get_connection_manager
            from src.web.backend.ws.debug_broadcaster import get_debug_broadcaster
            broadcaster = get_debug_broadcaster()
            broadcaster.attach(
                manager=get_connection_manager(),
                event_service=es,
                loop=loop,
            )
            _debug_broadcaster_started = True
        except Exception as e:  # noqa: BLE001
            try:
                from src.tools.debug_logger import get_debug_logger
                get_debug_logger().log_error('main', f'DebugBroadcaster 启动失败: {e}', e)
            except Exception:
                pass


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    """应用关闭钩子。"""
    global _event_service_started, _debug_broadcaster_started
    if _event_service is not None and _event_service_started:
        try:
            _event_service.stop()
        except Exception:
            pass
        _event_service_started = False
    # 关闭 DebugBroadcaster
    try:
        from src.web.backend.ws.debug_broadcaster import get_debug_broadcaster
        get_debug_broadcaster().detach()
    except Exception:
        pass
    _debug_broadcaster_started = False


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
