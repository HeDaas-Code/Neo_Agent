"""测试视图切换功能"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp

async def test_switch():
    """测试视图切换"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await asyncio.sleep(0.5)
        
        main_content = app.query_one("#main-content")
        print(f"初始视图: {main_content.current_view}")
        print(f"初始视图数量: {len(main_content.views)}")
        
        # 直接调用 switch_view
        print("\n直接调用 switch_view('itinerary')...")
        await app.switch_view('itinerary')
        await asyncio.sleep(0.5)
        
        print(f"切换后视图: {main_content.current_view}")
        print(f"切换后视图数量: {len(main_content.views)}")
        
        # 检查视图显示状态
        for view_id, view in main_content.views.items():
            print(f"  - {view_id}: display={view.display}")

if __name__ == "__main__":
    asyncio.run(test_switch())
