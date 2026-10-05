"""测试核心导航功能"""
from textual.pilot import Pilot
from neo_agent.ui.v2.app import NeoAgentApp
import asyncio


async def test_core_navigation():
    """测试核心视图导航"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause(0.5)
        
        main_content = app.query_one("#main-content")
        
        # 测试核心视图切换
        views = [
            ("chat", "对话"),
            ("itinerary", "今日行程"),
            ("scenes", "场景池"),
            ("memory", "记忆与知识"),
            ("relationships", "关系网络"),
        ]
        
        for view_id, view_name in views:
            await pilot.click(f"#nav-{view_id}")
            await pilot.pause(0.2)
            
            if main_content.current_view_id == view_id:
                print(f"✓ {view_name}: 切换成功")
            else:
                print(f"✗ {view_name}: 切换失败 (当前: {main_content.current_view_id})")
                return False
        
        print("\n✅ 核心导航功能正常！")
        return True


if __name__ == "__main__":
    result = asyncio.run(test_core_navigation())
    exit(0 if result else 1)
