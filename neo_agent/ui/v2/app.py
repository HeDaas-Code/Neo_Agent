"""Neo Agent TUI v2 主应用 - 完整重构版本"""
import asyncio
from datetime import datetime
from typing import Optional, Dict

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, RichLog, Input, Button, DataTable, Label
from textual.reactive import reactive
from textual.message import Message
from textual import events

from .client import AgentClient
from .theme import FULL_THEME
from .commands import CommandPalette, ConfigPanel, ExportPanel, ImportPanel, COMMAND_PANEL_CSS
from .event_handlers import EventHandlers


class StatusBar(Static):
    """顶栏状态栏"""
    character_name = reactive("连接中...")
    scene_info = reactive("")
    emotion = reactive("")
    time_str = reactive("")
    
    def compose(self) -> ComposeResult:
        yield Static("", id="status-content", classes="status-bar")
    
    def on_mount(self):
        self.set_interval(1.0, self.update_time)
        self.update_display()
    
    def update_time(self):
        self.time_str = datetime.now().strftime("%H:%M")
        self.update_display()
    
    def update_display(self):
        content = f"{self.character_name}"
        if self.scene_info:
            content += f" • {self.scene_info}"
        if self.emotion:
            content += f" • {self.emotion}"
        content += f" • {self.time_str}"
        self.query_one("#status-content", Static).update(content)


class NavigationItem(Static):
    """导航项 - 使用 Static 但监听鼠标点击"""
    
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.view_id = view_id
        self.can_focus = True  # 使其可聚焦
    
    def on_click(self, event: events.Click) -> None:
        """处理点击事件"""
        self.post_message(self.NavClicked(self.view_id))
    
    class NavClicked(Message):
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id


class Sidebar(Vertical):
    """左侧导航栏"""
    def compose(self) -> ComposeResult:
        yield Static("", classes="nav-section-header")
        yield NavigationItem("💬 对话", "chat", id="nav-chat", classes="nav-item active")
        yield NavigationItem("📅 今日行程", "itinerary", id="nav-itinerary", classes="nav-item")
        yield NavigationItem("🌍 场景池", "scenes", id="nav-scenes", classes="nav-item")
        yield NavigationItem("🧠 记忆与知识", "memory", id="nav-memory", classes="nav-item")
        yield NavigationItem("💭 关系网络", "relationships", id="nav-relationships", classes="nav-item")
        yield NavigationItem("🔍 审计日志", "audit", id="nav-audit", classes="nav-item")
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
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold #E9A568]欢迎使用 Neo Agent！[/bold #E9A568]")
        log.write("[dim]正在加载历史消息...[/dim]")
        try:
            if not self.client.connected:
                await asyncio.sleep(0.5)
            if not self.client.connected:
                log.write("[dim red]等待服务连接...[/dim red]")
                return
            history = await self.client.call("session.get_history", {"limit": 20})
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        log.write(f"[bold #F5E6D3]用户:[/bold #F5E6D3] {content}")
                    else:
                        log.write(f"[bold #E9A568]林依:[/bold #E9A568] {content}")
        except Exception as e:
            log.write(f"[dim red]加载历史失败: {e}[/dim red]")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "send-button":
            await self.send_message()
    
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat-input":
            await self.send_message()
    
    async def send_message(self):
        input_widget = self.query_one("#chat-input", Input)
        log = self.query_one("#chat-log", RichLog)
        user_msg = input_widget.value.strip()
        if not user_msg:
            return
        input_widget.value = ""
        log.write(f"[bold #F5E6D3]用户:[/bold #F5E6D3] {user_msg}")
        log.write("[dim]思考中...[/dim]")
        try:
            result = await self.client.call("session.send_message", {"text": user_msg})
            reply = result.get("reply", "")
            log.write(f"[bold #E9A568]林依:[/bold #E9A568] {reply}")
        except Exception as e:
            log.write(f"[dim red]发送失败: {e}[/dim red]")


class ItineraryView(Vertical):
    """今日行程视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("今日行程", classes="view-title")
        yield Button("刷新", id="refresh-itinerary", classes="refresh-button")
        yield RichLog(id="itinerary-log", classes="itinerary-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.refresh_itinerary()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-itinerary":
            await self.refresh_itinerary()
    
    async def refresh_itinerary(self):
        log = self.query_one("#itinerary-log", RichLog)
        log.clear()
        log.write("[dim]正在加载今日行程...[/dim]")
        try:
            result = await self.client.call("schedule.get_today_itinerary", {})
            itinerary = result.get("itinerary", [])
            if not itinerary:
                log.write("[dim]今日暂无行程[/dim]")
                return
            log.clear()
            for item in itinerary:
                time_str = item.get("time", "")
                activity = item.get("activity", "")
                location = item.get("location", "")
                schedule_type = item.get("type", "personal")
                type_label = {"personal": "个人", "user": "用户", "shared": "共同"}.get(schedule_type, "")
                is_current = item.get("is_current", False)
                marker = "▶" if is_current else " "
                log.write(f"{marker} [bold #E9A568]{time_str}[/bold #E9A568] [{type_label}] {activity}")
                if location:
                    log.write(f"   📍 {location}")
        except Exception as e:
            log.write(f"[dim red]加载失败: {e}[/dim red]")


class ScenePoolView(Vertical):
    """场景池视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("场景池", classes="view-title")
        yield Button("刷新", id="refresh-scenes", classes="refresh-button")
        yield RichLog(id="scenes-log", classes="scenes-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.refresh_scenes()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-scenes":
            await self.refresh_scenes()
    
    async def refresh_scenes(self):
        log = self.query_one("#scenes-log", RichLog)
        log.clear()
        log.write("[dim]正在加载场景池...[/dim]")
        try:
            result = await self.client.call("scene.list_pool", {})
            scenes = result.get("scenes", [])
            current_scene = result.get("current_scene", {})
            if not scenes:
                log.write("[dim]暂无已访问场景[/dim]")
                return
            log.clear()
            log.write(f"[bold #E9A568]当前场景:[/bold #E9A568] {current_scene.get('location', '未知')} - {current_scene.get('area', '未知')}\n")
            log.write("[bold #C9B89A]已访问场景:[/bold #C9B89A]")
            for scene in scenes:
                name = scene.get("name", "")
                visited = scene.get("visited", False)
                frozen = scene.get("layout_frozen", False)
                marker = "✓" if visited else " "
                status = "(已固化)" if frozen else "(可编辑)"
                log.write(f" {marker} {name} {status}")
        except Exception as e:
            log.write(f"[dim red]加载失败: {e}[/dim red]")


class MemoryView(Vertical):
    """记忆与知识视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("记忆与知识", classes="view-title")
        with Horizontal(classes="search-container"):
            yield Input(placeholder="搜索记忆...", id="memory-search", classes="search-input")
            yield Button("搜索", id="search-memory", classes="search-button")
        yield RichLog(id="memory-log", classes="memory-log", wrap=True, markup=True)
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "search-memory":
            await self.search_memory()
    
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "memory-search":
            await self.search_memory()
    
    async def search_memory(self):
        input_widget = self.query_one("#memory-search", Input)
        log = self.query_one("#memory-log", RichLog)
        query = input_widget.value.strip()
        if not query:
            log.clear()
            log.write("[dim]请输入搜索关键词[/dim]")
            return
        log.clear()
        log.write(f"[dim]正在搜索: {query}...[/dim]")
        try:
            result = await self.client.call("memory.search", {"query": query})
            memories = result.get("results", [])
            if not memories:
                log.write("[dim]未找到相关记忆[/dim]")
                return
            log.clear()
            log.write(f"[bold #E9A568]找到 {len(memories)} 条相关记忆:[/bold #E9A568]\n")
            for idx, mem in enumerate(memories, 1):
                content = mem.get("content", "")
                relevance = mem.get("relevance", 0.0)
                timestamp = mem.get("timestamp", "")
                log.write(f"{idx}. [bold #C9B89A]相关度: {relevance:.2f}[/bold #C9B89A]")
                log.write(f"   {content}")
                log.write(f"   [dim]{timestamp}[/dim]\n")
        except Exception as e:
            log.write(f"[dim red]搜索失败: {e}[/dim red]")


class RelationshipView(Vertical):
    """关系网络视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("关系网络", classes="view-title")
        yield Button("刷新", id="refresh-relationships", classes="refresh-button")
        yield RichLog(id="relationships-log", classes="relationships-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.refresh_relationships()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-relationships":
            await self.refresh_relationships()
    
    async def refresh_relationships(self):
        log = self.query_one("#relationships-log", RichLog)
        log.clear()
        log.write("[dim]正在加载关系网络...[/dim]")
        try:
            result = await self.client.call("relationship.list_all", {})
            relationships = result.get("relationships", [])
            if not relationships:
                log.write("[dim]暂无关系记录[/dim]")
                return
            log.clear()
            for rel in relationships:
                entity = rel.get("entity", "")
                score = rel.get("score", 0)
                last_updated = rel.get("last_updated", "")
                log.write(f"[bold #E9A568]{entity}[/bold #E9A568] - 分数: {score}")
                log.write(f"  [dim]最后更新: {last_updated}[/dim]\n")
        except Exception as e:
            log.write(f"[dim red]加载失败: {e}[/dim red]")


class AuditView(Vertical):
    """审计日志视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("审计日志", classes="view-title")
        yield Button("刷新", id="refresh-audit", classes="refresh-button")
        yield RichLog(id="audit-log", classes="audit-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.refresh_audit()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-audit":
            await self.refresh_audit()
    
    async def refresh_audit(self):
        log = self.query_one("#audit-log", RichLog)
        log.clear()
        log.write("[dim]正在加载审计日志...[/dim]")
        try:
            result = await self.client.call("audit.list_recent", {"limit": 50})
            audits = result.get("audits", [])
            if not audits:
                log.write("[dim]暂无审计记录[/dim]")
                return
            log.clear()
            for audit in audits:
                timestamp = audit.get("timestamp", "")
                operation = audit.get("operation", "")
                risk_level = audit.get("risk_level", "low")
                details = audit.get("details", "")
                risk_color = {"low": "#A8C079", "medium": "#E9A568", "high": "#D97757"}.get(risk_level, "#8A7A66")
                log.write(f"[{risk_color}]●[/{risk_color}] [{timestamp}] {operation}")
                if details:
                    log.write(f"   {details}\n")
        except Exception as e:
            log.write(f"[dim red]加载失败: {e}[/dim red]")


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
    
    async def refresh_current_view(self):
        """刷新当前视图"""
        current = self.views.get(self.current_view)
        if hasattr(current, 'on_mount'):
            await current.on_mount()


class NeoAgentApp(App):
    """Neo Agent TUI 主应用"""
    
    CSS = FULL_THEME + COMMAND_PANEL_CSS
    BINDINGS = [
        ("q", "quit", "退出"),
        (":", "command_mode", "命令模式"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
        self.connected = False
        self.event_handlers = None
        self.ws_client = None
    
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar", classes="sidebar")
            yield MainContent(self.client, id="main-content", classes="main-content")
        yield Static("正在连接服务...", id="footer", classes="footer")
    
    async def on_mount(self):
        self.event_handlers = EventHandlers(self)
        asyncio.create_task(self.connect_to_service())
        asyncio.create_task(self.periodic_status_update())
    
    async def connect_to_service(self):
        footer = self.query_one("#footer", Static)
        try:
            await self.client.connect()
            self.connected = True
            footer.update("服务已连接 • 按 : 进入命令模式 • 按 q 退出")
            self.notify("服务连接成功", severity="information")
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.character_name = "林依"
            status_bar.scene_info = "在家-客厅"
            status_bar.emotion = "情绪:平静"
            main_content = self.query_one("#main-content", MainContent)
            await main_content.refresh_current_view()
        except Exception as e:
            footer.update(f"服务连接失败: {e} • 按 q 退出")
            self.notify(f"连接失败: {e}", severity="error")
    
    async def periodic_status_update(self):
        while True:
            await asyncio.sleep(5)
            if self.connected:
                try:
                    await self.client.call("system.get_status", {})
                except Exception:
                    pass
    
    def on_navigation_item_nav_clicked(self, message: NavigationItem.NavClicked):
        """处理导航项点击"""
        view_id = message.view_id
        sidebar = self.query_one("#sidebar", Sidebar)
        for item in sidebar.query(NavigationItem):
            if item.view_id == view_id:
                item.add_class("active")
            else:
                item.remove_class("active")
        main_content = self.query_one("#main-content", MainContent)
        main_content.switch_to(view_id)
    
    def action_command_mode(self):
        self.run_worker(self._open_command_palette())
    
    async def _open_command_palette(self):
        result = await self.push_screen_wait(CommandPalette())
        if result:
            await self.handle_command(result)
    
    async def handle_command(self, cmd_data: dict):
        command = cmd_data.get("command", "")
        args = cmd_data.get("args", [])
        if command == "config":
            await self.open_config_panel()
        elif command == "debug":
            if args and args[0] in ["on", "off"]:
                try:
                    await self.client.call("system.set_debug", {"enabled": args[0] == "on"})
                    self.notify(f"Debug 模式已{'开启' if args[0] == 'on' else '关闭'}", severity="information")
                except Exception as e:
                    self.notify(f"设置失败: {e}", severity="error")
            else:
                self.notify("用法: debug on | debug off", severity="warning")
        elif command == "export":
            await self.open_export_panel(args[0] if args else "character")
        elif command == "import":
            if args:
                await self.import_data(args[0])
            else:
                await self.open_import_panel()
        else:
            self.notify(f"未知命令: {command}", severity="warning")
    
    async def open_config_panel(self):
        try:
            config = await self.client.call("system.get_config", {})
        except Exception:
            config = {"llm_model": "gpt-4", "pyvdisk_path": "~/.neo_agent/data",
                     "timezone": "Asia/Shanghai", "debug_mode": False}
        result = await self.push_screen_wait(ConfigPanel(config))
        if result:
            try:
                await self.client.call("system.update_config", result)
                self.notify("配置已保存", severity="information")
            except Exception as e:
                self.notify(f"保存失败: {e}", severity="error")
    
    async def open_export_panel(self, export_type: str):
        result = await self.push_screen_wait(ExportPanel(export_type))
        if result:
            try:
                await self.client.call("system.export_data", {"type": result["type"], "path": result["path"]})
                self.notify(f"导出成功: {result['path']}", severity="information")
            except Exception as e:
                self.notify(f"导出失败: {e}", severity="error")
    
    async def open_import_panel(self):
        result = await self.push_screen_wait(ImportPanel())
        if result:
            await self.import_data(result["path"])
    
    async def import_data(self, file_path: str):
        try:
            await self.client.call("system.import_data", {"path": file_path})
            self.notify(f"导入成功: {file_path}", severity="information")
        except Exception as e:
            self.notify(f"导入失败: {e}", severity="error")
    
    async def _handle_ws_event(self, event_data: dict):
        if self.event_handlers:
            try:
                await self.event_handlers.handle_event(event_data.get("type", ""), event_data.get("data", {}))
            except Exception as e:
                self.log(f"事件处理失败: {e}")
    
    async def on_unmount(self):
        if self.ws_client:
            await self.ws_client.disconnect()
        if self.connected:
            await self.client.disconnect()


def run_tui():
    app = NeoAgentApp()
    app.run()
