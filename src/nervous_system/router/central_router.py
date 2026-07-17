"""
CentralRouter - 神经系统中央路由器。

所有内部模块间通信的中枢。负责：
- 按 target 路由 Packet
- 管理事件订阅
- 执行中间件链
- 全链路追踪
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Callable, Coroutine, Dict, List, Optional

from src.nervous_system.base_module import BaseModule
from src.nervous_system.router.packet import Packet, PacketType

logger = logging.getLogger(__name__)

Middleware = Callable[[Packet, Callable[[Packet], Coroutine[Any, Any, Packet]]], Coroutine[Any, Any, Packet]]
EventHandler = Callable[[Packet], Coroutine[Any, Any, None]]


class CentralRouter:
    """
    中央路由器。

    使用方式：
        router = CentralRouter()
        router.register_module("cortex.llm_core", llm_module)
        router.add_middleware(audit_middleware)
        await router.initialize()
        response = await router.route(packet)
    """

    def __init__(self) -> None:
        self._modules: Dict[str, BaseModule] = {}
        self._subscribers: Dict[str, List[EventHandler]] = {}
        self._middlewares: List[Middleware] = []
        self._event_queue: asyncio.Queue[Packet] = asyncio.Queue()
        self._event_task: Optional[asyncio.Task] = None
        self._running = False

    def register_module(self, module_id: str, module: BaseModule) -> None:
        """
        注册一个功能模块。
        """
        if module_id in self._modules:
            raise ValueError(f"模块已注册: {module_id}")
        self._modules[module_id] = module
        logger.debug("[CentralRouter] 注册模块: %s", module_id)

    def unregister_module(self, module_id: str) -> None:
        """
        注销模块。
        """
        self._modules.pop(module_id, None)

    def add_middleware(self, middleware: Middleware) -> None:
        """
        添加中间件。中间件按添加顺序执行。
        """
        self._middlewares.append(middleware)

    def subscribe(self, channel: str, handler: EventHandler) -> None:
        """
        订阅某个通道的事件。
        """
        self._subscribers.setdefault(channel, []).append(handler)

    def unsubscribe(self, channel: str, handler: EventHandler) -> None:
        """
        取消订阅。
        """
        if channel in self._subscribers:
            self._subscribers[channel] = [h for h in self._subscribers[channel] if h != handler]

    async def initialize(self) -> None:
        """
        初始化所有已注册模块，并启动事件分发任务。
        """
        self._running = True
        for module in self._modules.values():
            try:
                await module.initialize()
            except Exception as exc:
                logger.error("[CentralRouter] 初始化模块 %s 失败: %s", module.module_id, exc)
                raise
        self._event_task = asyncio.create_task(self._event_loop())
        logger.info("[CentralRouter] 初始化完成，模块数: %d", len(self._modules))

    async def shutdown(self) -> None:
        """
        关闭所有模块和事件循环。
        """
        self._running = False
        if self._event_task:
            self._event_task.cancel()
            try:
                await self._event_task
            except asyncio.CancelledError:
                pass
        for module in self._modules.values():
            try:
                await module.shutdown()
            except Exception as exc:
                logger.error("[CentralRouter] 关闭模块 %s 失败: %s", module.module_id, exc)
        logger.info("[CentralRouter] 已关闭")

    async def route(self, packet: Packet) -> Packet:
        """
        路由一个 Packet 到目标模块并返回响应。
        """
        start_time = time.time()
        packet.metadata.setdefault("router_hops", []).append({
            "module": "central_router",
            "action": "route",
            "timestamp": start_time,
        })

        handler = self._build_handler()
        try:
            response = await handler(packet)
        except Exception as exc:
            logger.exception("[CentralRouter] 路由异常: %s", exc)
            response = Packet.error(packet, str(exc), code="ROUTER_ERROR")

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug("[CentralRouter] 路由耗时 %.3fms: %s -> %s", elapsed_ms, packet.source, packet.target)
        return response

    async def route_stream(self, packet: Packet) -> AsyncIterator[Packet]:
        """
        流式路由一个 Packet 到目标模块。

        直接调用目标模块的 handle_stream，绕过同步中间件链，
        但会记录 trace 并在出错时 yield ERROR/STREAM_ERROR 包。
        """
        start_time = time.time()
        packet.metadata.setdefault("router_hops", []).append({
            "module": "central_router",
            "action": "route_stream",
            "timestamp": start_time,
        })

        target_module = self._modules.get(packet.target)
        if target_module is None:
            yield Packet.error(packet, f"目标模块未找到: {packet.target}", code="MODULE_NOT_FOUND")
            return

        try:
            async for chunk in target_module.handle_stream(packet):
                yield chunk
        except Exception as exc:
            logger.exception("[CentralRouter] 流式路由异常: %s", exc)
            yield packet.stream_error(str(exc), code="ROUTER_ERROR")

        elapsed_ms = (time.time() - start_time) * 1000
        logger.debug("[CentralRouter] 流式路由耗时 %.3fms: %s -> %s", elapsed_ms, packet.source, packet.target)

    async def publish(self, packet: Packet) -> None:
        """
        发布事件到队列，由事件循环异步分发给订阅者。
        """
        await self._event_queue.put(packet)

    def _build_handler(self) -> Callable[[Packet], Coroutine[Any, Any, Packet]]:
        """
        构建中间件链，最终调用目标模块的 handle。
        """
        async def final_handler(packet: Packet) -> Packet:
            if packet.packet_type == PacketType.EVENT:
                # 事件类型直接分发，不返回响应
                await self._dispatch_event(packet)
                return packet.response({"status": "dispatched"})

            target_module = self._modules.get(packet.target)
            if target_module is None:
                return Packet.error(packet, f"目标模块未找到: {packet.target}", code="MODULE_NOT_FOUND")

            return await target_module.handle(packet)

        handler: Callable[[Packet], Coroutine[Any, Any, Packet]] = final_handler
        for middleware in reversed(self._middlewares):
            current = middleware
            next_handler = handler
            handler = lambda packet, m=current, n=next_handler: m(packet, n)

        return handler

    async def _dispatch_event(self, packet: Packet) -> None:
        """
        分发事件给订阅者。
        """
        handlers = self._subscribers.get(packet.channel, [])
        if not handlers:
            logger.debug("[CentralRouter] 通道 %s 无订阅者", packet.channel)
            return

        await asyncio.gather(
            *(self._safe_handle(handler, packet) for handler in handlers),
            return_exceptions=True,
        )

    async def _safe_handle(self, handler: EventHandler, packet: Packet) -> None:
        try:
            await handler(packet)
        except Exception as exc:
            logger.error("[CentralRouter] 事件处理异常: %s", exc)

    async def _event_loop(self) -> None:
        """
        后台事件分发循环。
        """
        while self._running:
            try:
                packet = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._dispatch_event(packet)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("[CentralRouter] 事件循环异常: %s", exc)
