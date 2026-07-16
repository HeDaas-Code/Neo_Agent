"""
DebugBroadcaster
- 启动时把 DebugLogger 的日志广播到 /ws/debug 频道
- 兼容两种集成方式：
  1) 通过 EventService（推荐）：注册 EventService 'debug_log' listener，由 events WS 转发
  2) 直接通过 manager.broadcast('debug', ...) 向 /ws/debug 客户端推送

本模块只负责订阅 + 派发；具体 WebSocket 生命周期由 ws/debug.py 管理。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


class DebugBroadcaster:
    """
    调试日志广播器
    - 启动时调用 attach() 注册订阅者
    - 关闭时调用 detach() 取消订阅
    - 同步 subscriber：直接 broadcast；async subscriber：调度到事件循环
    """

    CHANNEL = "debug"

    def __init__(self) -> None:
        self._unsub_debug: Optional[Callable[[], None]] = None
        self._unsub_event_service: Optional[Callable[[], None]] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def attach(self, manager: Any = None, event_service: Any = None,
               loop: Optional[asyncio.AbstractEventLoop] = None) -> bool:
        """
        注册订阅者。

        Args:
            manager: ConnectionManager 实例（来自 ws/manager.py）。Stage A.2 兼容：
                     既支持新 manager（仅 channel -> broadcast）也支持老 manager 单例。
            event_service: EventService 实例（可选）
            loop: 主事件循环

        Returns:
            True 表示至少成功注册了 DebugLogger 订阅者。
        """
        self._loop = loop
        try:
            from src.tools.debug_logger import get_debug_logger
        except Exception:
            return False
        debug_logger = get_debug_logger()
        try:
            debug_logger.set_main_loop(loop)
        except Exception:
            pass

        if manager is not None and hasattr(debug_logger, 'subscribe'):
            def _sync_subscriber(log_entry: Dict[str, Any]) -> None:
                try:
                    if manager is None:
                        return
                    coro = manager.broadcast(self.CHANNEL, {
                        "type": "log",
                        "entry": log_entry,
                    })
                    try:
                        running_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        running_loop = None
                    if running_loop is not None and self._loop is running_loop:
                        running_loop.create_task(coro)
                    else:
                        target = self._loop
                        if target is not None and target.is_running():
                            asyncio.run_coroutine_threadsafe(coro, target)
                        else:
                            try:
                                asyncio.run(coro)
                            except Exception:
                                pass
                except Exception:
                    pass

            try:
                unsub = debug_logger.subscribe(_sync_subscriber)
                if unsub is not None and callable(unsub):
                    self._unsub_debug = unsub
            except Exception:
                self._unsub_debug = None

        if event_service is not None and hasattr(event_service, 'register_websocket_listener'):
            try:
                async def _es_listener(_event_type: str, payload: Dict[str, Any]) -> None:
                    if manager is not None:
                        await manager.broadcast(self.CHANNEL, payload)

                self._unsub_event_service = event_service.register_websocket_listener(
                    'debug_log', _es_listener
                )
            except Exception:
                self._unsub_event_service = None

        return self._unsub_debug is not None or self._unsub_event_service is not None

    def detach(self) -> None:
        """取消所有订阅。"""
        if self._unsub_debug is not None:
            try:
                self._unsub_debug()
            except Exception:
                pass
            self._unsub_debug = None
        if self._unsub_event_service is not None:
            try:
                self._unsub_event_service()
            except Exception:
                pass
            self._unsub_event_service = None


# 进程级单例
_broadcaster: Optional[DebugBroadcaster] = None


def get_debug_broadcaster() -> DebugBroadcaster:
    """获取全局 DebugBroadcaster 单例。"""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = DebugBroadcaster()
    return _broadcaster


__all__ = ["DebugBroadcaster", "get_debug_broadcaster"]
