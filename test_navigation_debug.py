"""测试导航点击的调试版本"""
import asyncio
from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Static


class TestNavButton(Button):
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.view_id = view_id
        print(f"[创建] TestNavButton: {label} -> {view_id}")
    
    def on_button_pressed(self, event):
        print(f"[点击] TestNavButton.on_button_pressed: {self.view_id}")
        event.stop()
        if hasattr(self.app, 'show_view'):
            print(f"[调用] app.show_view({self.view_id})")
            self.app.show_view(self.view_id)


class TestApp(App):
    def compose(self):
        with Horizontal():
            with Vertical():
                yield TestNavButton("💬 对话", "chat")
                yield TestNavButton("📅 行程", "itinerary")
                yield TestNavButton("🌍 场景", "scenes")
            yield Static(id="content", markup=True)
    
    def on_mount(self):
        self.query_one("#content", Static).update("[bold]点击左侧按钮[/bold]")
    
    def show_view(self, view_id: str):
        print(f"[执行] show_view({view_id})")
        content = self.query_one("#content", Static)
        content.update(f"[bold cyan]当前视图: {view_id}[/bold cyan]")


if __name__ == "__main__":
    app = TestApp()
    app.run()
