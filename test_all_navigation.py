"""测试所有视图切换"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp

async def test_all_views():
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause(0.1)
        
        views = ["chat", "itinerary", "scenes", "memory", "relationships", "audit"]
        
        for view_id in views:
            print(f"\n=== 切换到 {view_id} ===")
            nav_id = f"nav-{view_id}"
            nav_item = app.query_one(f"#{nav_id}")
            nav_item.focus()
            await pilot.press("enter")
            await pilot.pause(0.1)
            
            main_content = app.query_one("#main-content")
            print(f"当前视图: {main_content.current_view}")
            
            # 检查只有目标视图可见
            for vid, view in main_content.views.items():
                if vid == view_id:
                    assert view.display == True, f"{vid} 应该可见"
                else:
                    assert view.display == False, f"{vid} 应该隐藏"
            
            print(f"✓ 视图 {view_id} 正常显示")
        
        print("\n=== 所有视图切换测试通过 ===")
        
        # 关闭客户端连接
        await app.client.close()

if __name__ == "__main__":
    asyncio.run(test_all_views())
