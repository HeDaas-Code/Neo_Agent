"""测试按钮事件"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp, NavigationItem

async def test_button_click():
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await asyncio.sleep(0.5)
        
        # 找到第二个导航项
        nav_items = app.query(NavigationItem)
        if len(nav_items) > 1:
            item = nav_items[1]
            print(f"导航项: {item.label_text}")
            print(f"view_id: {item.view_id}")
            print(f"是否有 on_button_pressed: {hasattr(item, 'on_button_pressed')}")
            
            # 直接调用按钮的 press 方法
            print("\n调用 press()...")
            item.press()
            await asyncio.sleep(0.5)
            
            main_content = app.query_one("#main-content")
            print(f"当前视图: {main_content.current_view}")

if __name__ == "__main__":
    asyncio.run(test_button_click())
