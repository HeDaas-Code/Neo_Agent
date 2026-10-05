"""
Neo Agent TUI v2 - 服务-客户端架构
琥珀主题 + 现代控制台设计
"""
import asyncio
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Header, Footer, Button, Input, RichLog
from textual.message import Message
from textual import events

from neo_agent.ui.v2.client import AgentClient
from neo_agent.ui.v2.theme import AMBER_THEME
from neo_agent.ui.v2.commands import CommandPalette
from neo_agent.ui.v2.views import (
    ItineraryView,
    ScenePoolView,
    MemoryView,
    RelationshipView,
    AuditView
)


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
        
        message = input_widget.value.strip()
        if not message:
            return
        
        # 清空输入框
        input_widget.value = ""
        
        # 显示用户消息
        log.write(f"[bold #F5E6D3]用户:[/bold #F5E6D3] {message}")
        log.write("[dim]思考中...[/dim]")
        
        try:
            result = await self.client.call("session.send_message", {"text": message})
            reply = result.get("reply", "")
            emotion = result.get("emotion", {})
            scene = result.get("scene", {})
            
            # 显示回复
            log.write(f"[bold #E9A568]林依:[/bold #E9A568] {reply}")
            
            # 更新顶栏信息（通过事件）
            self.post_message(self.ChatUpdated(emotion, scene))
            
        except Exception as e:
            log.write(f"[dim red]发送失败: {e}[/dim red]")
    
    class ChatUpdated(Message):
        def __init__(self, emotion: dict, scene: dict):
            super().__init__()
            self.emotion = emotion
            self.scene = scene


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
        if hasattr(current, 'refresh_itinerary'):
            await current.refresh_itinerary()
        elif hasattr(current, 'refresh_scenes'):
            await current.refresh_scenes()
        elif hasattr(current, 'refresh_relationships'):
            await current.refresh_relationships()
        elif hasattr(current, 'refresh_audit'):
            await current.refresh_audit()


class StatusBar(Static):
    """底部状态栏"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection_status = "连接中..."
    
    def update_status(self, connected: bool, scene: str = "", emotion: str = ""):
        if connected:
            status_parts = ["服务已连接"]
            if scene:
                status_parts.append(f"场景: {scene}")
            if emotion:
                status_parts.append(f"情绪: {emotion}")
            status_parts.append("按 : 进入命令模式 • 按 q 退出")
            self.update(" • ".join(status_parts))
        else:
            self.update("连接中...")


class TopBar(Static):
    """顶部状态栏"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.character_name = "林依"
        self.scene_text = "在家-客厅"
        self.emotion_text = "平静"
        self.time_text = ""
    
    def compose(self) -> ComposeResult:
        yield Static(self.render_content(), id="topbar-content")
    
    def render_content(self) -> str:
        import time
        self.time_text = time.strftime("%H:%M")
        return f"{self.character_name} • {self.scene_text} • 情绪:{self.emotion_text} • {self.time_text}"
    
    def update_info(self, scene: str = None, emotion: str = None):
        if scene:
            self.scene_text = scene
        if emotion:
            self.emotion_text = emotion
        content = self.query_one("#topbar-content", Static)
        content.update(self.render_content())


class NeoAgentTUI(App):
    """Neo Agent 主应用"""
    
    CSS = AMBER_THEME
    
    BINDINGS = [
        Binding("q", "quit", "退出", priority=True),
        Binding("colon", "command_mode", "命令模式", key_display=":"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
    
    def compose(self) -> ComposeResult:
        yield TopBar(id="topbar", classes="topbar")
        with Horizontal(id="main-layout"):
            yield Sidebar(id="sidebar", classes="sidebar")
            yield MainContent(self.client, id="main-content", classes="main-content")
        yield StatusBar(id="statusbar", classes="statusbar")
    
    async def on_mount(self):
        """应用启动"""
        # 连接服务
        await self.client.connect()
        
        # 更新状态栏
        statusbar = self.query_one("#statusbar", StatusBar)
        statusbar.update_status(self.client.connected)
        
        # 获取初始状态
        if self.client.connected:
            try:
                context = await self.client.call("session.get_context", {})
                scene = context.get("current_scene", {})
                emotion = context.get("emotion", {})
                
                topbar = self.query_one("#topbar", TopBar)
                scene_text = f"{scene.get('location', '未知')}-{scene.get('area', '未知')}"
                emotion_text = emotion.get("state", "平静")
                topbar.update_info(scene=scene_text, emotion=emotion_text)
                statusbar.update_status(True, scene_text, emotion_text)
            except:
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
            await self.toggle_debug_mode(args)
        elif command == "export":
            await self.export_data(args)
        elif command == "import":
            await self.import_data(args)
    
    async def open_config_panel(self):
        """打开配置面板（TODO）"""
        pass
    
    async def toggle_debug_mode(self, args):
        """切换调试模式"""
        try:
            mode = args[0] if args else "on"
            enabled = mode.lower() in ["on", "true", "1"]
            await self.client.call("system.set_debug", {"enabled": enabled})
            self.notify(f"调试模式已{'开启' if enabled else '关闭'}")
        except Exception as e:
            self.notify(f"操作失败: {e}", severity="error")
    
    async def export_data(self, args):
        """导出数据（TODO）"""
        self.notify("导出功能开发中...")
    
    async def import_data(self, args):
        """导入数据（TODO）"""
        self.notify("导入功能开发中...")


def run():
    """启动 TUI"""
    app = NeoAgentTUI()
    app.run()


if __name__ == "__main__":
    run()
