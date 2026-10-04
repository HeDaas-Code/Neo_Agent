"""命令面板系统"""
from typing import Dict, Callable, Any, Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input, Button, Label, Switch
from textual.screen import ModalScreen
from textual import on


class CommandPalette(ModalScreen):
    """命令面板（模态窗口）"""
    
    BINDINGS = [
        ("escape", "dismiss", "取消"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.command_history = []
    
    def compose(self) -> ComposeResult:
        with Vertical(id="command-container"):
            yield Static("命令面板", id="command-title")
            yield Input(placeholder="输入命令... (例如: config, debug on, export character)", 
                       id="command-input", 
                       classes="command-input")
            yield Static("", id="command-hint", classes="command-hint")
            with Horizontal(id="command-buttons"):
                yield Button("执行", variant="primary", id="execute-command")
                yield Button("取消", id="cancel-command")
    
    @on(Input.Changed, "#command-input")
    def on_input_changed(self, event: Input.Changed):
        """输入变化时显示提示"""
        cmd = event.value.strip().lower()
        hint_widget = self.query_one("#command-hint", Static)
        
        if not cmd:
            hint_widget.update("[dim]可用命令: config, debug, export, import[/dim]")
        elif cmd.startswith("config"):
            hint_widget.update("[dim]打开全局配置面板[/dim]")
        elif cmd.startswith("debug"):
            hint_widget.update("[dim]用法: debug on | debug off[/dim]")
        elif cmd.startswith("export"):
            hint_widget.update("[dim]用法: export character | export all[/dim]")
        elif cmd.startswith("import"):
            hint_widget.update("[dim]用法: import <文件路径>[/dim]")
        else:
            hint_widget.update("[yellow]未知命令[/yellow]")
    
    @on(Input.Submitted, "#command-input")
    async def on_input_submitted(self, event: Input.Submitted):
        """回车执行命令"""
        await self.execute_command()
    
    @on(Button.Pressed, "#execute-command")
    async def on_execute_pressed(self, event: Button.Pressed):
        """执行按钮点击"""
        await self.execute_command()
    
    @on(Button.Pressed, "#cancel-command")
    def on_cancel_pressed(self, event: Button.Pressed):
        """取消按钮点击"""
        self.dismiss(None)
    
    async def execute_command(self):
        """解析并执行命令"""
        input_widget = self.query_one("#command-input", Input)
        cmd = input_widget.value.strip()
        
        if not cmd:
            return
        
        # 添加到历史
        self.command_history.append(cmd)
        
        # 解析命令
        parts = cmd.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # 返回命令和参数给调用者
        self.dismiss({"command": command, "args": args})


class ConfigPanel(ModalScreen):
    """全局配置面板"""
    
    BINDINGS = [
        ("escape", "dismiss", "取消"),
    ]
    
    def __init__(self, current_config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.current_config = current_config
    
    def compose(self) -> ComposeResult:
        with Vertical(id="config-container"):
            yield Static("全局配置", id="config-title")
            
            # LLM 模型配置
            yield Label("LLM 模型:")
            yield Input(
                value=self.current_config.get("llm_model", "gpt-4"),
                id="config-llm-model",
                placeholder="例如: gpt-4, gpt-3.5-turbo"
            )
            
            # PyVDisk 路径
            yield Label("PyVDisk 数据目录:")
            yield Input(
                value=self.current_config.get("pyvdisk_path", "~/.neo_agent/data"),
                id="config-pyvdisk-path",
                placeholder="数据存储路径"
            )
            
            # 时区
            yield Label("时区:")
            yield Input(
                value=self.current_config.get("timezone", "Asia/Shanghai"),
                id="config-timezone",
                placeholder="例如: Asia/Shanghai, UTC"
            )
            
            # Debug 模式
            with Horizontal(classes="config-row"):
                yield Label("Debug 模式:")
                yield Switch(
                    value=self.current_config.get("debug_mode", False),
                    id="config-debug-switch"
                )
            
            # 按钮
            with Horizontal(id="config-buttons"):
                yield Button("保存", variant="primary", id="save-config")
                yield Button("取消", id="cancel-config")
    
    @on(Button.Pressed, "#save-config")
    async def on_save_pressed(self, event: Button.Pressed):
        """保存配置"""
        new_config = {
            "llm_model": self.query_one("#config-llm-model", Input).value,
            "pyvdisk_path": self.query_one("#config-pyvdisk-path", Input).value,
            "timezone": self.query_one("#config-timezone", Input).value,
            "debug_mode": self.query_one("#config-debug-switch", Switch).value,
        }
        self.dismiss(new_config)
    
    @on(Button.Pressed, "#cancel-config")
    def on_cancel_pressed(self, event: Button.Pressed):
        """取消"""
        self.dismiss(None)


class ExportPanel(ModalScreen):
    """导出数据面板"""
    
    BINDINGS = [
        ("escape", "dismiss", "取消"),
    ]
    
    def __init__(self, export_type: str = "character", **kwargs):
        super().__init__(**kwargs)
        self.export_type = export_type
    
    def compose(self) -> ComposeResult:
        with Vertical(id="export-container"):
            yield Static(f"导出 {self.export_type}", id="export-title")
            
            yield Label("导出路径:")
            yield Input(
                value=f"~/neo_agent_export_{self.export_type}.json",
                id="export-path",
                placeholder="保存文件路径"
            )
            
            yield Static("", id="export-status", classes="status-message")
            
            with Horizontal(id="export-buttons"):
                yield Button("导出", variant="primary", id="start-export")
                yield Button("取消", id="cancel-export")
    
    @on(Button.Pressed, "#start-export")
    async def on_start_export(self, event: Button.Pressed):
        """开始导出"""
        path = self.query_one("#export-path", Input).value
        self.dismiss({"type": self.export_type, "path": path})
    
    @on(Button.Pressed, "#cancel-export")
    def on_cancel_pressed(self, event: Button.Pressed):
        """取消"""
        self.dismiss(None)


class ImportPanel(ModalScreen):
    """导入数据面板"""
    
    BINDINGS = [
        ("escape", "dismiss", "取消"),
    ]
    
    def compose(self) -> ComposeResult:
        with Vertical(id="import-container"):
            yield Static("导入数据", id="import-title")
            
            yield Label("导入文件路径:")
            yield Input(
                placeholder="例如: ~/character_backup.json",
                id="import-path"
            )
            
            yield Static("", id="import-status", classes="status-message")
            
            with Horizontal(id="import-buttons"):
                yield Button("导入", variant="primary", id="start-import")
                yield Button("取消", id="cancel-import")
    
    @on(Button.Pressed, "#start-import")
    async def on_start_import(self, event: Button.Pressed):
        """开始导入"""
        path = self.query_one("#import-path", Input).value
        if not path.strip():
            status = self.query_one("#import-status", Static)
            status.update("[red]请输入文件路径[/red]")
            return
        self.dismiss({"path": path})
    
    @on(Button.Pressed, "#cancel-import")
    def on_cancel_pressed(self, event: Button.Pressed):
        """取消"""
        self.dismiss(None)


# 命令面板的 CSS 样式
COMMAND_PANEL_CSS = """
/* ============ 命令面板 ============ */
CommandPalette {
    align: center middle;
}

#command-container {
    width: 60;
    height: auto;
    background: $surface-1;
    border: solid $accent-primary;
    padding: 2;
}

#command-title {
    text-align: center;
    text-style: bold;
    color: $accent-primary;
    height: 1;
    margin-bottom: 1;
}

.command-input {
    width: 100%;
    height: 3;
    margin-bottom: 1;
}

.command-hint {
    height: 2;
    margin-bottom: 1;
    text-align: center;
}

#command-buttons {
    height: 3;
    align: center middle;
}

#command-buttons Button {
    margin: 0 1;
}

/* ============ 配置面板 ============ */
ConfigPanel {
    align: center middle;
}

#config-container {
    width: 70;
    height: auto;
    background: $surface-1;
    border: solid $accent-primary;
    padding: 2;
}

#config-title {
    text-align: center;
    text-style: bold;
    color: $accent-primary;
    height: 1;
    margin-bottom: 2;
}

.config-row {
    height: 3;
    margin-bottom: 1;
}

.config-row Label {
    width: 20;
}

#config-buttons {
    height: 3;
    align: center middle;
    margin-top: 2;
}

#config-buttons Button {
    margin: 0 1;
}

/* ============ 导出/导入面板 ============ */
ExportPanel, ImportPanel {
    align: center middle;
}

#export-container, #import-container {
    width: 60;
    height: auto;
    background: $surface-1;
    border: solid $accent-primary;
    padding: 2;
}

#export-title, #import-title {
    text-align: center;
    text-style: bold;
    color: $accent-primary;
    height: 1;
    margin-bottom: 2;
}

.status-message {
    height: 2;
    text-align: center;
    margin-top: 1;
}

#export-buttons, #import-buttons {
    height: 3;
    align: center middle;
    margin-top: 2;
}

#export-buttons Button, #import-buttons Button {
    margin: 0 1;
}
"""
