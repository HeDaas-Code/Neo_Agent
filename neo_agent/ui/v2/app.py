"""Neo Agent TUI v2 主应用 - 完整重构版本"""
import asyncio
from datetime import datetime
from typing import Optional, Dict

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Static, RichLog, Input, Button
from textual.reactive import reactive
from textual.message import Message

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
    """导航项"""
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.view_id = view_id
    
    def on_click(self):
        self.post_message(self.NavClicked(self.view_id))
    
    class NavClicked(Message):
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id


class Sidebar(Vertical):
    """左侧导航栏"""
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
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold #E9A568]欢迎使用 Neo Agent！[/bold #E9A568]")
        log.write("[dim]正在加载历史消息...[/dim]")
        try:
            # 等待客户端连接
            if not self.client.connected:
                await asyncio.sleep(0.5)  # 等待主应用连接
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
            response = await self.client.call("session.send_message", {"text": user_msg})
            reply = response.get("reply", "")
            log.write(f"[bold #E9A568]林依:[/bold #E9A568] {reply}")
        except Exception as e:
            log.write(f"[red]发送失败: {e}[/red]")


class ItineraryView(Vertical):
    """今日行程视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("📅 今日行程", classes="view-title")
        yield Static("", id="itinerary-date", classes="view-subtitle")
        yield ScrollableContainer(
            RichLog(id="itinerary-list", classes="itinerary-log", wrap=False, markup=True),
            classes="itinerary-container"
        )
        yield Button("刷新", id="refresh-itinerary", classes="refresh-button")
    
    async def on_mount(self):
        await self.load_itinerary()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-itinerary":
            await self.load_itinerary()
    
    async def load_itinerary(self):
        log = self.query_one("#itinerary-list", RichLog)
        date_label = self.query_one("#itinerary-date", Static)
        log.clear()
        if not self.client.connected:
            log.write("[dim red]等待服务连接...[/dim red]")
            return
        date_label.update(f"[dim]{datetime.now().strftime('%Y年%m月%d日')}[/dim]")
        log.write("[dim]加载中...[/dim]")
        try:
            itinerary = await self.client.call("schedule.get_today_itinerary", {})
            log.clear()
            if itinerary and len(itinerary) > 0:
                for item in itinerary:
                    time_str = item.get("time", "")
                    activity = item.get("activity", "")
                    location = item.get("location", "")
                    category = item.get("category", "agent")
                    is_current = item.get("is_current", False)
                    if category == "user":
                        icon, color = "📌", "#C9B89A"
                    elif category == "shared":
                        icon, color = "🤝", "#D4863C"
                    else:
                        icon, color = "✨", "#E9A568"
                    if is_current:
                        log.write(f"[bold {color}]▶ {icon} {time_str}[/bold {color}]")
                        log.write(f"[bold {color}]  {activity}[/bold {color}]")
                        if location:
                            log.write(f"[bold {color}]  📍 {location}[/bold {color}]")
                    else:
                        log.write(f"[{color}]{icon} {time_str}[/{color}]")
                        log.write(f"[dim]  {activity}[/dim]")
                        if location:
                            log.write(f"[dim]  📍 {location}[/dim]")
                    log.write("")
            else:
                log.write("[dim]今天还没有安排[/dim]")
        except Exception as e:
            log.clear()
            log.write(f"[red]加载失败: {e}[/red]")


class ScenePoolView(Vertical):
    """场景池视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("🌍 场景池", classes="view-title")
        yield Static("已访问的场景", classes="view-subtitle")
        yield ScrollableContainer(
            RichLog(id="scene-list", classes="scene-log", wrap=True, markup=True),
            classes="scene-container"
        )
        yield Button("刷新", id="refresh-scenes", classes="refresh-button")
    
    async def on_mount(self):
        await self.load_scenes()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-scenes":
            await self.load_scenes()
    
    async def load_scenes(self):
        log = self.query_one("#scene-list", RichLog)
        log.clear()
        if not self.client.connected:
            log.write("[dim red]等待服务连接...[/dim red]")
            return
        log.write("[dim]加载中...[/dim]")
        try:
            scenes = await self.client.call("scene.list_pool", {})
            current_scene = await self.client.call("scene.get_current", {})
            current_location_id = current_scene.get("location_id", "") if current_scene else ""
            log.clear()
            if scenes and len(scenes) > 0:
                for scene in scenes:
                    location_id = scene.get("location_id", "")
                    name = scene.get("name", "")
                    visited = scene.get("visited", False)
                    area_count = scene.get("area_count", 0)
                    is_current = location_id == current_location_id
                    if is_current:
                        log.write(f"[bold #E9A568]▶ 🌟 {name}[/bold #E9A568]")
                        log.write(f"[bold #E9A568]  当前所在位置[/bold #E9A568]")
                    else:
                        log.write(f"[bold #F5E6D3]{name}[/bold #F5E6D3]")
                    if visited:
                        log.write(f"[dim]  ✓ 已访问 • {area_count} 个区域[/dim]")
                    else:
                        log.write(f"[dim]  待访问[/dim]")
                    log.write("")
            else:
                log.write("[dim]还没有场景记录[/dim]")
                log.write("[dim]随着日程进行，场景会自动生成并记录在这里[/dim]")
        except Exception as e:
            log.clear()
            log.write(f"[red]加载失败: {e}[/red]")


class MemoryView(Vertical):
    """记忆与知识视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("🧠 记忆与知识", classes="view-title")
        with Horizontal(classes="search-bar"):
            yield Input(placeholder="搜索记忆...", id="memory-search", classes="search-input")
            yield Button("搜索", id="search-memory", classes="search-button")
        yield ScrollableContainer(
            RichLog(id="memory-results", classes="memory-log", wrap=True, markup=True),
            classes="memory-container"
        )
    
    async def on_mount(self):
        self.query_one("#memory-results", RichLog).write("[dim]输入关键词搜索记忆和知识[/dim]")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "search-memory":
            await self.search_memory()
    
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "memory-search":
            await self.search_memory()
    
    async def search_memory(self):
        search_input = self.query_one("#memory-search", Input)
        log = self.query_one("#memory-results", RichLog)
        query = search_input.value.strip()
        if not query:
            log.clear()
        if not self.client.connected:
            log.write("[dim red]等待服务连接...[/dim red]")
            return
            log.write("[dim]请输入搜索关键词[/dim]")
            return
        log.clear()
        log.write(f"[dim]搜索: {query}...[/dim]")
        try:
            results = await self.client.call("memory.search", {"query": query})
            log.clear()
            if results and len(results) > 0:
                log.write(f"[bold #E9A568]找到 {len(results)} 条相关记忆[/bold #E9A568]\n")
                for idx, result in enumerate(results, 1):
                    content = result.get("content", "")
                    relevance = result.get("relevance", 0.0)
                    timestamp = result.get("timestamp", "")
                    log.write(f"[bold #F5E6D3]{idx}. [/bold #F5E6D3]")
                    log.write(f"[dim]{content}[/dim]")
                    log.write(f"[dim]  相关度: {relevance:.2f} • {timestamp}[/dim]")
                    log.write("")
            else:
                log.write("[dim]没有找到相关记忆[/dim]")
        except Exception as e:
            log.clear()
            log.write(f"[red]搜索失败: {e}[/red]")


class RelationshipView(Vertical):
    """关系网络视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("💭 关系网络", classes="view-title")
        yield Static("与其他实体的关系状态", classes="view-subtitle")
        yield ScrollableContainer(
            RichLog(id="relationship-list", classes="relationship-log", wrap=True, markup=True),
            classes="relationship-container"
        )
        yield Button("刷新", id="refresh-relationships", classes="refresh-button")
    
    async def on_mount(self):
        await self.load_relationships()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-relationships":
            await self.load_relationships()
    
    async def load_relationships(self):
        log = self.query_one("#relationship-list", RichLog)
        log.clear()
        if not self.client.connected:
            log.write("[dim red]等待服务连接...[/dim red]")
            return
        log.write("[dim]加载中...[/dim]")
        try:
            relationships = await self.client.call("relationship.list_all", {})
            log.clear()
            if relationships and len(relationships) > 0:
                for rel in relationships:
                    entity = rel.get("entity", "")
                    score = rel.get("score", 0)
                    last_update = rel.get("last_update", "")
                    if score > 5:
                        icon, color = "💖", "#E9A568"
                    elif score > 0:
                        icon, color = "😊", "#D4863C"
                    elif score < -5:
                        icon, color = "💔", "#D97757"
                    elif score < 0:
                        icon, color = "😐", "#8A7A66"
                    else:
                        icon, color = "👤", "#C9B89A"
                    log.write(f"[bold {color}]{icon} {entity}[/bold {color}]")
                    log.write(f"[dim]  关系值: {score:+d} • 更新于 {last_update}[/dim]")
                    log.write("")
            else:
                log.write("[dim]还没有关系记录[/dim]")
                log.write("[dim]随着交流进行，关系会自动建立[/dim]")
        except Exception as e:
            log.clear()
            log.write(f"[red]加载失败: {e}[/red]")


class AuditView(Vertical):
    """审计日志视图"""
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("view-container")
    
    def compose(self) -> ComposeResult:
        yield Static("🔍 审计日志", classes="view-title")
        yield Static("Agent 操作记录", classes="view-subtitle")
        yield ScrollableContainer(
            RichLog(id="audit-log", classes="audit-log", wrap=True, markup=True),
            classes="audit-container"
        )
        yield Button("刷新", id="refresh-audit", classes="refresh-button")
    
    async def on_mount(self):
        await self.load_audit_logs()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-audit":
            await self.load_audit_logs()
    
    async def load_audit_logs(self):
        log = self.query_one("#audit-log", RichLog)
        log.clear()
        log.write("[dim]加载中...[/dim]")
        try:
            logs = await self.client.call("system.get_audit_logs", {"limit": 50})
            log.clear()
            if logs and len(logs) > 0:
                for entry in logs:
                    timestamp = entry.get("timestamp", "")
                    operation = entry.get("operation", "")
                    risk_level = entry.get("risk_level", "low")
                    status = entry.get("status", "success")
                    details = entry.get("details", "")
                    if risk_level == "high":
                        icon, color = "🔴", "#D97757"
                    elif risk_level == "medium":
                        icon, color = "🟡", "#D4863C"
                    else:
                        icon, color = "🟢", "#A8C079"
                    status_icon = "✓" if status == "success" else "✗"
                    log.write(f"[dim]{timestamp}[/dim] [{color}]{icon}[/{color}] [bold #F5E6D3]{operation}[/bold #F5E6D3] {status_icon}")
                    if details:
                        log.write(f"  [dim]{details}[/dim]")
                    log.write("")
            else:
                log.write("[dim]暂无日志[/dim]")
        except Exception as e:
            log.clear()
            log.write(f"[red]加载失败: {e}[/red]")


class MainContent(Container):
    """主内容区容器"""
    current_view_id = reactive("chat")
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.views: Dict[str, Vertical] = {}
    
    def compose(self) -> ComposeResult:
        self.views["chat"] = ChatView(self.client, id="view-chat")
        self.views["itinerary"] = ItineraryView(self.client, id="view-itinerary")
        self.views["scenes"] = ScenePoolView(self.client, id="view-scenes")
        self.views["memory"] = MemoryView(self.client, id="view-memory")
        self.views["relationships"] = RelationshipView(self.client, id="view-relationships")
        self.views["audit"] = AuditView(self.client, id="view-audit")
        for vid, view in self.views.items():
            view.styles.display = "block" if vid == "chat" else "none"
            yield view
    
    def switch_to(self, view_id: str):
        if view_id not in self.views:
            return
        for view in self.views.values():
            view.styles.display = "none"
        self.views[view_id].styles.display = "block"
        self.current_view_id = view_id
    
    async def refresh_current_view(self):
        """刷新当前视图数据"""
        if self.current_view_id not in self.views:
            return
        view = self.views[self.current_view_id]
        # 调用视图的刷新方法
        if hasattr(view, 'on_mount'):
            await view.on_mount()


class NeoAgentApp(App):
    """Neo Agent 主应用"""
    CSS = FULL_THEME + COMMAND_PANEL_CSS
    TITLE = "Neo Agent"
    BINDINGS = [("q", "quit", "退出"), (":", "command_mode", "命令")]
    
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
            yield MainContent(self.client, id="main-content")
        yield Static("服务连接中... • 按 : 进入命令模式 • 按 q 退出", id="footer", classes="footer")
    
    async def on_mount(self):
        await self.connect_to_service()
        self.run_worker(self.periodic_status_update(), exclusive=True)
        self.event_handlers = EventHandlers(self)
        try:
            from .websocket_client import WebSocketClient
            self.ws_client = WebSocketClient()
            if await self.ws_client.connect():
                for event_type in ["scene_changed", "emotion_updated", "message_received",
                                   "schedule_triggered", "relationship_changed",
                                   "daily_itinerary_generated", "system_status_changed", "audit_logged"]:
                    self.ws_client.on(event_type, self._handle_ws_event)
        except Exception as e:
            self.log(f"WebSocket 初始化失败: {e}")
    
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
            # 连接成功后刷新当前视图
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
