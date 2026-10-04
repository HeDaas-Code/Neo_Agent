"""Neo Agent TUI v2 主应用"""
import asyncio
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static, Footer, RichLog, Input, Button
from textual.reactive import reactive

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


class NavigationItem(Button):
    """导航项"""
    
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.label_text = label
        self.view_id = view_id
        self.variant = "default"
        self.add_class("nav-item")
    
    def on_button_pressed(self, event: Button.Pressed):
        """处理自己的点击事件"""
        event.stop()  # 阻止冒泡
        # 获取应用并调用 switch_view
        if hasattr(self.app, 'switch_view'):
            self.app.run_worker(self.app.switch_view(self.view_id))


class Sidebar(Vertical):
    """左侧导航栏"""
    
    def compose(self) -> ComposeResult:
        yield Static("", classes="nav-section-header")
        yield NavigationItem("💬 对话", "chat")
        yield NavigationItem("📅 今日行程", "itinerary")
        yield NavigationItem("🌍 场景池", "scenes")
        yield NavigationItem("🧠 记忆与知识", "memory")
        yield NavigationItem("💭 关系网络", "relationships")
        yield NavigationItem("🔍 审计日志", "audit")
        yield Static("─── 设置 ───", classes="nav-section-header")
        yield Static(":config 全局配置", classes="nav-item")
        yield Static(":debug  开发模式", classes="nav-item")
        yield Static(":export 导出数据", classes="nav-item")


class ChatView(Vertical):
    """对话视图"""
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("chat-container")
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield RichLog(id="chat-log", classes="chat-log", wrap=True, markup=True)
            with Horizontal(classes="chat-input-container"):
                yield Input(placeholder="输入消息... (Ctrl+Enter 发送)", id="chat-input")
                yield Button("发送", variant="primary", id="send-button")
    
    async def on_mount(self):
        """挂载时初始化"""
        self.query_one("#chat-log", RichLog).write("欢迎使用 Neo Agent！")
        self.query_one("#chat-log", RichLog).write("[dim]正在连接服务...[/dim]")
    
    async def on_input_submitted(self, event: Input.Submitted):
        """处理输入提交"""
        if event.input.id == "chat-input":
            await self.send_message()
    
    async def on_button_pressed(self, event: Button.Pressed):
        """处理按钮点击"""
        # 只处理发送按钮
        """处理按钮点击"""
        if event.button.id == "send-button":
            await self.send_message()
    
    async def send_message(self):
        """发送消息"""
        input_widget = self.query_one("#chat-input", Input)
        log_widget = self.query_one("#chat-log", RichLog)
        
        message = input_widget.value.strip()
        if not message:
            return
        
        # 清空输入框
        input_widget.value = ""
        
        # 显示用户消息
        log_widget.write(f"[bold $accent-primary]你:[/bold $accent-primary] {message}")
        
        # 显示加载状态
        log_widget.write("[dim]思考中...[/dim]")
        
        try:
            # 异步发送消息
            result = await self.client.send_message(message)
            
            # 移除"思考中"
            # （Textual RichLog 不支持删除最后一行，这里暂时跳过）
            
            # 显示回复
            reply = result.get("reply", "")
            emotion = result.get("emotion", {})
            
            emotion_str = ""
            if emotion:
                emotion_state = emotion.get("state", "")
                if emotion_state:
                    emotion_str = f" [dim]({emotion_state})[/dim]"
            
            log_widget.write(f"[bold $accent-secondary]林依:[/bold $accent-secondary]{emotion_str} {reply}")
            
        except Exception as e:
            log_widget.write(f"[bold $status-error]错误:[/bold $status-error] {str(e)}")


class MainContent(Container):
    """主内容区"""
    
    current_view = reactive("chat")
    
    def __init__(self, client: AgentClient, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.add_class("main-content")
        self.views = {}
    
    def compose(self) -> ComposeResult:
        # 初始化所有视图
        self.views["chat"] = ChatView(self.client)
        yield self.views["chat"]
    
    async def switch_to(self, view_id: str):
        """切换视图"""
        # 隐藏所有视图
        for view in self.views.values():
            view.display = False
        
        # 如果视图不存在，创建占位符
        if view_id not in self.views:
            placeholder = Static(
                f"[bold $accent-primary]{view_id.upper()} 视图[/bold $accent-primary]\n\n"
                f"[dim]该功能正在开发中...[/dim]",
                classes="placeholder-view"
            )
            placeholder.styles.padding = (2, 4)
            placeholder.styles.text_align = "center"
            self.views[view_id] = placeholder
            await self.mount(placeholder)
        
        # 显示目标视图
        self.views[view_id].display = True
        self.current_view = view_id


class NeoAgentApp(App):
    """Neo Agent 主应用"""
    
    CSS = FULL_THEME
    TITLE = "Neo Agent"
    
    def __init__(self):
        super().__init__()
        self.client = AgentClient()
        self.connected = False
    
    def on_button_pressed(self, event):
        """处理按钮点击"""
        # 检查是否是 NavigationItem
        if isinstance(event.button, NavigationItem):
            self.run_worker(self.switch_view(event.button.view_id))
    
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal():
            yield Sidebar(classes="sidebar")
            yield MainContent(self.client, id="main-content")
        yield Static("服务连接中... • 按 : 进入命令模式 • 按 q 退出", classes="footer")
    
    async def on_mount(self):
        """应用启动"""
        # 尝试连接服务
        try:
            connected = await self.client.connect(timeout=3.0)
            if connected:
                self.connected = True
                await self.update_status_from_service()
                
                # 更新底栏
                footer = self.query_one(".footer", Static)
                footer.update("服务运行中 • 按 : 进入命令模式 • 按 q 退出")
                
                # 更新对话日志
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write("[bold $status-success]✓ 已连接到服务[/bold $status-success]")
            else:
                # 连接失败
                footer = self.query_one(".footer", Static)
                footer.update("[bold $status-error]✗ 无法连接到服务[/bold $status-error] • 按 q 退出")
                
                chat_log = self.query_one("#chat-log", RichLog)
                chat_log.write("[bold $status-error]✗ 无法连接到服务，请确保服务已启动[/bold $status-error]")
        except Exception as e:
            footer = self.query_one(".footer", Static)
            footer.update(f"[bold $status-error]连接错误: {str(e)}[/bold $status-error]")
    
    async def update_status_from_service(self):
        """从服务更新状态栏"""
        try:
            context = await self.client.get_context()
            character = context.get("character", {})
            scene = context.get("current_scene", {})
            emotion = context.get("emotion", {})
            
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.character_name = character.get("name", "林依")
            
            scene_location = scene.get("location", "")
            scene_area = scene.get("area", "")
            if scene_location:
                status_bar.scene_info = f"{scene_location}-{scene_area}" if scene_area else scene_location
            
            emotion_state = emotion.get("state", "")
            if emotion_state:
                status_bar.emotion = f"情绪:{emotion_state}"
            
        except Exception:
            pass
    
    async def switch_view(self, view_id: str):
        """切换主内容视图"""
        main_content = self.query_one("#main-content", MainContent)
        await main_content.switch_to(view_id)
    
    async def on_unmount(self):
        """应用退出"""
        if self.connected:
            await self.client.disconnect()


def run_tui():
    """启动 TUI"""
    app = NeoAgentApp()
    app.run()
