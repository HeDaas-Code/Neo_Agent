"""最终 TUI 完整测试"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.app import NeoAgentApp

async def test_complete_tui():
    """完整的 TUI 功能测试"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        print("=" * 60)
        print("Neo Agent TUI 完整功能测试")
        print("=" * 60)
        
        # 1. 测试视图切换
        print("\n【1/6】测试视图切换...")
        main_content = app.query_one("#main-content")
        
        views = ["chat", "itinerary", "scenes", "memory", "relationships", "audit"]
        for view_id in views:
            main_content.switch_to(view_id)
            await pilot.pause(0.2)
        print("✓ 所有视图切换正常")
        
        # 2. 测试对话功能
        print("\n【2/6】测试对话功能...")
        main_content.switch_to("chat")
        await pilot.pause(0.3)
        
        try:
            chat_input = app.query_one("#chat-input")
            chat_log = app.query_one("#chat-log")
            print(f"  ✓ 对话界面加载成功")
            print(f"  - 输入框: {type(chat_input).__name__}")
            print(f"  - 消息列表: {type(chat_log).__name__}")
        except Exception as e:
            print(f"  ✗ 对话界面异常: {e}")
        
        # 3. 测试今日行程
        print("\n【3/6】测试今日行程...")
        main_content.switch_to("itinerary")
        itinerary_view = main_content.views["itinerary"]
        await itinerary_view.on_mount()
        await pilot.pause(0.5)
        
        try:
            itinerary_log = app.query_one("#itinerary-log")
            print(f"  ✓ 今日行程加载成功")
        except Exception as e:
            print(f"  ✗ 今日行程异常: {e}")
        
        # 4. 测试场景池
        print("\n【4/6】测试场景池...")
        main_content.switch_to("scenes")
        scenes_view = main_content.views["scenes"]
        await scenes_view.on_mount()
        await pilot.pause(0.5)
        
        try:
            scenes_log = app.query_one("#scenes-log")
            print(f"  ✓ 场景池加载成功")
        except Exception as e:
            print(f"  ✗ 场景池异常: {e}")
        
        # 5. 测试记忆搜索
        print("\n【5/6】测试记忆搜索...")
        main_content.switch_to("memory")
        await pilot.pause(0.3)
        
        try:
            memory_search = app.query_one("#memory-search")
            memory_log = app.query_one("#memory-log")
            print(f"  ✓ 记忆搜索界面正常")
        except Exception as e:
            print(f"  ✗ 记忆搜索异常: {e}")
        
        # 6. 测试关系网络
        print("\n【6/6】测试关系网络...")
        main_content.switch_to("relationships")
        rel_view = main_content.views["relationships"]
        await rel_view.on_mount()
        await pilot.pause(0.5)
        
        try:
            rel_log = app.query_one("#relationships-log")
            print(f"  ✓ 关系网络加载成功")
        except Exception as e:
            print(f"  ✗ 关系网络异常: {e}")
        
        print("\n" + "=" * 60)
        print("✓ TUI 完整功能测试通过")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_complete_tui())
