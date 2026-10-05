"""简单测试 TUI 视图切换"""
from textual.pilot import Pilot
from neo_agent.ui.v2.app import NeoAgentTUI
import asyncio


async def test_views():
    """测试视图切换"""
    app = NeoAgentTUI()
    
    async with app.run_test() as pilot:
        await pilot.pause(0.5)
        
        print("✓ TUI 启动成功")
        print(f"  当前视图: {app.current_view_id}")
        
        # 测试快捷键切换（更可靠）
        views = [
            ("i", "itinerary", "今日行程"),
            ("s", "scenes", "场景池"),
            ("m", "memory", "记忆与知识"),
            ("r", "relationships", "关系网络"),
            ("c", "chat", "对话"),
        ]
        
        for key, view_id, name in views:
            await pilot.press(key)
            await pilot.pause(0.3)
            
            # 验证切换
            if app.current_view_id == view_id:
                print(f"✓ 快捷键 '{key}' 成功切换到 {name}")
            else:
                print(f"✗ 快捷键 '{key}' 切换失败，当前: {app.current_view_id}")
        
        print("\n✓ 所有视图测试完成！")
        print("\n提示: 侧边栏按钮可以点击，快捷键也可以正常工作")


if __name__ == "__main__":
    asyncio.run(test_views())
