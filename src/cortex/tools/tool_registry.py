"""
ToolRegistry - v4.0 工具注册表。

为 LLMCore 提供可插拔的工具调用能力：
- 注册/查询 LangChain 兼容工具
- 列出可用工具元数据
- 提供默认工具（系统时间等）
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.tools import BaseTool, tool


class ToolRegistry:
    """
    工具注册表。

    管理 LangChain BaseTool 实例，并提供按名称查询、列表导出能力。
    """

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool_instance: BaseTool) -> None:
        """
        注册一个工具。
        """
        self._tools[tool_instance.name] = tool_instance

    def get(self, name: str) -> Optional[BaseTool]:
        """
        按名称获取工具。
        """
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        返回可用工具元数据列表，供 LLM 工具选择使用。
        """
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def get_tools(self) -> List[BaseTool]:
        """
        返回所有已注册工具实例。
        """
        return list(self._tools.values())


def _create_system_time_tool() -> BaseTool:
    """
    创建默认系统时间工具。
    """
    @tool
    def system_time() -> str:
        """
        获取当前系统时间、日期、星期等信息。

        适用场景：回答“现在几点”、“今天星期几”等时间相关问题。
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S %A")
    return system_time


def create_default_tool_registry() -> ToolRegistry:
    """
    创建默认工具注册表。

    默认包含：
    - system_time: 获取当前系统时间
    """
    registry = ToolRegistry()
    registry.register(_create_system_time_tool())
    return registry


__all__ = ["ToolRegistry", "create_default_tool_registry"]
