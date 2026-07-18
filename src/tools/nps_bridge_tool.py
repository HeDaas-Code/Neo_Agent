"""
v3.1.0 兼容层：src.tools.nps_bridge_tool

原实现已迁移至 src.cerebellum.nps.bridge_tool。
此文件保留旧导入路径，确保现有代码不受影响。
"""

from src.cerebellum.nps.bridge_tool import NPSBridgeTool

__all__ = ["NPSBridgeTool"]
