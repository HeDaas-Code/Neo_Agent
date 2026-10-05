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


class NavigationItem(Static, can_focus=True):
    """导航项 - 可点击的导航按钮"""
    
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
    
    class NavClicked(Message):
        """导航项被点击的消息"""
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id = view_id


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


class ChatView(Vertical):
    """对话视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", classes="chat-log", wrap=True, markup=True)
        with Horizontal(classes="chat-input-container"):
            yield Input(placeholder="输入消息... (Ctrl+Enter 发送)", id="chat-input", classes="chat-input")
            yield Button("发送", variant="primary", id="send-button")
    
    async def on_mount(self):
        """挂载时加载历史消息"""
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold #E9A568]欢迎使用 Neo Agent！[/bold #E9A568]")
        log.write("[dim]正在加载历史消息...[/dim]")
        
        try:
            history = await self.client.call("session.get_history", {"limit": 20})
            log.clear()
            log.write("[bold #E9A568]═══ 对话历史 ═══[/bold #E9A568]\n")
            
            for msg in reversed(history):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", "")
                
                if role == "user":
                    log.write(f"[bold #F5E6D3]你[/bold #F5E6D3]: {content}")
                else:
                    log.write(f"[bold #E9A568]林依[/bold #E9A568]: {content}")
            
            log.write("\n[dim]─────────────────[/dim]\n")
        except Exception as e:
            log.clear()
            log.write(f"[yellow]无法加载历史消息: {e}[/yellow]")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """发送按钮点击"""
        if event.button.id == "send-button":
            await self._send_message()
    
    async def on_input_submitted(self, event: Input.Submitted):
        """输入框提交（Ctrl+Enter）"""
        if event.input.id == "chat-input":
            await self._send_message()
    
    async def _send_message(self):
        """发送消息到 Agent"""
        input_widget = self.query_one("#chat-input", Input)
        log = self.query_one("#chat-log", RichLog)
        
        message = input_widget.value.strip()
        if not message:
            return
        
        # 清空输入框
        input_widget.value = ""
        
        # 显示用户消息
        log.write(f"\n[bold #F5E6D3]你[/bold #F5E6D3]: {message}")
        log.write("[dim #8A6B4F]思考中...[/dim #8A6B4F]")
        
        try:
            # 调用 RPC
            result = await self.client.call("session.send_message", {"text": message})
            
            reply = result.get("reply", "")
            emotion = result.get("emotion", {})
            scene = result.get("scene", {})
            
            # 移除"思考中..."
            log.write(f"[bold #E9A568]林依[/bold #E9A568]: {reply}")
            
            # 发送更新事件
            self.post_message(self.ChatUpdated(reply, emotion, scene))
            
        except Exception as e:
            log.write(f"[bold red]错误[/bold red]: {str(e)}")
    
    class ChatUpdated(Message):
        """对话更新消息"""
        def __init__(self, reply: str, emotion: dict, scene: dict):
            super().__init__()
            self.reply = reply
            self.emotion = emotion
            self.scene = scene


class ItineraryView(Vertical):
    """今日行程视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold #E9A568]今日行程[/bold #E9A568]", classes="view-title")
        yield DataTable(id="itinerary-table")
        yield Button("刷新", id="refresh-itinerary-btn", variant="primary")
    
    async def on_mount(self):
        """挂载时加载今日行程"""
        table = self.query_one("#itinerary-table", DataTable)
        table.add_columns("时间", "活动", "地点", "类型")
        await self.refresh_itinerary()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-itinerary-btn":
            await self.refresh_itinerary()
    
    async def refresh_itinerary(self):
        """刷新今日行程数据"""
        table = self.query_one("#itinerary-table", DataTable)
        table.clear()
        
        try:
            result = await self.client.call("schedule.get_today_itinerary", {})
            itinerary = result.get("itinerary", [])
            
            if not itinerary:
                table.add_row("--:--", "暂无行程", "—", "—")
            else:
                for item in itinerary:
                    time_str = item.get("time", "--:--")
                    activity = item.get("activity", "未知活动")
                    location = item.get("location", "未知")
                    itype = item.get("type", "个人")
                    table.add_row(time_str, activity, location, itype)
        except Exception as e:
            table.add_row("错误", str(e), "—", "—")


class ScenePoolView(Vertical):
    """场景池视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold #E9A568]场景池[/bold #E9A568]", classes="view-title")
        yield DataTable(id="scene-table")
        yield Button("刷新", id="refresh-scenes-btn", variant="primary")
    
    async def on_mount(self):
        """挂载时加载场景池"""
        table = self.query_one("#scene-table", DataTable)
        table.add_columns("地点", "访问次数", "最后访问")
        await self.refresh_scenes()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-scenes-btn":
            await self.refresh_scenes()
    
    async def refresh_scenes(self):
        """刷新场景池数据"""
        table = self.query_one("#scene-table", DataTable)
        table.clear()
        
        try:
            result = await self.client.call("scene.list_pool", {})
            scenes = result.get("scenes", [])
            
            if not scenes:
                table.add_row("暂无场景", "0", "—")
            else:
                for scene in scenes:
                    name = scene.get("name", "未知")
                    visits = scene.get("visit_count", 0)
                    last_visit = scene.get("last_visit", "从未")
                    table.add_row(name, str(visits), last_visit)
        except Exception as e:
            table.add_row("错误", str(e), "—")


class MemoryView(Vertical):
    """记忆与知识视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold #E9A568]记忆与知识[/bold #E9A568]", classes="view-title")
        with Horizontal(classes="search-container"):
            yield Input(placeholder="搜索记忆...", id="memory-search-input")
            yield Button("搜索", id="memory-search-btn", variant="primary")
        yield RichLog(id="memory-results", wrap=True, markup=True)
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "memory-search-btn":
            await self._search_memory()
    
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "memory-search-input":
            await self._search_memory()
    
    async def _search_memory(self):
        """搜索记忆"""
        input_widget = self.query_one("#memory-search-input", Input)
        results_log = self.query_one("#memory-results", RichLog)
        
        query = input_widget.value.strip()
        if not query:
            return
        
        results_log.clear()
        results_log.write("[dim]搜索中...[/dim]")
        
        try:
            result = await self.client.call("memory.search", {"query": query})
            memories = result.get("memories", [])
            
            results_log.clear()
            if not memories:
                results_log.write("[yellow]未找到相关记忆[/yellow]")
            else:
                results_log.write(f"[bold]找到 {len(memories)} 条记忆：[/bold]\n")
                for i, mem in enumerate(memories, 1):
                    text = mem.get("text", "")
                    relevance = mem.get("relevance", 0.0)
                    results_log.write(f"\n[bold #E9A568]{i}.[/bold #{E9A568}] [dim](相关度: {relevance:.2f})[/dim]")
                    results_log.write(f"  {text}")
        except Exception as e:
            results_log.clear()
            results_log.write(f"[red]搜索失败: {e}[/red]")


class RelationshipView(Vertical):
    """关系网络视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold #E9A568]关系网络[/bold #E9A568]", classes="view-title")
        yield DataTable(id="relationship-table")
        yield Button("刷新", id="refresh-relationships-btn", variant="primary")
    
    async def on_mount(self):
        """挂载时加载关系数据"""
        table = self.query_one("#relationship-table", DataTable)
        table.add_columns("实体", "分数", "阶段", "最近更新")
        await self.refresh_relationships()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-relationships-btn":
            await self.refresh_relationships()
    
    async def refresh_relationships(self):
        """刷新关系数据"""
        table = self.query_one("#relationship-table", DataTable)
        table.clear()
        
        try:
            result = await self.client.call("relationship.list_all", {})
            relationships = result.get("relationships", [])
            
            if not relationships:
                table.add_row("暂无关系", "0", "—", "—")
            else:
                for rel in relationships:
                    entity = rel.get("entity", "未知")
                    score = rel.get("score", 0)
                    stage = rel.get("stage", "stranger")
                    last_update = rel.get("last_update", "从未")
                    table.add_row(entity, str(score), stage, last_update)
        except Exception as e:
            table.add_row("错误", str(e), "—", "—")


class AuditView(Vertical):
    """审计日志视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("[bold #E9A568]审计日志[/bold #E9A568]", classes="view-title")
        yield RichLog(id="audit-log", wrap=True, markup=True)
        yield Button("刷新", id="refresh-audit-btn", variant="primary")
    
    async def on_mount(self):
        """挂载时加载审计日志"""
        await self.refresh_audit()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-audit-btn":
            await self.refresh_audit()
    
    async def refresh_audit(self):
        """刷新审计日志"""
        log = self.query_one("#audit-log", RichLog)
        log.clear()
        
        try:
            result = await self.client.call("audit.get_logs", {"limit": 50})
            logs = result.get("logs", [])
            
            if not logs:
                log.write("[dim]暂无审计日志[/dim]")
            else:
                for entry in logs:
                    timestamp = entry.get("timestamp", "")
                    action = entry.get("action", "unknown")
                    risk = entry.get("risk_level", "low")
                    details = entry.get("details", "")
                    
                    risk_color = {
                        "low": "#8A6B4F",
                        "medium": "#E9A568",
                        "high": "#D97757"
                    }.get(risk, "#8A6B4F")
                    
                    log.write(f"[{risk_color}]●[/{risk_color}] [{timestamp[:19]}] {action}: {details}")
        except Exception as e:
            log.write(f"[red]加载失败: {e}[/red]")


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
