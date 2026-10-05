"""Neo Agent TUI - 连接服务版本"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button
from textual.containers import Horizontal, Vertical
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
import asyncio
from pathlib import Path

from .client import ServiceClient
from .views_connected import (
    ChatView, ItineraryView, ScenePoolView, 
    MemoryView, RelationshipView, AuditView
)


class StatusBar(Static):
    """顶部状态栏"""
    
    character_name = reactive("加载中...")
    current_scene = reactive("...")
    emotion = reactive("...")
    time = reactive("--:--")
    connected = reactive(False)
    
    def render(self) -> str:
        conn_icon = "●" if self.connected else "○"
        conn_text = "已连接" if self.connected else "未连接"
        
        return (
            f"[bold #E9A568]{self.character_name}[/] • "
            f"[#C9B89A]{self.current_scene}[/] • "
            f"[italic #8A6B4F]情绪: {self.emotion}[/] • "
            f"[#D4863C]{self.time}[/]     "
            f"[{'#A8C079' if self.connected else '#D97757'}]{conn_icon} {conn_text}[/]"
        )


class NavItem(Static):
    """导航项组件"""
    
    def __init__(self, icon: str, name: str, key: str, view_id: str, **kwargs):
        super().__init__(f"{icon} {name} [{key}]", **kwargs)
        self.view_id = view_id
        self.can_focus = True
    
    def on_click(self):
        """点击事件"""
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
        for idx, (icon, name, key, view_id) in enumerate(self.VIEWS):
            item_class = "nav-item selected" if idx == 0 else "nav-item"
            yield NavItem(icon, name, key, view_id, classes=item_class, id=f"nav-{idx}")
        
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
                item = self.query_one(f"#nav-{i}")
                if i == index:
                    item.add_class("selected")
                else:
                    item.remove_class("selected")
            
            self.selected = index


class NeoAgentApp(App):
    """Neo Agent 主应用（连接服务版本）"""
    
    TITLE = "Neo Agent"
    CSS_PATH = "theme.tcss"
    
    BINDINGS = [
        Binding("c", "switch_view('chat')", "对话", key_display="c"),
        Binding("i", "switch_view('itinerary')", "行程", key_display="i"),
        Binding("s", "switch_view('scene')", "场景", key_display="s"),
        Binding("m", "switch_view('memory')", "记忆", key_display="m"),
        Binding("r", "switch_view('relationship')", "关系", key_display="r"),
        Binding("a", "switch_view('audit')", "审计", key_display="a"),
        Binding("q", "quit", "退出", key_display="q"),
    ]
    
    current_view = reactive("chat")
    
    def __init__(self):
        super().__init__()
        self.client = ServiceClient()
        self.views = {}
        self._update_task = None
    
    def compose(self) -> ComposeResult:
        """组合界面"""
        yield StatusBar(id="status-bar")
        
        with Horizontal(id="main-container"):
            yield Sidebar(id="sidebar")
            
            with Vertical(id="content-area"):
                # 初始化所有视图
                self.views["chat"] = ChatView(self.client)
                self.views["itinerary"] = ItineraryView(self.client)
                self.views["scene"] = ScenePoolView(self.client)
                self.views["memory"] = MemoryView(self.client)
                self.views["relationship"] = RelationshipView(self.client)
                self.views["audit"] = AuditView(self.client)
                
                # 只显示当前视图
                for view_id, view in self.views.items():
                    view.display = (view_id == "chat")
                    yield view
        
        yield Footer()
    
    def on_mount(self):
        """应用启动"""
        # 异步连接，不阻塞 UI
        self.set_timer(0.1, self._connect_service)
    
    async def _connect_service(self):
        """连接到服务"""
        status_bar = self.query_one("#status-bar", StatusBar)
        
        try:
            # 连接服务
            await self.client.connect()
            status_bar.connected = True
            
            # 获取初始数据
            await self._refresh_status()
            
            # 启动定时更新
            self._update_task = asyncio.create_task(self._periodic_update())
            
        except Exception as e:
            status_bar.connected = False
            status_bar.character_name = f"连接失败: {str(e)[:20]}"
    
    async def _refresh_status(self):
        """刷新状态栏"""
        status_bar = self.query_one("#status-bar", StatusBar)
        
        try:
            # 获取角色信息
            profile = await self.client.get_character_profile()
            status_bar.character_name = profile.get("name", "未知")
            
            # 获取当前场景
            scene = await self.client.get_current_scene()
            location = scene.get("location", {}).get("name", "未知")
            area = scene.get("area", {}).get("name", "")
            status_bar.current_scene = f"{location}-{area}" if area else location
            
            # 获取情绪
            emotion = await self.client.get_current_emotion()
            status_bar.emotion = emotion.get("state", "平静")
            
            # 更新时间
            from datetime import datetime
            status_bar.time = datetime.now().strftime("%H:%M")
            
        except Exception as e:
            pass  # 静默失败
    
    async def _periodic_update(self):
        """定期更新状态"""
        while True:
            await asyncio.sleep(10)  # 每 10 秒更新
            try:
                await self._refresh_status()
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
