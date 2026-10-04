"""测试真实点击"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp, NavigationItem

async def test_real_navigation():
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await asyncio.sleep(0.5)
        
        # 使用 CSS 选择器点击
        print("尝试点击第二个导航项...")
        nav_items = app.query(NavigationItem)
        
        if len(nav_items) > 1:
            # 直接在导航项上调用 click
            await pilot.click(NavigationItem, offset=(1, 0))
            await asyncio.sleep(0.5)
            
            main_content = app.query_one("#main-content")
            print(f"当前视图: {main_content.current_view}")
            
            # 如果还是不行，试试直接用坐标点击
            if main_content.current_view == "chat":
                print("\n尝试用坐标点击...")
                # 获取第二个导航项的位置
                item = nav_items[1]
                region = item.region
                print(f"导航项位置: {region}")
                
                # 点击导航项中心
                await pilot.click(region.x + region.width // 2, region.y + region.height // 2)
                await asyncio.sleep(0.5)
                
                print(f"坐标点击后视图: {main_content.current_view}")

if __name__ == "__main__":
    asyncio.run(test_real_navigation())
