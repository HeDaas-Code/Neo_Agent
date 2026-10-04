"""测试导航点击功能"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp

async def test_navigation():
    """测试导航项点击"""
    app = NeoAgentApp()
    
    # 模拟应用启动
    async with app.run_test() as pilot:
        # 等待连接
        await asyncio.sleep(1)
        
        # 查找导航项
        nav_items = app.query("NavigationItem")
        print(f"找到 {len(nav_items)} 个导航项")
        
        for item in nav_items:
            print(f"  - {item.label_text} (view_id: {item.view_id})")
        
        # 测试点击第二个导航项（今日行程）
        if len(nav_items) > 1:
            print("\n点击 '今日行程'...")
            await pilot.click("NavigationItem", offset=(1, 0))
            await asyncio.sleep(0.5)
            
            # 检查视图是否切换
            main_content = app.query_one("#main-content")
            print(f"当前视图: {main_content.current_view}")
        
        print("\n✓ 导航测试完成")

if __name__ == "__main__":
    asyncio.run(test_navigation())
