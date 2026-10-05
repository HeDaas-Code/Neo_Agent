"""Neo Agent TUI v2 模块"""

from .app import NeoAgentTUI, run

# 兼容旧的导入名称
NeoAgentApp = NeoAgentTUI
run_tui = run

__all__ = ['NeoAgentTUI', 'NeoAgentApp', 'run', 'run_tui']
