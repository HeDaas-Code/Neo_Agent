"""
nervous_system/app.py - v4.0 MVP FastAPI 入口。
>
这是一个独立的入口，用于验证新的神经系统架构：
- CentralRouter
- HTTP Gateway
- WebSocket Gateway
- LLM Gateway

不会破坏现有的 Web 后端。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.cerebellum.module import CerebellumModule
from src.cortex.llm_core import LLMCore
from src.hypothalamus.module import HypothalamusModule
from src.limbic.amygdala.module import AmygdalaModule
from src.limbic.hippocampus.module import HippocampusModule
from src.prefrontal.module import PrefrontalModule
from src.prefrontal.workflow_module import WorkflowModule
from src.nervous_system.gateway.http_gateway import HTTPGateway
from src.nervous_system.gateway.llm_gateway import LLMGateway
from src.nervous_system.gateway.ws_gateway import WebSocketGateway
from src.nervous_system.router.central_router import CentralRouter
from src.nervous_system.router.pipeline import (
    AuditMiddleware,
    StreamAuditMiddleware,
    StreamTimingMiddleware,
    TimingMiddleware,
)
from src.version import __version__

logger = logging.getLogger(__name__)


class NeoApp:
    """
    新版 Neo Agent 应用容器。
    """

    def __init__(self) -> None:
        self.router = CentralRouter()
        self.http_gateway = HTTPGateway(self.router)
        self.ws_gateway = WebSocketGateway(self.router)
        self.llm_gateway = LLMGateway(self.router)
        self.hippocampus_full = HippocampusModule(self.router)
        self.amygdala = AmygdalaModule(self.router)
        self.hypothalamus = HypothalamusModule(self.router)
        self.prefrontal = PrefrontalModule(self.router)
        self.workflow = WorkflowModule(self.router)
        self.cerebellum = CerebellumModule(self.router)
        self.llm_core = LLMCore(self.router)

    @property
    def capabilities(self) -> dict:
        """
        声明 v4 神经系统能力集合，便于前端/调用方感知路径差异。
        """
        return {
            "streaming": True,
            "tool_calling": True,
            "memory": True,
            "emotion": True,
            "schedule": True,
            "version": __version__,
        }

    async def initialize(self) -> None:
        """
        注册模块、添加中间件、初始化。
        """
        self.router.add_middleware(AuditMiddleware())
        self.router.add_middleware(TimingMiddleware())
        self.router.add_stream_middleware(StreamAuditMiddleware())
        self.router.add_stream_middleware(StreamTimingMiddleware())

        self.router.register_module(self.hippocampus_full.module_id, self.hippocampus_full)
        self.router.register_module(self.amygdala.module_id, self.amygdala)
        self.router.register_module(self.hypothalamus.module_id, self.hypothalamus)
        self.router.register_module(self.prefrontal.module_id, self.prefrontal)
        self.router.register_module(self.workflow.module_id, self.workflow)
        self.router.register_module(self.cerebellum.module_id, self.cerebellum)
        self.router.register_module(self.llm_core.module_id, self.llm_core)
        self.router.register_module(self.llm_gateway.module_id, self.llm_gateway)

        await self.router.initialize()
        await self.http_gateway.start()
        await self.ws_gateway.start()
        logger.info("[NeoApp] v%s 初始化完成", __version__)

    async def shutdown(self) -> None:
        """
        关闭应用。
        """
        await self.http_gateway.stop()
        await self.ws_gateway.stop()
        await self.router.shutdown()
        logger.info("[NeoApp] v%s 已关闭", __version__)


# 全局应用实例
neo_app = NeoApp()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    FastAPI 生命周期管理。
    """
    await neo_app.initialize()
    yield
    await neo_app.shutdown()


app = FastAPI(
    title="Neo Agent",
    version=__version__,
    description="基于人脑认知架构的新一代 Neo Agent",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v4/health")
async def health_v4() -> dict:
    """
    v4 健康检查。
    """
    return {
        "status": "ok",
        "version": __version__,
        "modules": list(neo_app.router._modules.keys()),
        "capabilities": neo_app.capabilities,
    }


@app.get("/api/v4/capabilities")
async def capabilities_v4() -> dict:
    """
    v4 能力清单。

    明确声明 v4 神经系统支持的能力，便于与 v3 ChatService 路径做差异对比。
    """
    return neo_app.capabilities


@app.post("/api/v4/chat")
async def chat_v4(request: Request) -> JSONResponse:
    """
    v4.0 MVP 聊天接口。

    请求体：
        {"content": "你好"}

    响应：
        {"data": {"role": "assistant", "content": "..."}, "trace_id": "..."}
    """
    gateway_request = await neo_app.http_gateway.parse_fastapi_request(request)
    response = await neo_app.http_gateway.handle(gateway_request)
    return JSONResponse(status_code=response.status_code, content=response.body)
