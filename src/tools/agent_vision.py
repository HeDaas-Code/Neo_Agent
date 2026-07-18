"""
v3.1.0 兼容层：src.tools.agent_vision

原实现已迁移至 src.cerebellum.vision.agent_vision。
此文件保留旧导入路径，确保现有代码不受影响。
"""

from src.cerebellum.vision.agent_vision import AgentVisionTool

__all__ = ["AgentVisionTool"]
