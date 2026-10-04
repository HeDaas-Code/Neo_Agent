"""将命令面板集成到主应用"""
import os

# 读取主应用文件
with open("neo_agent/ui/v2/app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

# 在导入部分添加命令面板导入
import_section = """from .client import AgentClient
from .theme import FULL_THEME"""

new_imports = """from .client import AgentClient
from .theme import FULL_THEME
from .commands import (
    CommandPalette, ConfigPanel, ExportPanel, ImportPanel,
    COMMAND_PANEL_CSS
)"""

app_content = app_content.replace(import_section, new_imports)

# 在 CSS 中添加命令面板样式
css_line = '    CSS = FULL_THEME'
new_css_line = '    CSS = FULL_THEME + COMMAND_PANEL_CSS'
app_content = app_content.replace(css_line, new_css_line)

# 在 action_command_mode 中添加命令面板逻辑
old_action = '''    async def action_command_mode(self):
        """命令模式（未实现）"""
        self.notify("命令模式开发中...", severity="information")'''

new_action = '''    async def action_command_mode(self):
        """打开命令面板"""
        result = await self.push_screen_wait(CommandPalette())
        if result:
            await self.handle_command(result)
    
    async def handle_command(self, cmd_data: dict):
        """处理命令"""
        command = cmd_data.get("command", "")
        args = cmd_data.get("args", [])
        
        if command == "config":
            await self.open_config_panel()
        
        elif command == "debug":
            if args and args[0] in ["on", "off"]:
                enabled = args[0] == "on"
                try:
                    await self.client.call("system.set_debug", {"enabled": enabled})
                    status = "开启" if enabled else "关闭"
                    self.notify(f"Debug 模式已{status}", severity="information")
                except Exception as e:
                    self.notify(f"设置失败: {e}", severity="error")
            else:
                self.notify("用法: debug on | debug off", severity="warning")
        
        elif command == "export":
            export_type = args[0] if args else "character"
            await self.open_export_panel(export_type)
        
        elif command == "import":
            if args:
                await self.import_data(args[0])
            else:
                await self.open_import_panel()
        
        else:
            self.notify(f"未知命令: {command}", severity="warning")
    
    async def open_config_panel(self):
        """打开配置面板"""
        try:
            # 获取当前配置
            current_config = await self.client.call("system.get_config", {})
        except Exception:
            current_config = {
                "llm_model": "gpt-4",
                "pyvdisk_path": "~/.neo_agent/data",
                "timezone": "Asia/Shanghai",
                "debug_mode": False
            }
        
        result = await self.push_screen_wait(ConfigPanel(current_config))
        if result:
            try:
                await self.client.call("system.update_config", result)
                self.notify("配置已保存", severity="information")
            except Exception as e:
                self.notify(f"保存失败: {e}", severity="error")
    
    async def open_export_panel(self, export_type: str):
        """打开导出面板"""
        result = await self.push_screen_wait(ExportPanel(export_type))
        if result:
            try:
                export_path = result["path"]
                export_type = result["type"]
                data = await self.client.call("system.export_data", {
                    "type": export_type,
                    "path": export_path
                })
                self.notify(f"导出成功: {export_path}", severity="information")
            except Exception as e:
                self.notify(f"导出失败: {e}", severity="error")
    
    async def open_import_panel(self):
        """打开导入面板"""
        result = await self.push_screen_wait(ImportPanel())
        if result:
            await self.import_data(result["path"])
    
    async def import_data(self, file_path: str):
        """导入数据"""
        try:
            await self.client.call("system.import_data", {"path": file_path})
            self.notify(f"导入成功: {file_path}", severity="information")
        except Exception as e:
            self.notify(f"导入失败: {e}", severity="error")'''

app_content = app_content.replace(old_action, new_action)

# 写回文件
with open("neo_agent/ui/v2/app.py", "w", encoding="utf-8") as f:
    f.write(app_content)

print("✓ 命令面板已集成到主应用")
