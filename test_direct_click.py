"""测试直接点击导航项"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp, NavigationItem

async def test_click():
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause()
        
        print("=== 初始状态 ===")
        main_content = app.query_one("#main-content")
        print(f"当前视图: {main_content.current_view}")
        
        # 直接发送消息
        print("\n=== 直接发送 NavClicked 消息 ===")
        nav_clicked = NavigationItem.NavClicked("itinerary")
        app.post_message(nav_clicked)
        
        await pilot.pause()
        
        print(f"切换后视图: {main_content.current_view}")
        
        # 检查视图显示状态
        for view_id, view in main_content.views.items():
            print(f"  {view_id}: display={view.display}")

if __name__ == "__main__":
    asyncio.run(test_click())
