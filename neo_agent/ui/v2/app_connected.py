"""Neo Agent TUI - 服务客户端版本（修复属性冲突）"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, Button, DataTable, RichLog
from textual.containers import Vertical, Horizontal, Container
from textual.reactive import reactive
from textual.message import Message
from textual import events

from neo_agent.ui.v2.client import ServiceClient
from neo_agent.ui.v2.views_connected import (
    ChatView, ItineraryView, ScenePoolView,
    MemoryView, RelationshipView, AuditView
)


class NavItem(Static):
    """导航项组件（可点击的 Static）"""
    
    can_focus = True
    
    def __init__(self, icon: str, label: str, key: str, view_id: str, **kwargs):
        display_text = f"{icon} {label}"
        super().__init__(display_text, **kwargs)
        self.icon = icon
        self.label_text = label
        self.shortcut_key = key
        self.view_id = view_id
    
    def on_click(self, event: events.Click) -> None:
        """点击事件"""
        self.post_message(Sidebar.ViewSelected(self.view_id))
    
    def on_key(self, event: events.Key) -> None:
        """键盘事件"""
        if event.key == "enter":
            self.post_message(Sidebar.ViewSelected(self.view_id))


class Sidebar(Vertical):
    """左侧导航栏"""
    
    VIEWS = [
        ("💬", "对话", "c", "chat"),
        ("📅", "今日行程", "i", "itinerary"),
        ("🌍", "场景池", "s", "scene"),
        ("🧠", "记忆与知识", "m", "memory"),
        ("💭", "关系网络", "r", "relationship"),
        ("🔍", "审计日志", "a", "audit"),
    ]
    
    selected = reactive(0)
    
    class ViewSelected(Message):
        """视图选择消息"""
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id
    
    def compose(self) -> ComposeResult:
        yield Static("[bold #E9A568]导航[/]\n", classes="sidebar-title")
        for idx, (icon, label, key, view_id) in enumerate(self.VIEWS):
            item_class = "nav-item selected" if idx == 0 else "nav-item"
            yield NavItem(icon, label, key, view_id, classes=item_class, id=f"nav-{idx}")
        
        yield Static("\n[dim #8A6B4F]设置 (命令)[/]", classes="sidebar-section")
        yield Static(":config 全局配置", classes="nav-hint")
        yield Static(":debug  开发模式", classes="nav-hint")
        yield Static(":export 导出数据", classes="nav-hint")
    
    def on_mount(self):
        """挂载时设置样式"""
        self.styles.width = "25%"
        self.styles.background = "#0A0805"
        self.styles.padding = (1, 2)
    
    def select(self, index: int):
        """选择导航项"""
        if 0 <= index < len(self.VIEWS):
            # 更新样式
            for i in range(len(self.VIEWS)):
                item = self.query_one(f"#nav-{i}", NavItem)
                if i == index:
                    item.add_class("selected")
                else:
                    item.remove_class("selected")
            
            self.selected = index


class StatusBar(Horizontal):
    """状态栏"""
    
    character_name = reactive("加载中...")
    current_scene = reactive("...")
    emotion = reactive("...")
    current_time = reactive("--:--")
    connection_status = reactive("○ 未连接")
    
    def compose(self) -> ComposeResult:
        yield Static(id="status-left")
        yield Static(id="status-right")
    
    def on_mount(self):
        self.styles.height = 1
        self.styles.background = "#101010"
        self.styles.padding = (0, 2)
        self.update_display()
    
    def watch_character_name(self, value: str):
        self.update_display()
    
    def watch_current_scene(self, value: str):
        self.update_display()
    
    def watch_emotion(self, value: str):
        self.update_display()
    
    def watch_current_time(self, value: str):
        self.update_display()
    
    def watch_connection_status(self, value: str):
        self.update_display()
    
    def update_display(self):
        """更新显示"""
        try:
            left = self.query_one("#status-left", Static)
            right = self.query_one("#status-right", Static)
            
            left.update(
                f"[bold #AFAFAF]{self.character_name}[/] • "
                f"[#E8E8E8]{self.current_scene}[/] • "
                f"[italic #707070]情绪: {self.emotion}[/] • "
                f"[#919191]{self.current_time}[/]"
            )
            
            right.update(f"[#8A8A8A]{self.connection_status}[/]")
        except:
            pass


class ContentArea(Container):
    """主内容区"""
    
    def compose(self) -> ComposeResult:
        yield Static("正在加载...", id="loading")
    
    def on_mount(self):
        self.styles.width = "75%"
        self.styles.background = "#030303"
        self.styles.padding = (1, 2)


class NeoAgentApp(App):
    """Neo Agent 主应用"""
    
    CSS = """
    /* 全局样式 */
    Screen {
        background: #050302;
    }
    
    /* 状态栏 */
    StatusBar {
        dock: top;
        height: 1;
        background: #101010;
    }
    
    #status-left {
        width: 80%;
        text-align: left;
    }
    
    #status-right {
        width: 20%;
        text-align: right;
    }
    
    /* 侧边栏 */
    Sidebar {
        width: 25%;
        background: #0A0805;
        border-right: solid #2B231C;
    }
    
    .sidebar-title {
        padding: 1 0;
        color: #E9A568;
    }
    
    .sidebar-section {
        padding: 1 0;
        color: #8A6B4F;
    }
    
    .nav-hint {
        padding: 0 2;
        color: #8A7A66;
    }
    
    /* 导航项 */
    NavItem {
        padding: 0 2;
        color: #B9B9B9;
        background: transparent;
    }
    
    NavItem:hover {
        background: #121008;
        color: #E9A568;
    }
    
    NavItem.selected {
        background: #1A1A1A;
        color: #AFAFAF;
        border-left: solid #E9A568;
    }
    
    NavItem:focus {
        background: #121008;
        border-left: solid #D4863C;
    }
    
    /* 内容区 */
    ContentArea {
        width: 75%;
        background: #030303;
    }
    
    /* 视图通用样式 */
    .view-container {
        height: 100%;
        background: #080808;
        border: solid #181812;
    }
    
    .view-title {
        padding: 1 2;
        background: #0F0F0D;
        color: #E9A568;
        text-style: bold;
    }
    
    .view-content {
        padding: 1 2;
    }
    
    /* 输入框 */
    Input {
        background: #080808;
        border: solid #1C1812;
        color: #F5E6D3;
    }
    
    Input:focus {
        border: solid #E9A568;
    }
    
    /* 按钮 */
    Button {
        background: #1C1812;
        color: #E9A568;
        border: none;
    }
    
    Button:hover {
        background: #2B231C;
        color: #D4863C;
    }
    
    Button:focus {
        background: #2B231C;
        border: solid #E9A568;
    }
    
    /* 数据表格 */
    DataTable {
        background: #080808;
        color: #C9B89A;
    }
    
    DataTable > .datatable--cursor {
        background: #1C1812;
        color: #E9A568;
    }
    
    /* 日志 */
    RichLog {
        background: #080808;
        border: solid #1C1812;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "退出"),
        ("c", "switch_view('chat')", "对话"),
        ("i", "switch_view('itinerary')", "行程"),
        ("s", "switch_view('scene')", "场景"),
        ("m", "switch_view('memory')", "记忆"),
        ("r", "switch_view('relationship')", "关系"),
        ("a", "switch_view('audit')", "审计"),
    ]
    
    def __init__(self):
        super().__init__()
        self.client = ServiceClient()
        self.views: Dict[str, Any] = {}
        self.current_view = "chat"
        self._update_task: Optional[asyncio.Task] = None
    
    def compose(self) -> ComposeResult:
        yield StatusBar(id="status-bar")
        with Horizontal():
            yield Sidebar(id="sidebar")
            yield ContentArea(id="content")
    
    async def on_mount(self):
        """应用启动"""
        # 连接服务
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.connection_status = "⟳ 连接中..."
        
        try:
            await self.client.connect()
            status_bar.connection_status = "● 已连接"
            
            # 初始化视图
            await self.init_views()
            
            # 加载初始数据
            await self.load_initial_data()
            
            # 启动定时更新
            self._update_task = asyncio.create_task(self.update_loop())
            
        except Exception as e:
            status_bar.connection_status = f"✗ 连接失败: {e}"
    
    async def init_views(self):
        """初始化所有视图"""
        content = self.query_one("#content", ContentArea)
        
        # 移除加载提示
        loading = content.query_one("#loading")
        loading.remove()
        
        # 创建所有视图
        self.views = {
            "chat": ChatView(self.client, id="view-chat"),
            "itinerary": ItineraryView(self.client, id="view-itinerary"),
            "scene": ScenePoolView(self.client, id="view-scene"),
            "memory": MemoryView(self.client, id="view-memory"),
            "relationship": RelationshipView(self.client, id="view-relationship"),
            "audit": AuditView(self.client, id="view-audit"),
        }
        
        # 挂载所有视图（初始隐藏除了 chat）
        for view_id, view in self.views.items():
            await content.mount(view)
            view.display = (view_id == "chat")
    
    async def load_initial_data(self):
        """加载初始数据"""
        status_bar = self.query_one("#status-bar", StatusBar)
        
        try:
            # 获取角色信息
            profile = await self.client.call("character.get_profile")
            status_bar.character_name = profile.get("name", "未知")
            
            # 获取当前场景
            scene = await self.client.call("scene.get_current")
            status_bar.current_scene = scene.get("name", "未知")
            
            # 获取情绪
            emotion = await self.client.call("emotion.get_current")
            status_bar.emotion = emotion.get("state", "平静")
            
            # 刷新当前视图
            current = self.views.get(self.current_view)
            if current and hasattr(current, 'refresh_data'):
                await current.refresh_data()
                
        except Exception as e:
            self.notify(f"加载数据失败: {e}", severity="error")
    
    async def update_loop(self):
        """定时更新循环"""
        while True:
            await asyncio.sleep(5)
            
            # 更新时间
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.current_time = datetime.now().strftime("%H:%M")
            
            # 刷新当前视图
            try:
                current = self.views.get(self.current_view)
                if current and hasattr(current, 'refresh_data'):
                    await current.refresh_data()
            except:
                pass
    
    def action_switch_view(self, view_id: str):
        """切换视图"""
        if view_id in self.views:
            # 隐藏所有视图
            for vid, view in self.views.items():
                view.display = (vid == view_id)
            
            self.current_view = view_id
            
            # 更新侧边栏选择
            sidebar = self.query_one("#sidebar", Sidebar)
            for idx, (_, _, _, vid) in enumerate(Sidebar.VIEWS):
                if vid == view_id:
                    sidebar.select(idx)
                    break
            
            # 立即刷新新视图
            view = self.views[view_id]
            if hasattr(view, "refresh_data"):
                asyncio.create_task(view.refresh_data())
    
    def on_sidebar_view_selected(self, message: Sidebar.ViewSelected):
        """响应侧边栏选择"""
        self.action_switch_view(message.view_id)
    
    async def on_unmount(self):
        """应用退出"""
        if self._update_task:
            self._update_task.cancel()
        
        await self.client.disconnect()


def main():
    """主入口"""
    app = NeoAgentApp()
    app.run()


if __name__ == "__main__":
    main()
