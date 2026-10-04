"""测试所有视图"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp

async def test_all_views():
    """测试所有视图切换"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await asyncio.sleep(0.5)
        
        main_content = app.query_one("#main-content")
        print(f"初始视图数量: {len(main_content.views)}")
        
        # 测试切换到每个视图
        views = ["chat", "itinerary", "scenes", "memory", "relationships", "audit"]
        
        for view_id in views:
            print(f"\n切换到 {view_id}...")
            await app.switch_view(view_id)
            await asyncio.sleep(0.3)
            
            if view_id in main_content.views:
                print(f"  ✓ {view_id} 视图已创建")
                print(f"    显示状态: {main_content.views[view_id].display}")
                print(f"    类型: {type(main_content.views[view_id]).__name__}")
            else:
                print(f"  ✗ {view_id} 视图未创建")
        
        print(f"\n最终视图数量: {len(main_content.views)}")
        print(f"当前视图: {main_content.current_view}")

if __name__ == "__main__":
    asyncio.run(test_all_views())
