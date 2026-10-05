"""测试视图切换功能"""
from textual.pilot import Pilot
from neo_agent.ui.v2.app import NeoAgentApp
import asyncio


async def test_view_switching():
    """测试点击导航按钮切换视图"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        # 等待应用加载
        await pilot.pause(0.5)
        
        # 获取主内容区
        main_content = app.query_one("#main-content")
        
        # 验证初始视图是对话
        assert main_content.current_view_id == "chat"
        print("✓ 初始视图: chat")
        
        # 点击今日行程按钮
        await pilot.click("#nav-itinerary")
        await pilot.pause(0.2)
        assert main_content.current_view_id == "itinerary"
        print("✓ 切换到: itinerary")
        
        # 点击场景池按钮
        await pilot.click("#nav-scenes")
        await pilot.pause(0.2)
        assert main_content.current_view_id == "scenes"
        print("✓ 切换到: scenes")
        
        # 点击记忆按钮
        await pilot.click("#nav-memory")
        await pilot.pause(0.2)
        assert main_content.current_view_id == "memory"
        print("✓ 切换到: memory")
        
        # 点击关系网络按钮
        await pilot.click("#nav-relationships")
        await pilot.pause(0.2)
        assert main_content.current_view_id == "relationships"
        print("✓ 切换到: relationships")
        
        # 滚动到审计日志按钮
        sidebar = app.query_one("#sidebar")
        sidebar.scroll_end(animate=False)
        await pilot.pause(0.2)
        
        # 点击审计日志按钮
        await pilot.click("#nav-audit")
        await pilot.pause(0.2)
        assert main_content.current_view_id == "audit"
        print("✓ 切换到: audit")
        
        # 滚动回顶部
        sidebar.scroll_home(animate=False)
        await pilot.pause(0.2)
        
        # 点击对话按钮返回
        await pilot.click("#nav-chat")
        await pilot.pause(0.2)
        assert main_content.current_view_id == "chat"
        print("✓ 切换回: chat")
        
        print("\n✅ 所有导航测试通过！")


if __name__ == "__main__":
    asyncio.run(test_view_switching())
