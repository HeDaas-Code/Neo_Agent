"""测试导航点击是否能切换视图"""
from textual.pilot import Pilot
import asyncio
import sys

async def test_navigation():
    from neo_agent.ui.v2.app import NeoAgentApp
    
    app = NeoAgentApp()
    async with app.run_test() as pilot:
        # 等待应用启动
        await pilot.pause(1.0)
        
        # 获取主内容区
        main_content = app.query_one("#main-content")
        print(f"初始视图: {main_content.current_view_id}")
        
        # 点击"今日行程"按钮
        itinerary_btn = app.query_one("#nav-itinerary")
        print(f"找到按钮: {itinerary_btn}")
        
        await pilot.click("#nav-itinerary")
        await pilot.pause(0.5)
        
        print(f"点击后视图: {main_content.current_view_id}")
        
        # 点击"场景池"按钮
        await pilot.click("#nav-scenes")
        await pilot.pause(0.5)
        
        print(f"再次点击后视图: {main_content.current_view_id}")
        
        # 验证视图切换
        assert main_content.current_view_id == "scenes", f"视图应该是 'scenes'，实际是 '{main_content.current_view_id}'"
        
        print("✓ 导航切换测试通过！")

if __name__ == "__main__":
    try:
        asyncio.run(test_navigation())
        sys.exit(0)
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
