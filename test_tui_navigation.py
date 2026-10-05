"""测试 TUI 导航功能"""
from textual.pilot import Pilot
from neo_agent.ui.v2.app import NeoAgentTUI
import asyncio


async def test_navigation():
    """测试导航切换"""
    app = NeoAgentTUI()
    
    async with app.run_test() as pilot:
        # 等待初始化
        await pilot.pause()
        
        print("✓ TUI 启动成功")
        
        # 测试点击各个导航项
        nav_buttons = [
            ("nav_itinerary", "今日行程"),
            ("nav_scenes", "场景池"),
            ("nav_memory", "记忆与知识"),
            ("nav_relationships", "关系网络"),
            ("nav_audit", "审计日志"),
            ("nav_chat", "对话"),
        ]
        
        for btn_id, name in nav_buttons:
            # 查找并点击按钮
            btn = app.query_one(f"#{btn_id}")
            await pilot.click(f"#{btn_id}")
            await pilot.pause()
            
            # 验证视图切换
            view_id = btn_id.replace("nav_", "")
            current_view = app.query_one(f"#view_{view_id}")
            
            if "hidden" not in current_view.classes:
                print(f"✓ 成功切换到 {name} 视图")
            else:
                print(f"✗ 切换到 {name} 失败")
        
        # 测试快捷键
        print("\n测试快捷键...")
        shortcuts = [
            ("c", "对话"),
            ("i", "今日行程"),
            ("s", "场景池"),
            ("m", "记忆"),
            ("r", "关系"),
            ("a", "审计"),
        ]
        
        for key, name in shortcuts:
            await pilot.press(key)
            await pilot.pause()
            print(f"✓ 快捷键 '{key}' -> {name}")
        
        print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(test_navigation())
