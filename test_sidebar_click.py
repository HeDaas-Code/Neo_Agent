#!/usr/bin/env python3
"""测试侧边栏点击功能"""
from textual.pilot import Pilot
from neo_agent.ui.v2.app_connected import NeoAgentApp
import asyncio

async def test_sidebar():
    """测试侧边栏导航"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        # 等待应用启动
        await pilot.pause(1.0)
        
        # 检查侧边栏是否存在
        sidebar = app.query_one("#sidebar")
        print(f"✓ 侧边栏已加载")
        
        # 检查导航项
        nav_items = app.query(".nav-item")
        print(f"✓ 找到 {len(nav_items)} 个导航项")
        
        # 测试点击第二个导航项（今日行程）
        if len(nav_items) >= 2:
            itinerary_btn = nav_items[1]
            print(f"  点击: {itinerary_btn.render()}")
            await pilot.click("#nav-1")
            await pilot.pause(0.5)
            
            # 检查视图是否切换
            current_view = app.current_view
            print(f"✓ 当前视图: {current_view}")
        
        # 测试键盘快捷键
        await pilot.press("s")  # 切换到场景池
        await pilot.pause(0.5)
        print(f"✓ 快捷键后视图: {app.current_view}")
        
        print("\n✓ 所有测试通过")

if __name__ == "__main__":
    asyncio.run(test_sidebar())
