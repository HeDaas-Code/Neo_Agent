"""
Packet - 神经系统数据包

所有内部模块间通信的基本单元，类似神经系统中的动作电位信号。
每个 Packet 携带 trace_id，支持全链路追踪。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class PacketType(Enum):
    """数据包类型。"""

    REQUEST = "request"      # 同步/异步请求
    EVENT = "event"          # 事件发布（广播）
    RESPONSE = "response"    # 请求响应
    ERROR = "error"          # 错误响应


class Priority(Enum):
    """数据包优先级。"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Packet:
    """
    神经系统数据包。

    Attributes:
        trace_id: 全链路追踪 ID，同一个用户请求的所有 Packet 共享。
        source: 来源模块 ID，如 "cortex.llm_core"。
        target: 目标模块 ID（EVENT 类型可为空字符串）。
        packet_type: 数据包类型。
        channel: 业务通道，如 "chat" / "memory" / "emotion" / "schedule"。
        payload: 业务数据字典。
        metadata: 元数据，用于中间件传递上下文（user_id、权限等）。
        priority: 优先级。
        timestamp: 创建时间戳（秒级浮点数）。
    """

    source: str
    target: str
    packet_type: PacketType
    channel: str
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    priority: Priority = Priority.NORMAL
    timestamp: float = field(default_factory=time.time)

    @staticmethod
    def error(origin: Packet, message: str, code: str = "INTERNAL_ERROR") -> Packet:
        """
        基于原始 Packet 生成错误响应包。
        """
        return Packet(
            trace_id=origin.trace_id,
            source="nervous_system.router",
            target=origin.source,
            packet_type=PacketType.ERROR,
            channel=origin.channel,
            payload={"error": message, "code": code, "original_target": origin.target},
            metadata=origin.metadata,
        )

    def is_request(self) -> bool:
        return self.packet_type == PacketType.REQUEST

    def is_event(self) -> bool:
        return self.packet_type == PacketType.EVENT

    def is_response(self) -> bool:
        return self.packet_type == PacketType.RESPONSE

    def is_error(self) -> bool:
        return self.packet_type == PacketType.ERROR

    def response(self, payload: Dict[str, Any]) -> Packet:
        """
        基于当前请求包构造响应包。
        """
        return Packet(
            trace_id=self.trace_id,
            source=self.target,
            target=self.source,
            packet_type=PacketType.RESPONSE,
            channel=self.channel,
            payload=payload,
            metadata=self.metadata,
        )
