"""测试导航修复"""
from textual.app import App, ComposeResult
from textual.widgets import Button
from textual.containers import Vertical
from textual.message import Message


class NavButton(Button):
    """导航按钮"""
    
    class NavClicked(Message):
        def __init__(self, view_id: str):
            super().__init__()
            self.view_id = view_id
    
    def __init__(self, label: str, view_id: str):
        super().__init__(label)
        self.view_id = view_id
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.post_message(self.NavClicked(self.view_id))


class TestApp(App):
    """测试应用"""
    
    CSS = """
    Screen {
        background: #050302;
        color: #F5E6D3;
    }
    
    NavButton {
        width: 100%;
        margin: 0 0 1 0;
    }
    
    #content {
        width: 1fr;
        height: 100%;
        background: #0A0805;
        padding: 2;
    }
    """
    
    def compose(self) -> ComposeResult:
        with Vertical():
            yield NavButton("💬 对话", "chat")
            yield NavButton("📅 行程", "itinerary")
            yield NavButton("🌍 场景", "scenes")
    
    async def on_nav_button_nav_clicked(self, message: NavButton.NavClicked) -> None:
        self.notify(f"切换到: {message.view_id}", timeout=2)


if __name__ == "__main__":
    app = TestApp()
    app.run()
