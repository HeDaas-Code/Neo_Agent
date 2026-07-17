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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Phase 6: v4.0 神经系统桥接（导入失败不破坏 v3）
try:
    from src.nervous_system.app import NeoApp
    from src.nervous_system.router.packet import Packet, PacketType
    from src.web.backend.services.neo_bridge import set_neo_app
except Exception:  # noqa: BLE001
    NeoApp = None  # type: ignore
    Packet = None  # type: ignore
    PacketType = None  # type: ignore
    set_neo_app = None  # type: ignore

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


# =====================================================================
# Phase 6: v4.0 NeoApp 全局实例（失败不影响 v3）
# =====================================================================
_neo_app: "NeoApp | None" = None


def get_neo_app() -> "NeoApp | None":
    """返回当前进程内的全局 NeoApp 实例。"""
    return _neo_app


@app.get("/api/health")
async def health_check() -> dict:
    """
    健康检查端点
    Health check endpoint.

    返回服务状态、版本号、当前时间戳（ISO 8601, UTC）以及 v4 模块状态。
    """
    result = {
        "status": "ok",
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "v4_status": "ok",
        "v4_modules": [],
    }

    neo = get_neo_app()
    if neo is None:
        result["v4_status"] = "degraded"
        return result

    try:
        result["v4_modules"] = list(neo.router._modules.keys())
    except Exception as exc:  # noqa: BLE001
        result["v4_status"] = "degraded"
        try:
            from src.tools.debug_logger import get_debug_logger
            get_debug_logger().log_error('main', f'读取 v4 模块列表失败: {exc}', exc)
        except Exception:
            pass

    return result


@app.get("/api/chat")
async def chat_placeholder() -> dict:
    """
    占位聊天端点（Stage A.3 替换为真实实现）
    """
    return {"message": "chat endpoint placeholder"}


# =====================================================================
# Phase 6: v4.0 通用网关路由
# =====================================================================
@app.post("/api/v4/gateway/{target}/{channel}")
async def v4_gateway(target: str, channel: str, request: Request) -> JSONResponse:
    """
    通过 CentralRouter 调用任意 v4 模块。

    请求体作为 payload 透传给目标模块；返回体统一为
    {"data": ..., "trace_id": ...} 或 {"error": ..., "code": ..., "trace_id": ...}。
    """
    neo = get_neo_app()
    if neo is None or Packet is None or PacketType is None:
        return JSONResponse(
            status_code=503,
            content={
                "error": "v4 nervous system not available",
                "code": "NEOAPP_NOT_READY",
                "trace_id": "",
            },
        )

    body: dict = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}

    try:
        packet = Packet(
            source="web.backend",
            target=target,
            packet_type=PacketType.REQUEST,
            channel=channel,
            payload=body,
            metadata={"user_id": request.headers.get("X-User-Id", "default")},
        )
        response = await neo.router.route(packet)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "code": "GATEWAY_EXCEPTION",
                "trace_id": getattr(exc, "trace_id", ""),
            },
        )

    if response.is_error():
        return JSONResponse(
            status_code=500,
            content={
                "error": response.payload.get("error", "unknown error"),
                "code": response.payload.get("code", "INTERNAL_ERROR"),
                "trace_id": response.trace_id,
            },
        )

    return JSONResponse(
        status_code=200,
        content={"data": response.payload, "trace_id": response.trace_id},
    )


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

    # Phase 6: 初始化 v4.0 NeoApp（失败不影响 v3）
    if NeoApp is not None and set_neo_app is not None:
        global _neo_app
        try:
            _neo_app = NeoApp()
            set_neo_app(_neo_app)
            await _neo_app.initialize()
        except Exception as e:  # noqa: BLE001
            _neo_app = None
            try:
                set_neo_app(None)
            except Exception:
                pass
            try:
                from src.tools.debug_logger import get_debug_logger
                get_debug_logger().log_error('main', f'NeoApp 初始化失败: {e}', e)
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
    global _event_service_started, _debug_broadcaster_started, _neo_app
    # Phase 6: 关闭 v4.0 NeoApp（失败忽略）
    if _neo_app is not None:
        try:
            await _neo_app.shutdown()
        except Exception:
            pass
        _neo_app = None
        try:
            set_neo_app(None)
        except Exception:
            pass
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
