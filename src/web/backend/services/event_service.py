"""
EventService - 跨端事件服务

Stage D.3:
- 提供 `register_websocket_listener(channel, callback)` 注册 WebSocket 监听器
- 提供 `emit_event(event_type, payload)` 触发事件（异步派发到匹配 channel 的 listener）
- 提供 `start()` 启动后台任务，订阅 EventManager 并把事件转发到 listeners

设计要点：
1. 进程内单例：fastapi 应用内通过 `get_event_service()` 获取同一实例
2. 与 WebSocket ConnectionManager 解耦：listener 拿到的只是 (event_type, payload) 元组
3. 所有调用 try/except 保护，单个 listener 失败不影响其他
"""

from __future__ import annotations

import asyncio
import inspect
import sys
import threading
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def log_info(self, *args, **kwargs): pass
            def log_warn(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        return _Stub()

debug_logger = get_debug_logger()


# 类型别名：listener 签名 (event_type: str, payload: dict) -> Awaitable[None] | None
ListenerCallback = Callable[[str, Dict[str, Any]], Optional[Awaitable[None]]]


class EventService:
    """
    事件服务（Web 后端侧）
    1. 维护 _listeners: Dict[channel, List[callback]]
    2. start() 后台订阅 EventManager 事件 → 转发到 listeners
    3. emit_event(event_type, payload) 可由 WebSocket handler 主动派发
    """

    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        # channel -> [callback]
        self._listeners: Dict[str, List[ListenerCallback]] = {}
        self._lock = threading.RLock()
        self._started: bool = False
        self._unsubscribers: List[Callable[[], None]] = []
        # 兜底队列：在 start() 之前调用 emit_event 时，把事件暂存；start 后批量 dispatch
        self._pending_events: List[Dict[str, Any]] = []
        # 事件循环引用（WebSocket 在 fastapi 事件循环中运行）
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # 单例
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "EventService":
        with cls._instance_lock:
            if not hasattr(cls, "_instance") or cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ------------------------------------------------------------------
    # 注册监听器
    # ------------------------------------------------------------------
    def register_websocket_listener(
        self,
        channel: str,
        callback: ListenerCallback,
    ) -> Callable[[], None]:
        """
        注册一个 WebSocket listener 到指定 channel。
        - channel: 事件类型字符串（'*' 表示通配）
        - callback: 同步或 async 函数，签名 (event_type, payload) -> None
        返回 unsubscribe 函数，调用后移除该 listener。
        """
        if not channel:
            channel = '*'
        if not callable(callback):
            raise TypeError("callback must be callable")

        with self._lock:
            self._listeners.setdefault(str(channel), []).append(callback)

        def _unregister() -> None:
            self.unregister_websocket_listener(channel, callback)

        return _unregister

    def unregister_websocket_listener(
        self,
        channel: str,
        callback: ListenerCallback,
    ) -> bool:
        """注销 listener。"""
        key = str(channel or '*')
        with self._lock:
            listeners = self._listeners.get(key)
            if not listeners:
                return False
            try:
                listeners.remove(callback)
            except ValueError:
                return False
            if not listeners:
                self._listeners.pop(key, None)
            return True

    def listener_count(self, channel: Optional[str] = None) -> int:
        """查询 listener 数量（测试 / 健康检查用）。"""
        with self._lock:
            if channel is None:
                return sum(len(v) for v in self._listeners.values())
            return len(self._listeners.get(str(channel), []))

    # ------------------------------------------------------------------
    # 事件派发
    # ------------------------------------------------------------------
    def emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        触发事件：找到匹配 channel 的所有 listener，异步派发。
        - 服务未 start 时，事件会暂存在 _pending_events 中；start() 后批量回放
        - 单个 listener 抛错不会影响其他
        """
        try:
            event_type = str(event_type or 'message')
            payload_dict: Dict[str, Any] = dict(payload or {})

            with self._lock:
                matched = list(self._listeners.get(event_type, [])) + \
                          list(self._listeners.get('*', []))

            if not matched:
                # 未启动或暂无订阅：暂存到 pending（仅保留最近 200 条，避免内存膨胀）
                if not self._started:
                    with self._lock:
                        self._pending_events.append({
                            'event_type': event_type,
                            'payload': payload_dict,
                        })
                        if len(self._pending_events) > 200:
                            self._pending_events = self._pending_events[-200:]
                return

            self._dispatch_to_listeners(event_type, payload_dict, matched)
        except Exception as e:  # noqa: BLE001
            try:
                debug_logger.log_error('EventService', f'emit_event 失败: {e}', e)
            except Exception:
                pass

    def _dispatch_to_listeners(
        self,
        event_type: str,
        payload: Dict[str, Any],
        listeners: List[ListenerCallback],
    ) -> None:
        """把事件分发到 listeners，sync/async 兼容。"""
        for cb in listeners:
            try:
                if inspect.iscoroutinefunction(cb):
                    # 尝试调度到事件循环
                    scheduled = self._schedule_coroutine(cb, event_type, payload)
                    if not scheduled:
                        # 没有事件循环时降级为同步执行（用 asyncio.run）
                        try:
                            asyncio.run(cb(event_type, payload))
                        except Exception as inner:  # noqa: BLE001
                            self._safe_log_error('EventService',
                                                 f'async listener 执行失败: {inner}', inner)
                else:
                    cb(event_type, payload)
            except Exception as e:  # noqa: BLE001
                self._safe_log_error('EventService',
                                     f'listener 执行失败({event_type}): {e}', e)

    def _schedule_coroutine(
        self,
        cb: ListenerCallback,
        event_type: str,
        payload: Dict[str, Any],
    ) -> bool:
        """在已知事件循环上调度协程；返回是否成功调度。"""
        try:
            loop = self._loop
            if loop is None:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
            if loop is not None and loop.is_running():
                loop.create_task(cb(event_type, payload))
                return True
        except Exception as e:  # noqa: BLE001
            self._safe_log_error('EventService',
                                 f'调度协程失败({event_type}): {e}', e)
        return False

    # ------------------------------------------------------------------
    # 启动 / 关闭
    # ------------------------------------------------------------------
    def start(self, event_manager: Any = None) -> bool:
        """
        启动后台任务，订阅 EventManager 并把事件转发到 listeners。
        - 可重复调用；多次调用幂等。
        - 启动后会回放 _pending_events 中的事件。
        """
        if self._started:
            return True

        try:
            # 记录事件循环引用（WebSocket 在同一循环中运行）
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = None

            em = event_manager
            if em is None:
                try:
                    from src.core.event_manager import get_event_manager
                    em = get_event_manager()
                except Exception as e:  # noqa: BLE001
                    self._safe_log_error('EventService',
                                         f'获取 EventManager 失败: {e}', e)
                    em = None

            if em is not None and hasattr(em, 'subscribe'):
                # 订阅常见事件类型 + 通配
                event_types = [
                    'scheduler_tick',
                    'proactive_message',
                    'chat_event',
                    'debug_log',
                    'message',
                ]
                for et in event_types:
                    try:
                        unsub = em.subscribe(et, self._on_manager_event)
                        if unsub is not None and callable(unsub):
                            self._unsubscribers.append(unsub)
                    except Exception as e:  # noqa: BLE001
                        self._safe_log_error('EventService',
                                             f'订阅 {et} 失败: {e}', e)
                # 通配订阅
                try:
                    unsub = em.subscribe('*', self._on_manager_event)
                    if unsub is not None and callable(unsub):
                        self._unsubscribers.append(unsub)
                except Exception as e:  # noqa: BLE001
                    self._safe_log_error('EventService',
                                         f'订阅通配失败: {e}', e)

            self._started = True
            try:
                debug_logger.log_info('EventService', '事件服务已启动', {
                    'listeners': self.listener_count(),
                })
            except Exception:
                pass

            # 回放 pending 事件
            with self._lock:
                pending = list(self._pending_events)
                self._pending_events.clear()
            for item in pending:
                try:
                    self.emit_event(item.get('event_type', 'message'),
                                    item.get('payload', {}))
                except Exception as e:  # noqa: BLE001
                    self._safe_log_error('EventService',
                                         f'回放 pending 失败: {e}', e)
            return True
        except Exception as e:  # noqa: BLE001
            self._safe_log_error('EventService', f'start 失败: {e}', e)
            return False

    def stop(self) -> None:
        """停止服务（清理订阅、保留 listeners 以便再次 start）。"""
        try:
            for unsub in list(self._unsubscribers):
                try:
                    unsub()
                except Exception:
                    pass
            self._unsubscribers.clear()
            self._started = False
            try:
                debug_logger.log_info('EventService', '事件服务已停止')
            except Exception:
                pass
        except Exception as e:  # noqa: BLE001
            self._safe_log_error('EventService', f'stop 失败: {e}', e)

    # ------------------------------------------------------------------
    # EventManager → EventService 桥接
    # ------------------------------------------------------------------
    def _on_manager_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        由 EventManager.subscribe 注册的回调。
        把事件转发给本服务的所有匹配 listener。
        """
        try:
            # 复用 emit_event 逻辑
            self.emit_event(event_type, payload)
        except Exception as e:  # noqa: BLE001
            self._safe_log_error('EventService',
                                 f'EventManager 事件转发失败: {e}', e)

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    def _safe_log_error(self, module: str, msg: str, exc: Any = None) -> None:
        try:
            debug_logger.log_error(module, msg, exc)
        except Exception:
            pass


# 全局单例（直接调用 get_event_service() 即可）
_event_service: Optional[EventService] = None
_event_service_lock = threading.Lock()


def get_event_service() -> EventService:
    """获取全局 EventService 单例。"""
    global _event_service
    with _event_service_lock:
        if _event_service is None:
            _event_service = EventService()
        return _event_service


# Stage A.3: 直接可导入的模块级单例别名（与 get_event_service() 共享同一实例）
# 兼容 services/__init__.py 中的 `from .event_service import event_service` 用法。
event_service: EventService = get_event_service()


__all__ = ["EventService", "get_event_service", "event_service", "ListenerCallback"]
