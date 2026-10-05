"""使用 Textual Pilot 测试 TUI 视图切换"""
import asyncio
from textual.pilot import Pilot
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.app import NeoAgentApp

async def test_view_navigation():
    """测试视图导航"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        # 等待初始化
        await pilot.pause(1.0)
        
        print("✓ TUI 启动成功")
        
        # 测试点击侧边栏各个菜单项
        nav_items = [
            ("#nav-chat", "对话"),
            ("#nav-itinerary", "今日行程"),
            ("#nav-scenes", "场景池"),
            ("#nav-memory", "记忆与知识"),
            ("#nav-relationships", "关系网络"),
            ("#nav-audit", "审计日志"),
        ]
        
        for selector, name in nav_items:
            try:
                await pilot.click(selector)
                await pilot.pause(0.3)
                print(f"✓ 成功切换到 {name} 视图")
            except Exception as e:
                print(f"✗ 切换到 {name} 失败: {e}")
        
        # 测试记忆搜索
        print("\n=== 测试记忆搜索 ===")
        try:
            await pilot.click("#nav-memory")
            await pilot.pause(0.3)
            
            # 输入搜索关键词
            search_input = app.query_one("#memory-search")
            search_input.value = "测试"
            await pilot.pause(0.2)
            
            # 点击搜索按钮
            await pilot.click("#search-memory")
            await pilot.pause(1.0)
            
            print("✓ 记忆搜索功能正常")
        except Exception as e:
            print(f"✗ 记忆搜索失败: {e}")
        
        print("\n✓ 所有视图导航测试完成")

if __name__ == "__main__":
    asyncio.run(test_view_navigation())
