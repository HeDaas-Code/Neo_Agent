"""
BaseGateway - 所有外部网关的抽象基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class GatewayRequest:
    """
    网关统一请求格式。
    """

    method: str                          # GET / POST / WS_MESSAGE 等
    path: str                            # 请求路径
    headers: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)  # user_id, trace_id 等


@dataclass
class GatewayResponse:
    """
    网关统一响应格式。
    """

    status_code: int
    body: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)


class BaseGateway(ABC):
    """
    外部网关基类。所有外部交互（HTTP/WebSocket/LLM/Storage）都必须通过网关实现。
    """

    gateway_id: str = "base"

    @abstractmethod
    async def start(self) -> None:
        """启动网关。"""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """停止网关。"""
        ...

    @abstractmethod
    async def handle(self, request: GatewayRequest) -> GatewayResponse:
        """处理一个请求。"""
        ...
