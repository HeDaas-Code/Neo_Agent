"""测试侧边栏导航功能"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentTUI

async def test_navigation():
    """测试导航切换"""
    app = NeoAgentTUI()
    
    async with app.run_test() as pilot:
        # 等待应用加载
        await pilot.pause(1.0)
        
        # 测试快捷键导航
        print("测试快捷键 'i' - 切换到行程视图")
        await pilot.press("i")
        await pilot.pause(0.5)
        assert app.current_view_id == "itinerary", f"Expected 'itinerary', got '{app.current_view_id}'"
        print("✓ 快捷键 'i' 工作正常")
        
        print("测试快捷键 's' - 切换到场景视图")
        await pilot.press("s")
        await pilot.pause(0.5)
        assert app.current_view_id == "scenes", f"Expected 'scenes', got '{app.current_view_id}'"
        print("✓ 快捷键 's' 工作正常")
        
        print("测试快捷键 'c' - 切换回对话视图")
        await pilot.press("c")
        await pilot.pause(0.5)
        assert app.current_view_id == "chat", f"Expected 'chat', got '{app.current_view_id}'"
        print("✓ 快捷键 'c' 工作正常")
        
        # 测试点击导航按钮
        print("\n测试点击导航按钮 '📅 今日行程'")
        await pilot.click("#nav_itinerary")
        await pilot.pause(0.5)
        assert app.current_view_id == "itinerary", f"Expected 'itinerary', got '{app.current_view_id}'"
        print("✓ 点击导航按钮工作正常")
        
        print("\n测试点击导航按钮 '🧠 记忆与知识'")
        await pilot.click("#nav_memory")
        await pilot.pause(0.5)
        assert app.current_view_id == "memory", f"Expected 'memory', got '{app.current_view_id}'"
        print("✓ 点击导航按钮工作正常")
        
        print("\n✅ 所有导航测试通过！")

if __name__ == "__main__":
    asyncio.run(test_navigation())
