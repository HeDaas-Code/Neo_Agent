"""测试 TUI 交互功能"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.app import NeoAgentApp

async def test_chat_interaction():
    """测试对话交互"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        print("=== 测试对话功能 ===")
        
        # 切换到对话视图
        main_content = app.query_one("#main-content")
        main_content.switch_to("chat")
        await pilot.pause(0.5)
        
        # 获取输入框
        try:
            chat_input = app.query_one("#chat-input")
            print(f"✓ 找到对话输入框")
            
            # 输入消息
            chat_input.value = "你好，林依"
            await pilot.pause(0.2)
            
            # 模拟发送（按 Ctrl+Enter）
            await pilot.press("ctrl+j")  # Ctrl+J 是 Ctrl+Enter 的替代
            await pilot.pause(2.0)
            
            print("✓ 消息发送测试完成")
            
        except Exception as e:
            print(f"✗ 对话测试失败: {e}")
        
        print("\n=== 测试今日行程 ===")
        
        # 切换到今日行程视图
        main_content.switch_to("itinerary")
        await pilot.pause(0.5)
        
        try:
            itinerary_view = main_content.views["itinerary"]
            await itinerary_view.on_mount()
            await pilot.pause(0.5)
            
            # 检查是否显示了行程数据
            table = app.query_one("#itinerary-table")
            row_count = table.row_count
            print(f"✓ 行程表显示 {row_count} 条记录")
            
        except Exception as e:
            print(f"✗ 行程测试失败: {e}")
        
        print("\n=== 测试场景池 ===")
        
        # 切换到场景池视图
        main_content.switch_to("scenes")
        await pilot.pause(0.5)
        
        try:
            scenes_view = main_content.views["scenes"]
            await scenes_view.on_mount()
            await pilot.pause(0.5)
            
            # 检查场景列表
            container = app.query_one("#scenes-container")
            print(f"✓ 场景池视图加载成功")
            
        except Exception as e:
            print(f"✗ 场景池测试失败: {e}")
        
        print("\n✓ 所有交互测试完成")

if __name__ == "__main__":
    asyncio.run(test_chat_interaction())
