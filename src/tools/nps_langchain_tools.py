"""
v3.1.0 兼容层：src.tools.nps_langchain_tools

原实现已迁移至 src.cerebellum.nps.langchain_tools。
此文件保留旧导入路径，确保现有代码不受影响。
"""

from src.cerebellum.nps.langchain_tools import (
    NPSSystemTimeTool,
    NPSWebSearchTool,
    create_nps_tools,
)

__all__ = [
    "NPSSystemTimeTool",
    "NPSWebSearchTool",
    "create_nps_tools",
]
