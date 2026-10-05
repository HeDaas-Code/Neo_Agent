"""Neo Agent TUI v2 - 服务客户端主应用"""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Button
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from datetime import datetime

from .views import (
    ChatView, ItineraryView, ScenePoolView,
    MemoryView, RelationshipView, AuditView
)
from .modals import ConfigModal, CommandPalette, SceneDetailModal, ItineraryDetailModal
from .client import ServiceClient
from .theme import AMBER_THEME


class ViewChangeRequested(Message):
    """视图切换请求消息"""
    def __init__(self, view_id: str):
        super().__init__()
        self.view_id = view_id


class Sidebar(VerticalScroll):
    """侧边栏容器"""
    
    def compose(self) -> ComposeResult:
        # 主要导航项
        yield Button("💬 对话", id="nav_chat", classes="nav_button active")
        yield Button("📅 今日行程", id="nav_itinerary", classes="nav_button")
        yield Button("🌍 场景池", id="nav_scenes", classes="nav_button")
        yield Button("🧠 记忆与知识", id="nav_memory", classes="nav_button")
        yield Button("💭 关系网络", id="nav_relationships", classes="nav_button")
        yield Button("🔍 审计日志", id="nav_audit", classes="nav_button")
        
        # 分隔线
        yield Static("─── 设置 ───", classes="nav_section_title")
        yield Static(":config 全局配置", classes="nav_hint")
        yield Static(":debug 开发模式", classes="nav_hint")
        yield Static(":export 导出数据", classes="nav_hint")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理按钮点击"""
        button_id = event.button.id
        if button_id and button_id.startswith("nav_"):
            view_id = button_id.replace("nav_", "")
            # 发送视图切换消息到主应用
            self.post_message(ViewChangeRequested(view_id))
            event.stop()
    
    def set_active(self, view_id: str) -> None:
        """设置激活状态"""
        for btn in self.query(Button):
            if btn.id == f"nav_{view_id}":
                btn.add_class("active")
            else:
                btn.remove_class("active")


class StatusBar(Static):
    """底部状态栏"""
    
    status = reactive("正在连接服务...")
    scene_status = reactive("")
    
    def render(self) -> str:
        parts = [f"[bold]状态:[/] {self.status}"]
        if self.scene_status:
            parts.append(self.scene_status)
        parts.append("[dim]: 命令模式 | ? 帮助 | q 退出[/]")
        return " • ".join(parts)


class TopBar(Static):
    """顶部状态栏"""
    
    character_name = reactive("林依")
    current_scene = reactive("未知")
    emotion = reactive("平静")
    time = reactive("")
    connection_status = reactive("未连接")
    
    def render(self) -> str:
        if not self.time:
            self.time = datetime.now().strftime("%H:%M")
        
        # 根据连接状态显示不同颜色
        if self.connection_status == "已连接":
            status_color = "green"
        elif self.connection_status == "连接中":
            status_color = "yellow"
        else:
            status_color = "red"
        
        return (
            f"[bold]{self.character_name}[/] • "
            f"[dim]在[/] {self.current_scene} • "
            f"[dim]情绪:[/] {self.emotion} • "
            f"{self.time}     "
            f"[{status_color}]● {self.connection_status}[/]"
        )


class NeoAgentTUI(App):
    """Neo Agent TUI 主应用"""
    
    CSS = AMBER_THEME + """
    Screen {
        background: #050302;
    }
    
    #top_bar {
        dock: top;
        height: 1;
        background: #0A0805;
        color: #F5E6D3;
        padding: 0 2;
    }
    
    #main_container {
        width: 100%;
        height: 1fr;
    }
    
    Sidebar {
        width: 24;
        background: #0A0805;
        border-right: solid #1C1812;
        padding: 1 1;
    }
    
    .nav_button {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        text-align: left;
        background: transparent;
        border: none;
        color: #C9B89A;
    }
    
    .nav_button:hover {
        background: #12100D;
        color: #F5E6D3;
    }
    
    .nav_button.active {
        background: #1C1812;
        color: #E9A568;
        border-left: thick #E9A568;
    }
    
    .nav_section_title {
        color: #8A7A66;
        text-style: italic;
        margin: 2 0 1 0;
        padding: 0 1;
    }
    
    .nav_hint {
        color: #8A6B4F;
        margin: 0 0 0 1;
        padding: 0;
    }
    
    #content {
        width: 1fr;
        height: 100%;
        background: #050302;
    }
    
    .view {
        width: 100%;
        height: 100%;
    }
    
    .view.hidden {
        display: none;
    }
    
    #status_bar {
        dock: bottom;
        height: 1;
        background: #0A0805;
        color: #C9B89A;
        padding: 0 2;
    }
    """
    
    BINDINGS = [
        Binding("c", "switch_view('chat')", "对话", show=True),
        Binding("i", "switch_view('itinerary')", "行程", show=True),
        Binding("s", "switch_view('scenes')", "场景", show=True),
        Binding("m", "switch_view('memory')", "记忆", show=True),
        Binding("r", "switch_view('relationships')", "关系", show=True),
        Binding("a", "switch_view('audit')", "审计", show=True),
        Binding("q", "quit", "退出", show=True),
        Binding("colon", "command_mode", "命令", show=False),
        Binding("question_mark", "help", "帮助", show=False),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = ServiceClient()
        self.current_view_id = "chat"
        self.debug_mode = False
    
    def compose(self) -> ComposeResult:
        yield TopBar(id="top_bar")
        
        with Horizontal(id="main_container"):
            yield Sidebar()
            
            with Container(id="content"):
                yield ChatView(classes="view", id="view_chat")
                yield ItineraryView(classes="view hidden", id="view_itinerary")
                yield ScenePoolView(classes="view hidden", id="view_scenes")
                yield MemoryView(classes="view hidden", id="view_memory")
                yield RelationshipView(classes="view hidden", id="view_relationships")
                yield AuditView(classes="view hidden", id="view_audit")
        
        yield StatusBar(id="status_bar")
    
    async def on_mount(self) -> None:
        """应用挂载时初始化"""
        top_bar = self.query_one("#top_bar", TopBar)
        top_bar.connection_status = "连接中"
        
        # 连接到服务
        try:
            await self.client.connect()
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.status = "服务运行中"
            top_bar.connection_status = "已连接"
            
            # 加载初始视图
            await self.load_current_view()
            
            # 更新顶栏信息
            await self.update_top_bar()
            
        except Exception as e:
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.status = f"连接失败: {e}"
            top_bar.connection_status = "未连接"
            self.notify(f"无法连接到服务: {e}", severity="error", timeout=10)
    
    def on_view_change_requested(self, message: ViewChangeRequested) -> None:
        """处理视图切换请求"""
        self.call_later(self.switch_view, message.view_id)
    
    async def update_top_bar(self) -> None:
        """更新顶栏信息"""
        try:
            # 获取角色信息
            profile = await self.client.call("character.get_profile")
            context = await self.client.call("session.get_context")
            
            top_bar = self.query_one("#top_bar", TopBar)
            if profile:
                top_bar.character_name = profile.get("name", "林依")
            
            if context:
                scene = context.get("current_scene", {})
                top_bar.current_scene = scene.get("location", "未知")
                top_bar.emotion = context.get("emotion", "平静")
            
            # 更新时间
            top_bar.time = datetime.now().strftime("%H:%M")
                
        except Exception:
            pass  # 静默失败，使用默认值
    
    def update_navigation(self) -> None:
        """更新导航栏激活状态"""
        sidebar = self.query_one(Sidebar)
        sidebar.set_active(self.current_view_id)
    
    async def load_current_view(self) -> None:
        """加载当前视图数据"""
        view = self.query_one(f"#view_{self.current_view_id}")
        if hasattr(view, 'load_data'):
            try:
                await view.load_data(self.client)
            except Exception as e:
                self.notify(f"加载视图失败: {e}", severity="error")
    
    async def switch_view(self, view_id: str) -> None:
        """切换视图"""
        if view_id == self.current_view_id:
            return
        
        # 隐藏所有视图
        for vid in ["chat", "itinerary", "scenes", "memory", "relationships", "audit"]:
            view = self.query_one(f"#view_{vid}")
            view.add_class("hidden")
        
        # 显示目标视图
        view = self.query_one(f"#view_{view_id}")
        view.remove_class("hidden")
        
        # 更新当前视图ID
        self.current_view_id = view_id
        
        # 更新导航栏
        self.update_navigation()
        
        # 加载视图数据
        await self.load_current_view()
    
    async def action_switch_view(self, view_id: str) -> None:
        """快捷键切换视图"""
        await self.switch_view(view_id)
    
    async def action_command_mode(self) -> None:
        """进入命令模式"""
        command = await self.push_screen_wait(CommandPalette())
        if command:
            await self.execute_command(command)
    
    async def execute_command(self, command: str) -> None:
        """执行命令"""
        parts = command.split()
        cmd = parts[0] if parts else ""
        
        if cmd == "config":
            result = await self.push_screen_wait(ConfigModal())
            if result:
                self.notify(f"配置已保存", timeout=3)
        
        elif cmd == "debug":
            if len(parts) > 1:
                mode = parts[1]
                if mode == "on":
                    self.debug_mode = True
                    self.notify("Debug 模式已开启", timeout=3)
                elif mode == "off":
                    self.debug_mode = False
                    self.notify("Debug 模式已关闭", timeout=3)
            else:
                self.notify("用法: debug on|off", severity="warning")
        
        elif cmd == "export":
            target = parts[1] if len(parts) > 1 else "all"
            self.notify(f"导出 {target}...", timeout=3)
        
        elif cmd == "import":
            self.notify("导入功能开发中...", timeout=3)
        
        elif cmd == "quit":
            self.exit()
        
        elif cmd == "help":
            help_text = """可用命令：
:config - 全局配置
:debug on|off - 切换调试模式
:export [character|all] - 导出数据
:import <path> - 导入数据
:quit - 退出"""
            self.notify(help_text, title="帮助", timeout=10)
        
        else:
            self.notify(f"未知命令: {command}", severity="warning")
    
    def action_help(self) -> None:
        """显示帮助"""
        help_text = """快捷键：
c - 对话视图
i - 今日行程
s - 场景池
m - 记忆与知识
r - 关系网络
a - 审计日志
: - 命令模式
? - 此帮助
q - 退出"""
        self.notify(help_text, title="快捷键", timeout=10)
    
    async def action_quit(self) -> None:
        """退出应用"""
        await self.client.disconnect()
        self.exit()


def run_tui():
    """启动 TUI"""
    app = NeoAgentTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
