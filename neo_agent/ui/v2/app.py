"""Neo Agent TUI v2 - 服务客户端主应用"""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
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
from .client import AgentClient
from .theme import AMBER_THEME


class NavigationItem(Button):
    """导航项 - 使用 Button 确保可点击"""
    
    class NavClicked(Message):
        """导航项点击消息"""
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id
    
    def __init__(self, label: str, icon: str, view_id: str, count: int = 0):
        # Button 的 label 会自动显示
        self.nav_label = label
        self.icon = icon
        self.view_id = view_id
        self.count = count
        self._is_active = False
        
        # 初始化按钮
        count_text = f" ({count})" if count > 0 else ""
        super().__init__(f"{icon} {label}{count_text}", variant="default")
    
    def update_display(self):
        """更新显示内容"""
        count_text = f" ({self.count})" if self.count > 0 else ""
        self.label = f"{self.icon} {self.nav_label}{count_text}"
        
        # 更新样式
        if self._is_active:
            self.variant = "primary"
        else:
            self.variant = "default"
    
    def set_active(self, active: bool):
        self._is_active = active
        self.update_display()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮点击事件"""
        event.stop()  # 阻止事件冒泡
        self.post_message(self.NavClicked(self.view_id))


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
    
    def render(self) -> str:
        if not self.time:
            self.time = datetime.now().strftime("%H:%M")
        return (
            f"[bold]{self.character_name}[/] • "
            f"[dim]在[/] {self.current_scene} • "
            f"[dim]情绪:[/] {self.emotion} • "
            f"{self.time}"
        )


class NeoAgentTUI(App):
    """Neo Agent TUI 主应用"""
    
    CSS = AMBER_THEME + """
    Screen {
        background: $surface-0;
    }
    
    #top_bar {
        dock: top;
        height: 1;
        background: $surface-1;
        color: $text-primary;
        padding: 0 2;
    }
    
    #main_container {
        width: 100%;
        height: 1fr;
    }
    
    #sidebar {
        width: 24;
        background: $surface-1;
        border-right: solid $surface-3;
        padding: 1;
    }
    
    #content {
        width: 1fr;
        background: $surface-0;
    }
    
    NavigationItem {
        width: 100%;
        height: auto;
        margin: 0 0 1 0;
        text-align: left;
    }
    
    NavigationItem Button {
        width: 100%;
    }
    
    .nav_section {
        width: 100%;
        height: auto;
        margin-top: 1;
    }
    
    .nav_title {
        color: $text-dim;
        text-style: italic;
        margin-bottom: 1;
        padding: 0 1;
    }
    
    #status_bar {
        dock: bottom;
        height: 1;
        background: $surface-1;
        color: $text-secondary;
        padding: 0 2;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("colon", "command_mode", "命令", show=False),
        Binding("question_mark", "help", "帮助", show=False),
        Binding("c", "switch_view('chat')", "对话", show=False),
        Binding("i", "switch_view('itinerary')", "行程", show=False),
        Binding("s", "switch_view('scenes')", "场景", show=False),
        Binding("m", "switch_view('memory')", "记忆", show=False),
        Binding("r", "switch_view('relationships')", "关系", show=False),
        Binding("a", "switch_view('audit')", "审计", show=False),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
        self.current_view_id = "chat"
        self.views = {}
        self.debug_mode = False
    
    def compose(self) -> ComposeResult:
        yield TopBar(id="top_bar")
        
        with Horizontal(id="main_container"):
            with Vertical(id="sidebar"):
                yield NavigationItem("对话", "💬", "chat")
                yield NavigationItem("今日行程", "📅", "itinerary", count=0)
                yield NavigationItem("场景池", "🌍", "scenes", count=0)
                yield NavigationItem("记忆与知识", "🧠", "memory")
                yield NavigationItem("关系网络", "💭", "relationships")
                yield NavigationItem("审计日志", "🔍", "audit")
                
                yield Static("─── 设置 ───", classes="nav_title")
                yield Static("[dim]:config 全局配置[/]")
                yield Static("[dim]:debug 开发模式[/]")
                yield Static("[dim]:export 导出数据[/]")
            
            with Container(id="content"):
                yield ChatView(id="view_chat")
                yield ItineraryView(id="view_itinerary")
                yield ScenePoolView(id="view_scenes")
                yield MemoryView(id="view_memory")
                yield RelationshipView(id="view_relationships")
                yield AuditView(id="view_audit")
        
        yield StatusBar(id="status_bar")
    
    async def on_mount(self) -> None:
        """挂载后初始化"""
        # 隐藏所有视图，只显示对话视图
        for vid in ["itinerary", "scenes", "memory", "relationships", "audit"]:
            view = self.query_one(f"#view_{vid}")
            view.display = False
        
        # 激活对话导航项
        self.update_navigation()
        
        # 连接服务
        await self.connect_service()
        
        # 设置定时器更新时间
        self.set_interval(60, self.update_time)
    
    async def connect_service(self) -> None:
        """连接到服务"""
        status_bar = self.query_one("#status_bar", StatusBar)
        try:
            await self.client.connect()
            status_bar.status = "[green]服务运行中[/]"
            
            # 加载初始数据
            await self.load_initial_data()
        except Exception as e:
            status_bar.status = f"[red]连接失败: {e}[/]"
            self.notify(f"无法连接到服务: {e}", severity="error", timeout=10)
    
    async def load_initial_data(self) -> None:
        """加载初始数据"""
        try:
            # 加载角色信息
            profile = await self.client.call("character.get_profile")
            if profile:
                top_bar = self.query_one("#top_bar", TopBar)
                top_bar.character_name = profile.get("name", "林依")
            
            # 加载当前场景
            scene = await self.client.call("scene.get_current")
            if scene:
                top_bar = self.query_one("#top_bar", TopBar)
                top_bar.current_scene = scene.get("location", "未知")
            
            # 加载情绪
            emotion = await self.client.call("emotion.get_current")
            if emotion:
                top_bar = self.query_one("#top_bar", TopBar)
                top_bar.emotion = emotion.get("state", "平静")
            
            # 更新导航计数
            await self.update_counts()
            
        except Exception as e:
            self.notify(f"加载数据失败: {e}", severity="error")
    
    async def update_counts(self) -> None:
        """更新导航项计数"""
        try:
            # 更新行程计数
            itinerary = await self.client.call("schedule.get_today_itinerary")
            if itinerary:
                for nav in self.query(NavigationItem):
                    if nav.view_id == "itinerary":
                        nav.count = len(itinerary)
                        nav.update_display()
            
            # 更新场景池计数
            scenes = await self.client.call("scene.list_pool")
            if scenes:
                for nav in self.query(NavigationItem):
                    if nav.view_id == "scenes":
                        nav.count = len(scenes)
                        nav.update_display()
        except Exception as e:
            pass  # 静默失败
    
    def update_time(self) -> None:
        """更新顶部时间"""
        top_bar = self.query_one("#top_bar", TopBar)
        top_bar.time = datetime.now().strftime("%H:%M")
    
    def update_navigation(self) -> None:
        """更新导航项激活状态"""
        for nav in self.query(NavigationItem):
            nav.set_active(nav.view_id == self.current_view_id)
    
    async def switch_view(self, view_id: str) -> None:
        """切换视图"""
        # 隐藏所有视图
        for vid in ["chat", "itinerary", "scenes", "memory", "relationships", "audit"]:
            view = self.query_one(f"#view_{vid}")
            view.display = False
        
        # 显示目标视图
        view = self.query_one(f"#view_{view_id}")
        view.display = True
        
        # 加载视图数据
        if hasattr(view, 'load_data'):
            await view.load_data(self.client)
        
        self.current_view_id = view_id
        self.update_navigation()
    
    async def on_navigation_item_nav_clicked(self, message: NavigationItem.NavClicked) -> None:
        """处理导航项点击"""
        await self.switch_view(message.view_id)
    
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
