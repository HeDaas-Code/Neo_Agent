"""
v3.1.0 兼容层：src.tools.interrupt_question_tool

原实现已迁移至 src.cerebellum.interrupt.interrupt_question_tool。
此文件保留旧导入路径，确保现有代码不受影响。
"""

from src.cerebellum.interrupt.interrupt_question_tool import InterruptQuestionTool

__all__ = ["InterruptQuestionTool"]
