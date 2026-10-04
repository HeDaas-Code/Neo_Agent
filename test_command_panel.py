"""测试命令面板"""
import asyncio

async def test_command_panel():
    from neo_agent.ui.v2.app import NeoAgentApp
    
    app = NeoAgentApp()
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        # 按 : 打开命令面板
        print("✓ 按 : 打开命令面板...")
        await pilot.press("colon")
        await pilot.pause(1.0)
        
        # 检查命令面板是否打开
        screens = app.screen_stack
        assert len(screens) == 2, "应该有2个屏幕"
        assert screens[-1].__class__.__name__ == "CommandPalette", "顶部应该是命令面板"
        print(f"✓ 命令面板已打开")
        
        # 检查输入框
        command_input = app.screen.query_one("#command-input")
        print(f"✓ 找到输入框: {command_input.id}")
        
        # 输入命令
        print("✓ 输入命令: config")
        command_input.value = "config"
        await pilot.pause(0.3)
        
        # 按 ESC 取消
        print("✓ 按 ESC 取消...")
        await pilot.press("escape")
        await pilot.pause(0.5)
        
        # 验证命令面板已关闭
        screens = app.screen_stack
        assert len(screens) == 1, "命令面板应该已关闭"
        print("✓ 命令面板已关闭")
        
        print("\n✓ 命令面板测试全部通过！")

if __name__ == "__main__":
    asyncio.run(test_command_panel())
