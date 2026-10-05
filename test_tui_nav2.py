"""测试 TUI 导航功能 - 直接发送消息"""
import asyncio
from textual.pilot import Pilot
from neo_agent.ui.v2.app import NeoAgentApp, NavigationItem

async def test_navigation():
    app = NeoAgentApp()
    async with app.run_test() as pilot:
        # 等待应用启动
        await pilot.pause(2)
        
        # 检查初始状态
        print("=== 初始状态 ===")
        main_content = app.query_one("#main-content")
        print(f"当前视图: {main_content.current_view}")
        
        # 直接发送 NavClicked 消息
        print("\n=== 发送 NavClicked 消息 ===")
        nav_item = app.query_one("#nav-itinerary", NavigationItem)
        app.post_message(NavigationItem.NavClicked("itinerary"))
        await pilot.pause(1)
        
        print(f"当前视图: {main_content.current_view}")
        for view_id, view in main_content.views.items():
            print(f"  {view_id}: display={view.display}")

if __name__ == "__main__":
    asyncio.run(test_navigation())
