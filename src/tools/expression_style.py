"""
v3.1.0 兼容层：src.tools.expression_style

原实现已迁移至 src.cerebellum.style.expression_style。
此文件保留旧导入路径，确保现有代码不受影响。
"""

from src.cerebellum.style.expression_style import ExpressionStyleManager

__all__ = ["ExpressionStyleManager"]
