"""测试导航修复"""
from textual.app import App, ComposeResult
from textual.widgets import Button, Static
from textual.containers import Vertical, Horizontal


class TestNav(Button):
    def __init__(self, label: str, view_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.view_id = view_id


class TestApp(App):
    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield TestNav("View 1", "v1", id="nav-1")
                yield TestNav("View 2", "v2", id="nav-2")
            with Vertical():
                yield Static("Content", id="content")
    
    async def on_button_pressed(self, event: Button.Pressed):
        if isinstance(event.button, TestNav):
            content = self.query_one("#content", Static)
            content.update(f"Switched to: {event.button.view_id}")
            self.notify(f"View: {event.button.view_id}")


if __name__ == "__main__":
    TestApp().run()
