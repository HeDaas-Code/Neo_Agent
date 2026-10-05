"""测试 NavigationItem 点击事件"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp

async def test_nav_click():
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause()
        
        print("=== 查找导航项 ===")
        nav_items = app.query(type(app.query_one("#nav-itinerary")))
        print(f"找到 {len(nav_items)} 个导航项")
        
        for item in nav_items:
            print(f"  id={item.id}, view_id={item.view_id}, can_focus={item.can_focus}")
        
        print("\n=== 尝试点击 ===")
        # 方法1: 通过 pilot.click
        itinerary_nav = app.query_one("#nav-itinerary")
        print(f"目标: {itinerary_nav.id}, 位置: {itinerary_nav.region}")
        
        # 先聚焦
        itinerary_nav.focus()
        await pilot.pause()
        print(f"聚焦后: focused={app.focused}")
        
        # 尝试按回车
        await pilot.press("enter")
        await pilot.pause()
        
        main_content = app.query_one("#main-content")
        print(f"按回车后视图: {main_content.current_view}")

if __name__ == "__main__":
    asyncio.run(test_nav_click())
