"""简单的 TUI 测试"""
from textual.app import App, ComposeResult
from textual.widgets import Static, Footer
from textual.containers import Horizontal, Vertical
from textual.message import Message


class NavItem(Static):
    """导航项"""
    
    def __init__(self, text: str, view_id: str, **kwargs):
        super().__init__(text, **kwargs)
        self.view_id = view_id
        self.can_focus = True
    
    def on_click(self):
        """点击事件"""
        self.post_message(ViewSelected(self.view_id))


class ViewSelected(Message):
    """视图选择消息"""
    def __init__(self, view_id: str):
        super().__init__()
        self.view_id = view_id


class TestApp(App):
    """测试应用"""
    
    CSS = """
    NavItem {
        height: 3;
        padding: 1 2;
        background: #12100D;
        color: #C9B89A;
    }
    
    NavItem:hover {
        background: #1C1812;
        color: #E9A568;
    }
    
    #sidebar {
        width: 30%;
        background: #0A0805;
    }
    
    #content {
        width: 70%;
        background: #050302;
        padding: 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("[bold]导航[/]\n")
                yield NavItem("💬 对话", "chat", id="nav-chat")
                yield NavItem("📅 行程", "itinerary", id="nav-itinerary")
                yield NavItem("🌍 场景", "scene", id="nav-scene")
            
            yield Static("点击左侧导航项测试", id="content")
        
        yield Footer()
    
    def on_view_selected(self, message: ViewSelected):
        """处理选择"""
        content = self.query_one("#content", Static)
        content.update(f"当前视图: {message.view_id}")


if __name__ == "__main__":
    app = TestApp()
    app.run()
