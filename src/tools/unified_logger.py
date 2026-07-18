"""
Unified Logger - 统一日志模块

标准化日志的格式、级别与输出位置，支持后端与前端日志的统一收集。

设计要点：
- 统一字段：timestamp, level, module, message, source, trace_id, extra
- 统一级别：DEBUG, INFO, WARN, ERROR, FATAL
- Handler 机制：文件、内存缓冲、WebSocket 广播、外部转发器（预留）
- 线程安全，支持同步调用
- 自身错误通过 print 降级，避免循环日志
"""

from __future__ import annotations

import json
import threading
import traceback
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Dict, List, Optional, Protocol


class LogLevel(str, Enum):
    """标准日志级别。"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


@dataclass
class LogEntry:
    """标准日志条目。"""

    timestamp: str
    level: str
    module: str
    message: str
    source: str = "backend"
    trace_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("extra") is None:
            d.pop("extra", None)
        if d.get("trace_id") is None:
            d.pop("trace_id", None)
        return d


class LogHandler(Protocol):
    """日志处理器协议。"""

    def emit(self, entry: LogEntry) -> None:
        ...

    def close(self) -> None:
        ...


class FileHandler:
    """
    文件日志处理器。

    使用 RotatingFileHandler 按大小滚动，默认单个文件 10MB，保留 5 个备份。
    """

    def __init__(
        self,
        log_file: str = "debug.log",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ):
        self.log_file = log_file
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._lock = threading.Lock()
        self._handler: Optional[RotatingFileHandler] = None
        self._ensure_handler()

    def _ensure_handler(self) -> None:
        if self._handler is not None:
            return
        try:
            self._handler = RotatingFileHandler(
                self.log_file,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            self._handler.setFormatter(
                self._formatter()
            )
        except Exception as e:
            print(f"[UnifiedLogger.FileHandler] 初始化失败: {e}")

    @staticmethod
    def _formatter() -> Any:
        """返回标准文本格式。"""
        from logging import Formatter
        return Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    def emit(self, entry: LogEntry) -> None:
        if self._handler is None:
            return
        try:
            # 模拟 logging.LogRecord
            from logging import LogRecord, getLogger
            logger = getLogger(entry.module)
            record = LogRecord(
                name=entry.module,
                level=self._level_to_logging(entry.level),
                pathname="",
                lineno=0,
                msg=self._format_message(entry),
                args=(),
                exc_info=None,
            )
            record.created = datetime.fromisoformat(entry.timestamp).timestamp()
            with self._lock:
                self._handler.emit(record)
                self._handler.flush()
        except Exception as e:
            print(f"[UnifiedLogger.FileHandler] 写入失败: {e}")

    def _format_message(self, entry: LogEntry) -> str:
        lines = [entry.message]
        if entry.source:
            lines.append(f"  source: {entry.source}")
        if entry.trace_id:
            lines.append(f"  trace_id: {entry.trace_id}")
        if entry.extra:
            try:
                extra_str = json.dumps(entry.extra, ensure_ascii=False, indent=2)
                lines.append(f"  extra: {extra_str}")
            except Exception:
                lines.append(f"  extra: {str(entry.extra)}")
        return "\n".join(lines)

    @staticmethod
    def _level_to_logging(level: str) -> int:
        from logging import DEBUG, ERROR, FATAL, INFO, WARN
        mapping = {
            "DEBUG": DEBUG,
            "INFO": INFO,
            "WARN": WARN,
            "ERROR": ERROR,
            "FATAL": FATAL,
        }
        return mapping.get(level.upper(), INFO)

    def close(self) -> None:
        if self._handler is not None:
            try:
                self._handler.close()
            except Exception:
                pass
            self._handler = None


class MemoryBufferHandler:
    """
    内存缓冲处理器。

    使用双端队列保存最近 N 条日志，供 REST API 查询。
    """

    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self._buffer: deque = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def emit(self, entry: LogEntry) -> None:
        with self._lock:
            self._buffer.append(entry.to_dict())

    def get_buffer(
        self,
        module: Optional[str] = None,
        level: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 200,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._buffer)

        lvl = (level or "").strip().upper() or None
        mod = (module or "").strip() or None
        src = (source or "").strip() or None
        out: List[Dict[str, Any]] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            if lvl and str(item.get("level", "")).upper() != lvl:
                continue
            if mod and mod.lower() not in str(item.get("module", "")).lower():
                continue
            if src and str(item.get("source", "")).lower() != src.lower():
                continue
            ts = item.get("timestamp")
            if isinstance(ts, str):
                if start and ts < start:
                    continue
                if end and ts > end:
                    continue
            out.append(item)

        if len(out) > limit:
            out = out[-limit:]
        return out

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

    def close(self) -> None:
        self.clear()


class WebSocketBroadcastHandler:
    """
    WebSocket 广播处理器。

    将日志广播到 /ws/debug 的订阅者。通过 ConnectionManager 实现。
    由于 UnifiedLogger 是全局单例，而 ConnectionManager 在 Web 启动后才可用，
    因此采用延迟绑定：启动时调用 set_broadcast_callback() 注入回调。
    """

    def __init__(self):
        self._broadcast: Optional[Callable[[str, Dict[str, Any]], Any]] = None
        self._lock = threading.Lock()

    def set_broadcast_callback(
        self, callback: Callable[[str, Dict[str, Any]], Any]
    ) -> None:
        with self._lock:
            self._broadcast = callback

    def emit(self, entry: LogEntry) -> None:
        with self._lock:
            broadcast = self._broadcast
        if broadcast is None:
            return
        try:
            broadcast("debug", {"type": "log", "entry": entry.to_dict()})
        except Exception as e:
            print(f"[UnifiedLogger.WebSocketBroadcastHandler] 广播失败: {e}")

    def close(self) -> None:
        with self._lock:
            self._broadcast = None


class ExternalForwarderHandler:
    """
    外部日志服务转发器（预留）。

    通过环境变量 UNIFIED_LOGGER_FORWARDER_URL 配置外部 HTTP endpoint，
    批量转发日志。当前版本仅保存 URL 与阈值，未来可实现异步发送。
    """

    def __init__(self, endpoint: Optional[str] = None, batch_size: int = 100):
        self.endpoint = endpoint
        self.batch_size = batch_size
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def emit(self, entry: LogEntry) -> None:
        if not self.endpoint:
            return
        with self._lock:
            self._buffer.append(entry.to_dict())
            if len(self._buffer) >= self.batch_size:
                self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        # 异步发送由未来版本实现；当前避免阻塞主流程
        threading.Thread(target=self._send, args=(batch,), daemon=True).start()

    def _send(self, batch: List[Dict[str, Any]]) -> None:
        try:
            import urllib.request
            body = json.dumps({"logs": batch}, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                self.endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            print(f"[UnifiedLogger.ExternalForwarderHandler] 转发失败: {e}")

    def close(self) -> None:
        with self._lock:
            self._flush_locked()


class UnifiedLogger:
    """
    统一日志记录器。

    提供标准字段、标准级别、多 Handler 输出的日志服务。
    支持后端与前端的日志统一收集。
    """

    def __init__(
        self,
        log_file: str = "debug.log",
        debug_mode: bool = False,
        memory_size: int = 5000,
    ):
        self.debug_mode = debug_mode
        self._handlers: List[LogHandler] = []
        self._lock = threading.Lock()

        # 默认 Handler
        self._file_handler = FileHandler(log_file=log_file)
        self._memory_handler = MemoryBufferHandler(max_size=memory_size)
        self._ws_handler = WebSocketBroadcastHandler()

        self.add_handler(self._file_handler)
        self.add_handler(self._memory_handler)
        self.add_handler(self._ws_handler)

        # 外部转发器：仅当环境变量存在时启用
        import os
        forwarder_url = os.getenv("UNIFIED_LOGGER_FORWARDER_URL")
        if forwarder_url:
            self._forwarder = ExternalForwarderHandler(endpoint=forwarder_url)
            self.add_handler(self._forwarder)
        else:
            self._forwarder = None

    def add_handler(self, handler: LogHandler) -> None:
        with self._lock:
            self._handlers.append(handler)

    def remove_handler(self, handler: LogHandler) -> None:
        with self._lock:
            try:
                self._handlers.remove(handler)
            except ValueError:
                pass

    def set_websocket_broadcast(
        self, callback: Callable[[str, Dict[str, Any]], Any]
    ) -> None:
        """注入 WebSocket 广播回调。"""
        self._ws_handler.set_broadcast_callback(callback)

    def log(
        self,
        level: str,
        module: str,
        message: str,
        source: str = "backend",
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        记录一条标准日志。

        Args:
            level: 日志级别 DEBUG/INFO/WARN/ERROR/FATAL
            module: 模块名
            message: 日志消息
            source: 来源 backend/frontend
            trace_id: 可选追踪 ID
            extra: 可选结构化附加数据
        """
        try:
            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                level=self._normalize_level(level),
                module=module or "app",
                message=str(message) if message is not None else "",
                source=source or "backend",
                trace_id=trace_id,
                extra=extra,
            )

            # DEBUG 级别在 debug_mode=False 时是否输出？
            # 统一日志默认始终记录 INFO 及以上；DEBUG 仅在 debug_mode=True 时记录
            if entry.level == LogLevel.DEBUG.value and not self.debug_mode:
                return

            with self._lock:
                handlers = list(self._handlers)

            for handler in handlers:
                try:
                    handler.emit(entry)
                except Exception as e:
                    print(f"[UnifiedLogger] Handler 失败 ({type(handler).__name__}): {e}")
        except Exception as e:
            # 自身错误不得再调用自己，避免死循环
            print(f"[UnifiedLogger] 记录日志失败: {e}")
            traceback.print_exc()

    def debug(
        self,
        module: str,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        source: str = "backend",
    ) -> None:
        self.log(LogLevel.DEBUG.value, module, message, source, trace_id, extra)

    def info(
        self,
        module: str,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        source: str = "backend",
    ) -> None:
        self.log(LogLevel.INFO.value, module, message, source, trace_id, extra)

    def warn(
        self,
        module: str,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        source: str = "backend",
    ) -> None:
        self.log(LogLevel.WARN.value, module, message, source, trace_id, extra)

    def error(
        self,
        module: str,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        source: str = "backend",
    ) -> None:
        self.log(LogLevel.ERROR.value, module, message, source, trace_id, extra)

    def fatal(
        self,
        module: str,
        message: str,
        trace_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
        source: str = "backend",
    ) -> None:
        self.log(LogLevel.FATAL.value, module, message, source, trace_id, extra)

    def get_buffer(
        self,
        module: Optional[str] = None,
        level: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 200,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return self._memory_handler.get_buffer(module, level, start, end, limit, source)

    def clear_buffer(self) -> None:
        self._memory_handler.clear()

    def get_statistics(self) -> Dict[str, Any]:
        buffer = self.get_buffer(limit=10000)
        by_level: Dict[str, int] = {}
        by_source: Dict[str, int] = {}
        for item in buffer:
            lvl = str(item.get("level", "UNKNOWN")).upper()
            src = str(item.get("source", "backend")).upper()
            by_level[lvl] = by_level.get(lvl, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1
        return {
            "total_logs": len(buffer),
            "by_level": by_level,
            "by_source": by_source,
            "debug_mode": self.debug_mode,
            "log_file": getattr(self._file_handler, "log_file", "debug.log"),
        }

    @staticmethod
    def _normalize_level(level: str) -> str:
        mapping = {
            "debug": "DEBUG",
            "info": "INFO",
            "warn": "WARN",
            "warning": "WARN",
            "error": "ERROR",
            "fatal": "FATAL",
            "critical": "FATAL",
        }
        return mapping.get(str(level).lower(), str(level).upper())

    def close(self) -> None:
        with self._lock:
            handlers = list(self._handlers)
            self._handlers.clear()
        for handler in handlers:
            try:
                handler.close()
            except Exception:
                pass


# =====================================================================
# 全局单例
# =====================================================================
_unified_logger_instance: Optional[UnifiedLogger] = None
_unified_logger_lock = threading.Lock()


def get_unified_logger(
    log_file: str = "debug.log",
    debug_mode: bool = False,
    reset: bool = False,
) -> UnifiedLogger:
    """获取全局 UnifiedLogger 单例。"""
    global _unified_logger_instance
    with _unified_logger_lock:
        if _unified_logger_instance is None or reset:
            _unified_logger_instance = UnifiedLogger(
                log_file=log_file,
                debug_mode=debug_mode,
            )
        return _unified_logger_instance
