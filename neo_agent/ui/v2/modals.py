"""TUI 模态窗口组件"""
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Input, Label, Switch
from textual.screen import ModalScreen


class ConfigModal(ModalScreen[dict | None]):
    """全局配置模态窗口"""
    
    CSS = """
    ConfigModal {
        align: center middle;
    }
    
    #config_dialog {
        width: 80;
        height: 30;
        background: $surface-1;
        border: solid $accent-primary;
        padding: 1 2;
    }
    
    .config_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    .config_section {
        height: auto;
        margin-bottom: 1;
    }
    
    .config_label {
        width: 20;
        color: $text-secondary;
    }
    
    .config_input {
        width: 1fr;
    }
    
    .button_bar {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    
    .button_bar Button {
        margin: 0 1;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Container(id="config_dialog"):
            yield Static("全局配置", classes="config_title")
            
            with Horizontal(classes="config_section"):
                yield Label("LLM 模型:", classes="config_label")
                yield Input(
                    placeholder="gpt-4o-mini",
                    id="llm_model",
                    classes="config_input"
                )
            
            with Horizontal(classes="config_section"):
                yield Label("PyVDisk 路径:", classes="config_label")
                yield Input(
                    placeholder="~/.neo_agent/vdisk",
                    id="vdisk_path",
                    classes="config_input"
                )
            
            with Horizontal(classes="config_section"):
                yield Label("时区:", classes="config_label")
                yield Input(
                    placeholder="Asia/Shanghai",
                    id="timezone",
                    classes="config_input"
                )
            
            with Horizontal(classes="config_section"):
                yield Label("Debug 模式:", classes="config_label")
                yield Switch(id="debug_switch")
            
            with Horizontal(classes="button_bar"):
                yield Button("保存", variant="primary", id="save_btn")
                yield Button("取消", variant="default", id="cancel_btn")
    
    def on_mount(self) -> None:
        """加载当前配置"""
        # TODO: 从配置文件加载
        self.query_one("#llm_model", Input).value = "gpt-4o-mini"
        self.query_one("#vdisk_path", Input).value = "~/.neo_agent/vdisk"
        self.query_one("#timezone", Input).value = "Asia/Shanghai"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_btn":
            config = {
                "llm_model": self.query_one("#llm_model", Input).value,
                "vdisk_path": self.query_one("#vdisk_path", Input).value,
                "timezone": self.query_one("#timezone", Input).value,
                "debug": self.query_one("#debug_switch", Switch).value
            }
            self.dismiss(config)
        else:
            self.dismiss(None)


class SceneDetailModal(ModalScreen[None]):
    """场景详情模态窗口"""
    
    CSS = """
    SceneDetailModal {
        align: center middle;
    }
    
    #scene_dialog {
        width: 90;
        height: 35;
        background: $surface-1;
        border: solid $accent-primary;
        padding: 1 2;
    }
    
    .scene_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    .scene_content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
        background: $surface-0;
        padding: 1;
        border: solid $surface-3;
    }
    
    .close_btn {
        width: 100%;
        align: center middle;
        margin-top: 1;
    }
    """
    
    def __init__(self, scene_data: dict):
        super().__init__()
        self.scene_data = scene_data
    
    def compose(self) -> ComposeResult:
        location = self.scene_data.get("location", "未知地点")
        description = self.scene_data.get("description", "暂无描述")
        areas = self.scene_data.get("areas", [])
        objects = self.scene_data.get("objects", [])
        
        content = f"""[bold]{location}[/bold]

描述：
{description}

区域：
"""
        for area in areas:
            content += f"  • {area}\n"
        
        content += "\n物体：\n"
        for obj in objects:
            content += f"  • {obj}\n"
        
        with Container(id="scene_dialog"):
            yield Static(f"场景详情 - {location}", classes="scene_title")
            yield Static(content, classes="scene_content")
            with Horizontal(classes="close_btn"):
                yield Button("关闭", variant="primary", id="close_btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class ItineraryDetailModal(ModalScreen[None]):
    """日程详情模态窗口"""
    
    CSS = """
    ItineraryDetailModal {
        align: center middle;
    }
    
    #itinerary_dialog {
        width: 80;
        height: 30;
        background: $surface-1;
        border: solid $accent-primary;
        padding: 1 2;
    }
    
    .itinerary_title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent-primary;
        margin-bottom: 1;
    }
    
    .itinerary_content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
        background: $surface-0;
        padding: 1;
        border: solid $surface-3;
    }
    
    .close_btn {
        width: 100%;
        align: center middle;
        margin-top: 1;
    }
    """
    
    def __init__(self, itinerary_data: dict):
        super().__init__()
        self.itinerary_data = itinerary_data
    
    def compose(self) -> ComposeResult:
        time = self.itinerary_data.get("time", "未知时间")
        activity = self.itinerary_data.get("activity", "未知活动")
        location = self.itinerary_data.get("location", "未知地点")
        owner = self.itinerary_data.get("owner", "agent")
        scene_id = self.itinerary_data.get("scene_id")
        
        owner_text = {
            "agent": "林依个人",
            "user": "用户个人",
            "shared": "共同活动"
        }.get(owner, owner)
        
        content = f"""[bold]{activity}[/bold]

时间：{time}
地点：{location}
归属：{owner_text}
场景绑定：{scene_id or '无'}
"""
        
        with Container(id="itinerary_dialog"):
            yield Static(f"日程详情", classes="itinerary_title")
            yield Static(content, classes="itinerary_content")
            with Horizontal(classes="close_btn"):
                yield Button("关闭", variant="primary", id="close_btn")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()


class CommandPalette(ModalScreen[str | None]):
    """命令面板（类 Vim 的 : 模式）"""
    
    CSS = """
    CommandPalette {
        align: center bottom;
    }
    
    #command_container {
        width: 100%;
        height: auto;
        background: $surface-2;
        border-top: solid $accent-primary;
        padding: 0 1;
    }
    
    #command_input {
        width: 100%;
        border: none;
        background: transparent;
    }
    """
    
    COMMANDS = {
        "config": "打开全局配置",
        "debug on": "开启调试模式",
        "debug off": "关闭调试模式",
        "export character": "导出角色数据",
        "export all": "导出全部数据",
        "import": "导入数据",
        "quit": "退出 TUI",
        "help": "显示帮助"
    }
    
    def compose(self) -> ComposeResult:
        with Container(id="command_container"):
            yield Input(
                placeholder="输入命令 (? 查看帮助, Esc 取消)",
                id="command_input"
            )
    
    def on_mount(self) -> None:
        self.query_one("#command_input", Input).focus()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        
        if not command:
            self.dismiss(None)
            return
        
        if command == "?":
            # 显示帮助
            help_text = "\n".join(f":{k} - {v}" for k, v in self.COMMANDS.items())
            self.app.notify(help_text, title="可用命令", timeout=10)
            self.dismiss(None)
        else:
            self.dismiss(command)
    
    def on_key(self, event) -> None:
        if event.key == "escape":
            self.dismiss(None)
