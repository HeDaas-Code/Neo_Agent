"""Neo Agent TUI v2 - 服务-客户端架构"""
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Input, Button, RichLog, DataTable
from textual.reactive import reactive
from textual.message import Message
from textual import events
from rich.text import Text

from .client import AgentClient
from .theme import AMBER_THEME


class NavigationItem(Static):
    """导航项 - 可点击的导航按钮"""
    
    can_focus = True
    
    DEFAULT_CSS = """
    NavigationItem {
        height: auto;
        padding: 1;
        text-style: bold;
    }
    
    NavigationItem:hover {
        background: #12100D;
    }
    
    NavigationItem.active {
        background: #E9A568 20%;
        color: #E9A568;
    }
    
    NavigationItem:focus {
        background: #1C1812;
    }
    """
    
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.view_id = view_id
    
    def on_click(self, event: events.Click) -> None:
        """处理点击事件"""
        event.stop()
        self.post_message(self.NavClicked(self.view_id))
    
    def on_key(self, event: events.Key) -> None:
        """处理键盘事件 - 回车键触发导航"""
        if event.key == "enter":
            self.post_message(self.NavClicked(self.view_id))
    
    class NavClicked(Message):
        """导航项被点击的消息"""
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id


class TopBar(Static):
    """顶部状态栏"""
    character = reactive("林依")
    scene = reactive("家")
    emotion = reactive("平静")
    time = reactive("--:--")
    
    def render(self) -> str:
        return f"{self.character} • {self.scene} • 情绪:{self.emotion} • {self.time}"
    
    def update_info(self, character: str = None, scene: str = None, emotion: str = None, time: str = None):
        if character:
            self.character = character
        if scene:
            self.scene = scene
        if emotion:
            self.emotion = emotion
        if time:
            self.time = time


class Sidebar(Vertical):
    """左侧导航栏"""
    
    DEFAULT_CSS = """
    Sidebar {
        width: 24;
        background: #0A0805;
        border-right: solid #2B231C;
    }
    
    .nav-section-header {
        color: #8A6B4F;
        padding: 1;
        text-style: bold;
    }
    
    .nav-hint {
        color: #8A7A66;
        padding-left: 2;
        text-style: italic;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Static("", classes="nav-section-header")
        yield NavigationItem("💬 对话", "chat", id="nav-chat", classes="active")
        yield NavigationItem("📅 今日行程", "itinerary", id="nav-itinerary")
        yield NavigationItem("🌍 场景池", "scenes", id="nav-scenes")
        yield NavigationItem("🧠 记忆与知识", "memory", id="nav-memory")
        yield NavigationItem("💭 关系网络", "relationships", id="nav-relationships")
        yield NavigationItem("🔍 审计日志", "audit", id="nav-audit")
        yield Static("─── 设置 ───", classes="nav-section-header")
        yield Static(":config 全局配置", classes="nav-hint")
        yield Static(":debug  开发模式", classes="nav-hint")
        yield Static(":export 导出数据", classes="nav-hint")


from .views import ChatView, ItineraryView, ScenePoolView, MemoryView, RelationshipView, AuditView

class MainContent(Container):
    """主内容区容器"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.current_view = "chat"
        self.views = {}
    
    def compose(self) -> ComposeResult:
        self.views["chat"] = ChatView(self.client, id="view-chat")
        self.views["itinerary"] = ItineraryView(self.client, id="view-itinerary")
        self.views["scenes"] = ScenePoolView(self.client, id="view-scenes")
        self.views["memory"] = MemoryView(self.client, id="view-memory")
        self.views["relationships"] = RelationshipView(self.client, id="view-relationships")
        self.views["audit"] = AuditView(self.client, id="view-audit")
        
        for view_id, view in self.views.items():
            if view_id != "chat":
                view.display = False
            yield view
    
    def switch_to(self, view_id: str):
        """切换到指定视图"""
        if view_id not in self.views:
            return
        
        for vid, view in self.views.items():
            view.display = (vid == view_id)
        
        self.current_view = view_id


class StatusBar(Static):
    """底部状态栏"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection_status = "连接中..."
    
    def update_status(self, connected: bool, scene: str = "", emotion: str = ""):
        if connected:
            status_parts = ["[bold #A8C079]●[/bold #A8C079] 服务已连接"]
            if scene:
                status_parts.append(f"场景: {scene}")
            if emotion:
                status_parts.append(f"情绪: {emotion}")
            status_parts.append("按 : 进入命令模式 • 按 q 退出")
            self.update(" • ".join(status_parts))
        else:
            self.update("[bold #D97757]●[/bold #D97757] 连接中...")


class CommandPalette(Container):
    """命令面板（模态）"""
    pass


class NeoAgentApp(App):
    """Neo Agent TUI 主应用"""
    
    CSS = AMBER_THEME + """
    Screen {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 3 1fr 3;
    }
    
    #topbar {
        dock: top;
        height: 3;
        background: #0A0805;
        content-align: center middle;
        text-style: bold;
        color: #F5E6D3;
        border-bottom: solid #2B231C;
    }
    
    #main-layout {
        layout: horizontal;
    }
    
    #sidebar {
        width: 24;
    }
    
    #main-content {
        width: 1fr;
    }
    
    #statusbar {
        dock: bottom;
        height: 3;
        background: #0A0805;
        content-align: left middle;
        padding-left: 2;
        color: #C9B89A;
        border-top: solid #2B231C;
    }
    
    .view-container {
        padding: 2;
        background: #050302;
    }
    
    .view-title {
        margin-bottom: 1;
        text-style: bold;
        color: #E9A568;
    }
    
    .chat-log {
        height: 1fr;
        background: #050302;
        border: solid #2B231C;
        padding: 1;
    }
    
    .chat-input-container {
        dock: bottom;
        height: 3;
        background: #0A0805;
        padding: 0 1;
    }
    
    DataTable {
        height: 1fr;
        background: #0A0805;
    }
    
    RichLog {
        height: 1fr;
        background: #050302;
        border: solid #2B231C;
        padding: 1;
    }
    """

    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("colon", "command_mode", "命令模式"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
    
    def compose(self) -> ComposeResult:
        yield TopBar(id="topbar")
        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar")
            yield MainContent(self.client, id="main-content")
        yield StatusBar(id="statusbar")
    
    async def on_mount(self):
        """应用启动时连接服务"""
        statusbar = self.query_one("#statusbar", StatusBar)
        
        try:
            await self.client.connect()
            statusbar.update_status(True)
            
            # 获取初始状态
            context = await self.client.call("session.get_context", {})
            if not context:
                context = {}
            
            scene = context.get("current_scene") or {}
            emotion = context.get("emotion") or {}
            character = context.get("character") or {}
            
            # 更新顶栏
            topbar = self.query_one("#topbar", TopBar)
            character_name = character.get("name", "林依")
            scene_text = f"{scene.get('location', '未知')}"
            emotion_text = emotion.get("state", "平静")
            
            topbar.update_info(character=character_name, scene=scene_text, emotion=emotion_text)
            statusbar.update_status(True, scene_text, emotion_text)
            
        except Exception as e:
            statusbar.update(f"[red]连接失败: {e}[/red]")
    
    def on_navigation_item_nav_clicked(self, message: NavigationItem.NavClicked):
        """处理导航项点击"""
        view_id = message.view_id
        
        # 更新导航项样式
        sidebar = self.query_one("#sidebar", Sidebar)
        for item in sidebar.query(NavigationItem):
            if item.view_id == view_id:
                item.add_class("active")
            else:
                item.remove_class("active")
        
        # 切换视图
        main_content = self.query_one("#main-content", MainContent)
        main_content.switch_to(view_id)
    
    def on_chat_view_chat_updated(self, message: ChatView.ChatUpdated):
        """处理对话更新事件"""
        topbar = self.query_one("#topbar", TopBar)
        statusbar = self.query_one("#statusbar", StatusBar)
        
        scene = message.scene
        emotion = message.emotion
        
        scene_text = f"{scene.get('location', '未知')}-{scene.get('area', '未知')}"
        emotion_text = emotion.get("state", "平静")
        
        topbar.update_info(scene=scene_text, emotion=emotion_text)
        statusbar.update_status(True, scene_text, emotion_text)
    
    def action_command_mode(self):
        """打开命令面板"""
        self.notify("命令模式尚未实现")


def run_tui():
    """启动 TUI"""
    app = NeoAgentApp()
    app.run()
