"""Neo Agent TUI v2 主应用 - 修复导航点击"""
import asyncio
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Footer, RichLog, Input, Button, DataTable, Label
from textual.reactive import reactive
from textual.message import Message

from .client import AgentClient
from .theme import FULL_THEME


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
        
        status_widget = self.query_one("#status-content", Static)
        status_widget.update(content)


class ViewSwitch(Message):
    """视图切换消息"""
    def __init__(self, view_id: str):
        self.view_id = view_id
        super().__init__()


class NavigationItem(Button):
    """导航项按钮"""
    
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.view_id = view_id
        self.variant = "default"
        self.classes = "nav-item"


class Sidebar(Vertical):
    """左侧导航栏"""
    
    def compose(self) -> ComposeResult:
        yield Static("", classes="nav-section-header")
        yield NavigationItem("💬 对话", "chat", id="nav-chat")
        yield NavigationItem("📅 今日行程", "itinerary", id="nav-itinerary")
        yield NavigationItem("🌍 场景池", "scenes", id="nav-scenes")
        yield NavigationItem("🧠 记忆与知识", "memory", id="nav-memory")
        yield NavigationItem("💭 关系网络", "relationships", id="nav-relationships")
        yield NavigationItem("🔍 审计日志", "audit", id="nav-audit")
        yield Static("─── 设置 ───", classes="nav-section-header")
        yield Static(":config 全局配置", classes="nav-hint")
        yield Static(":debug  开发模式", classes="nav-hint")
        yield Static(":export 导出数据", classes="nav-hint")


# ============ 视图组件 ============

class ChatView(Vertical):
    """对话视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.classes = "view-container"
    
    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", classes="chat-log", wrap=True, markup=True)
        with Horizontal(classes="chat-input-container"):
            yield Input(placeholder="输入消息... (Ctrl+Enter 发送)", id="chat-input", classes="chat-input")
            yield Button("发送", variant="primary", id="send-button")
    
    async def on_mount(self):
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold $accent-primary]欢迎使用 Neo Agent！[/bold $accent-primary]")
        log.write("[dim]正在加载历史消息...[/dim]")
        
        # 加载历史
        try:
            history = await self.client.call("session.get_history", {"limit": 20})
            if history:
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    timestamp = msg.get("timestamp", "")
                    
                    if role == "user":
                        log.write(f"[bold $text-primary]用户:[/bold $text-primary] {content}")
                    else:
                        log.write(f"[bold $accent-primary]林依:[/bold $accent-primary] {content}")
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
        
        # 清空输入
        input_widget.value = ""
        
        # 显示用户消息
        log.write(f"[bold $text-primary]用户:[/bold $text-primary] {user_msg}")
        log.write("[dim]林依正在思考...[/dim]")
        
        try:
            result = await self.client.call("session.send_message", {"text": user_msg})
            reply = result.get("reply", "")
            emotion = result.get("emotion", {})
            
            log.write(f"[bold $accent-primary]林依:[/bold $accent-primary] {reply}")
            
            if emotion:
                emotion_str = f"{emotion.get('state', '')} ({emotion.get('intensity', 0):.1f})"
                log.write(f"[dim]情绪: {emotion_str}[/dim]")
        
        except Exception as e:
            log.write(f"[bold red]发送失败:[/bold red] {e}")


class ItineraryView(Vertical):
    """今日行程视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.classes = "view-container"
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]今日行程[/bold $accent-primary]", classes="view-title")
        yield DataTable(id="itinerary-table", classes="data-table")
        yield Button("刷新", id="refresh-itinerary", classes="action-button")
    
    async def on_mount(self):
        await self.load_itinerary()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "refresh-itinerary":
            await self.load_itinerary()
    
    async def load_itinerary(self):
        table = self.query_one("#itinerary-table", DataTable)
        table.clear(columns=True)
        table.add_columns("时间", "活动", "地点", "类型")
        
        try:
            itinerary = await self.client.call("schedule.get_today_itinerary", {})
            if itinerary:
                for item in itinerary:
                    time_str = item.get("time", "")
                    activity = item.get("activity", "")
                    location = item.get("location", "")
                    type_str = item.get("type", "personal")
                    
                    table.add_row(time_str, activity, location, type_str)
            else:
                table.add_row("--:--", "今日暂无安排", "", "")
        except Exception as e:
            table.add_row("错误", str(e), "", "")


class ScenePoolView(Vertical):
    """场景池视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.classes = "view-container"
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]场景池[/bold $accent-primary]", classes="view-title")
        yield DataTable(id="scenes-table", classes="data-table")
        with Vertical(id="scene-detail", classes="detail-panel"):
            yield Static("[bold]当前场景[/bold]", classes="detail-title")
            yield Static("", id="scene-description", classes="detail-content")
    
    async def on_mount(self):
        await self.load_scenes()
        await self.load_current_scene()
    
    async def load_scenes(self):
        table = self.query_one("#scenes-table", DataTable)
        table.clear(columns=True)
        table.add_columns("地点", "访问次数", "最后访问")
        
        try:
            scenes = await self.client.call("scene.list_pool", {})
            if scenes:
                for scene in scenes:
                    name = scene.get("name", "未命名")
                    visits = scene.get("visits", 0)
                    last_visit = scene.get("last_visit", "从未")
                    table.add_row(name, str(visits), last_visit)
        except Exception as e:
            table.add_row("错误", str(e), "")
    
    async def load_current_scene(self):
        desc_widget = self.query_one("#scene-description", Static)
        try:
            scene = await self.client.call("scene.get_current", {})
            location = scene.get("location", "未知")
            area = scene.get("area", "")
            description = scene.get("description", "")
            
            text = f"[bold]{location}[/bold]"
            if area:
                text += f" - {area}"
            if description:
                text += f"\n\n{description}"
            
            desc_widget.update(text)
        except Exception as e:
            desc_widget.update(f"[red]加载失败: {e}[/red]")


class MemoryView(Vertical):
    """记忆与知识视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.classes = "view-container"
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]记忆与知识[/bold $accent-primary]", classes="view-title")
        with Horizontal(classes="search-bar"):
            yield Input(placeholder="搜索记忆...", id="memory-search", classes="search-input")
            yield Button("搜索", id="search-memory", variant="primary")
        yield RichLog(id="memory-results", classes="results-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.load_recent_memories()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "search-memory":
            await self.search_memories()
    
    async def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "memory-search":
            await self.search_memories()
    
    async def load_recent_memories(self):
        log = self.query_one("#memory-results", RichLog)
        log.clear()
        log.write("[dim]最近的记忆：[/dim]\n")
        
        try:
            memories = await self.client.call("memory.search", {"query": "", "limit": 10})
            if memories:
                for mem in memories:
                    content = mem.get("content", "")
                    timestamp = mem.get("timestamp", "")
                    log.write(f"[bold]{timestamp}[/bold]: {content}\n")
        except Exception as e:
            log.write(f"[red]加载失败: {e}[/red]")
    
    async def search_memories(self):
        input_widget = self.query_one("#memory-search", Input)
        log = self.query_one("#memory-results", RichLog)
        
        query = input_widget.value.strip()
        if not query:
            await self.load_recent_memories()
            return
        
        log.clear()
        log.write(f"[dim]搜索: {query}[/dim]\n")
        
        try:
            memories = await self.client.call("memory.search", {"query": query, "limit": 20})
            if memories:
                for mem in memories:
                    content = mem.get("content", "")
                    score = mem.get("score", 0.0)
                    log.write(f"[bold]相关度 {score:.2f}[/bold]: {content}\n")
            else:
                log.write("[dim]未找到相关记忆[/dim]")
        except Exception as e:
            log.write(f"[red]搜索失败: {e}[/red]")


class RelationshipView(Vertical):
    """关系网络视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.classes = "view-container"
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]关系网络[/bold $accent-primary]", classes="view-title")
        yield DataTable(id="relationships-table", classes="data-table")
    
    async def on_mount(self):
        await self.load_relationships()
    
    async def load_relationships(self):
        table = self.query_one("#relationships-table", DataTable)
        table.clear(columns=True)
        table.add_columns("对象", "亲密度", "最后互动", "状态")
        
        try:
            relationships = await self.client.call("relationship.list_all", {})
            if relationships:
                for rel in relationships:
                    entity = rel.get("entity", "未知")
                    score = rel.get("score", 0)
                    last_interaction = rel.get("last_interaction", "从未")
                    status = rel.get("status", "")
                    
                    table.add_row(entity, str(score), last_interaction, status)
            else:
                table.add_row("暂无", "", "", "")
        except Exception as e:
            table.add_row("错误", str(e), "", "")


class AuditView(Vertical):
    """审计日志视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.classes = "view-container"
    
    def compose(self) -> ComposeResult:
        yield Static("[bold $accent-primary]审计日志[/bold $accent-primary]", classes="view-title")
        with Horizontal(classes="filter-bar"):
            yield Button("全部", id="filter-all", variant="primary")
            yield Button("高风险", id="filter-high-risk")
            yield Button("操作", id="filter-actions")
        yield RichLog(id="audit-log", classes="results-log", wrap=True, markup=True)
    
    async def on_mount(self):
        await self.load_audit_logs()
    
    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id.startswith("filter-"):
            filter_type = event.button.id.replace("filter-", "")
            await self.load_audit_logs(filter_type)
    
    async def load_audit_logs(self, filter_type: str = "all"):
        log = self.query_one("#audit-log", RichLog)
        log.clear()
        log.write(f"[dim]过滤器: {filter_type}[/dim]\n")
        
        try:
            logs = await self.client.call("system.get_audit_logs", {"filter": filter_type, "limit": 50})
            if logs:
                for entry in logs:
                    timestamp = entry.get("timestamp", "")
                    risk_level = entry.get("risk_level", "low")
                    action = entry.get("action", "")
                    details = entry.get("details", "")
                    
                    risk_color = {
                        "high": "red",
                        "medium": "yellow",
                        "low": "green"
                    }.get(risk_level, "white")
                    
                    log.write(f"[bold {risk_color}][{risk_level.upper()}][/bold {risk_color}] "
                             f"{timestamp} - {action}")
                    if details:
                        log.write(f"  [dim]{details}[/dim]\n")
            else:
                log.write("[dim]暂无日志[/dim]")
        except Exception as e:
            log.write(f"[red]加载失败: {e}[/red]")


# ============ 主内容区 ============

class MainContent(Container):
    """主内容区容器"""
    
    current_view_id = reactive("chat")
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.views = {}
    
    def compose(self) -> ComposeResult:
        # 预先创建所有视图
        self.views["chat"] = ChatView(self.client)
        self.views["itinerary"] = ItineraryView(self.client)
        self.views["scenes"] = ScenePoolView(self.client)
        self.views["memory"] = MemoryView(self.client)
        self.views["relationships"] = RelationshipView(self.client)
        self.views["audit"] = AuditView(self.client)
        
        # 只显示对话视图
        for vid, view in self.views.items():
            if vid == "chat":
                view.styles.display = "block"
            else:
                view.styles.display = "none"
            yield view
    
    async def switch_to(self, view_id: str):
        """切换到指定视图"""
        if view_id not in self.views:
            self.app.notify(f"未知视图: {view_id}", severity="warning")
            return
        
        # 隐藏所有视图
        for view in self.views.values():
            view.styles.display = "none"
        
        # 显示目标视图
        self.views[view_id].styles.display = "block"
        self.current_view_id = view_id
        self.app.notify(f"切换到: {view_id}", severity="information")


# ============ 主应用 ============

class NeoAgentApp(App):
    """Neo Agent 主应用"""
    
    CSS = FULL_THEME
    TITLE = "Neo Agent"
    BINDINGS = [
        ("q", "quit", "退出"),
        (":", "command_mode", "命令"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
        self.connected = False
    
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar", classes="sidebar")
            yield MainContent(self.client, id="main-content")
        yield Static("服务连接中... • 按 : 进入命令模式 • 按 q 退出", id="footer", classes="footer")
    
    async def on_mount(self):
        """应用启动时连接服务"""
        try:
            connected = await self.client.connect(timeout=3.0)
            if connected:
                self.connected = True
                await self.update_status()
                self.query_one("#footer", Static).update(
                    "服务运行中 • 按 : 进入命令模式 • 按 q 退出"
                )
                self.notify("已连接到服务", severity="information")
            else:
                self.query_one("#footer", Static).update(
                    "服务连接失败 • 请先运行: python main.py start"
                )
                self.notify("服务连接失败", severity="error")
        except Exception as e:
            self.notify(f"连接错误: {e}", severity="error")
    
    async def update_status(self):
        """更新状态栏"""
        try:
            profile = await self.client.call("character.get_profile", {})
            context = await self.client.call("session.get_context", {})
            
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.character_name = profile.get("name", "林依")
            
            scene = context.get("current_scene", {})
            if scene:
                location = scene.get("location", "")
                area = scene.get("area", "")
                status_bar.scene_info = f"{location}-{area}" if area else location
            
            emotion = context.get("emotion", {})
            if emotion:
                state = emotion.get("state", "")
                intensity = emotion.get("intensity", 0)
                status_bar.emotion = f"情绪:{state}"
        
        except Exception as e:
            self.notify(f"状态更新失败: {e}", severity="warning")
    
    async def on_button_pressed(self, event: Button.Pressed):
        """统一处理按钮点击"""
        # 检查是否是导航按钮
        if isinstance(event.button, NavigationItem):
            view_id = event.button.view_id
            main_content = self.query_one("#main-content", MainContent)
            await main_content.switch_to(view_id)
    
    async def action_command_mode(self):
        """命令模式（未实现）"""
        self.notify("命令模式开发中...", severity="information")
    
    async def on_unmount(self):
        """应用退出时断开连接"""
        if self.connected:
            await self.client.disconnect()


def run_tui():
    """启动 TUI"""
    app = NeoAgentApp()
    app.run()
