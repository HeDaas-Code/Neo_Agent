"""
BaseModule - 所有认知功能模块的抽象基类。

每个模块（大脑皮层、海马体、杏仁核等）都必须继承此类，
并通过 CentralRouter 进行通信，而不是直接调用其他模块的方法。
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from src.nervous_system.router.central_router import CentralRouter
    from src.nervous_system.router.packet import Packet


class BaseModule(ABC):
    """
    功能模块基类。

    子类必须实现：
    - module_id: 模块唯一标识，如 "cortex.llm_core"
    - module_type: 模块类型，如 "cortex" / "limbic" / "prefrontal"
    - initialize / shutdown / handle
    """

    module_id: str = "base"
    module_type: str = "base"

    def __init__(self, router: "CentralRouter") -> None:
        self.router = router
        self._initialized = False

    async def initialize(self) -> None:
        """
        异步初始化。子类可重写以加载模型、连接数据库等。
        """
        self._initialized = True

    async def shutdown(self) -> None:
        """
        异步关闭。子类可重写以释放资源。
        """
        self._initialized = False

    @abstractmethod
    async def handle(self, packet: "Packet") -> "Packet":
        """
        处理来自 CentralRouter 的 Packet，返回响应 Packet。
        """
        ...

    async def emit(self, channel: str, payload: Dict[str, Any]) -> None:
        """
        向事件总线发布事件。
        """
        from src.nervous_system.router.packet import Packet, PacketType

        packet = Packet(
            trace_id=uuid.uuid4().hex,
            source=self.module_id,
            target="",
            packet_type=PacketType.EVENT,
            channel=channel,
            payload=payload,
        )
        await self.router.publish(packet)

    async def request(
        self,
        target: str,
        channel: str,
        payload: Dict[str, Any],
        metadata: Dict[str, Any] | None = None,
    ) -> "Packet":
        """
        向目标模块发送请求并等待响应。
        """
        from src.nervous_system.router.packet import Packet, PacketType

        packet = Packet(
            trace_id=uuid.uuid4().hex,
            source=self.module_id,
            target=target,
            packet_type=PacketType.REQUEST,
            channel=channel,
            payload=payload,
            metadata=metadata or {},
        )
        return await self.router.route(packet)
