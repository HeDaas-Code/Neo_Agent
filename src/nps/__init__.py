"""
NPS (Neo Plugin System) - 可拓展的智能体工具系统
用于拓展智能体的上下文信息，支持自动注册和调用工具模块
"""

from .nps_registry import NPSRegistry
from .nps_invoker import NPSInvoker

__all__ = ['NPSRegistry', 'NPSInvoker']
