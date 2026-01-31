"""
Neo Agent - GUI modules

图形界面模块包含所有GUI相关的组件
"""

from src.gui.gui_enhanced import EnhancedChatDebugGUI
from src.gui.database_gui import DatabaseGUI
from src.gui.nps_gui import NPSManagerGUI
from src.gui.schedule_gui import ScheduleGUI
from src.gui.settings_migration_gui import SettingsMigrationGUI

# Alias for compatibility
NeoAgentGUI = EnhancedChatDebugGUI

__all__ = [
    'EnhancedChatDebugGUI',
    'NeoAgentGUI',
    'DatabaseGUI',
    'NPSManagerGUI',
    'ScheduleGUI',
    'SettingsMigrationGUI',
]
