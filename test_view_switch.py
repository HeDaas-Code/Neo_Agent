"""测试视图切换功能"""
from textual.app import App
from textual.pilot import Pilot
import asyncio

async def test_navigation():
    """测试侧边栏导航"""
    from neo_agent.ui.v2.app import NeoAgentTUI
    
    app = NeoAgentTUI()
    
    async with app.run_test() as pilot:
        # 等待加载
        await pilot.pause(1.0)
        
        # 测试点击"今日行程"按钮
        print("📋 测试：点击 '今日行程' 按钮")
        await pilot.click("#nav_itinerary")
        await pilot.pause(0.5)
        
        # 检查视图是否切换
        chat_view = app.query_one("#view_chat")
        itinerary_view = app.query_one("#view_itinerary")
        
        chat_hidden = "hidden" in chat_view.classes
        itinerary_hidden = "hidden" in itinerary_view.classes
        
        print(f"  对话视图隐藏: {chat_hidden}")
        print(f"  行程视图隐藏: {itinerary_hidden}")
        
        if chat_hidden and not itinerary_hidden:
            print("✓ 视图切换成功！")
        else:
            print("❌ 视图切换失败")
            print(f"  对话视图类: {chat_view.classes}")
            print(f"  行程视图类: {itinerary_view.classes}")
            print(f"  当前视图ID: {app.current_view_id}")
        
        # 测试切换到场景池
        print("\n📋 测试：点击 '场景池' 按钮")
        await pilot.click("#nav_scenes")
        await pilot.pause(0.5)
        
        scenes_view = app.query_one("#view_scenes")
        scenes_hidden = "hidden" in scenes_view.classes
        itinerary_hidden = "hidden" in itinerary_view.classes
        
        print(f"  行程视图隐藏: {itinerary_hidden}")
        print(f"  场景视图隐藏: {scenes_hidden}")
        
        if itinerary_hidden and not scenes_hidden:
            print("✓ 视图切换成功！")
        else:
            print("❌ 视图切换失败")
            print(f"  当前视图ID: {app.current_view_id}")

if __name__ == "__main__":
    asyncio.run(test_navigation())
