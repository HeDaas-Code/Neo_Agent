"""简化的 TUI 测试"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.app import NeoAgentApp

async def test_views():
    """测试所有视图"""
    app = NeoAgentApp()
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        print("✓ TUI 启动成功")
        
        # 直接测试 MainContent 的 switch_to 方法
        main_content = app.query_one("#main-content")
        
        views_to_test = [
            ("chat", "对话"),
            ("itinerary", "今日行程"),
            ("scenes", "场景池"),
            ("memory", "记忆与知识"),
            ("relationships", "关系网络"),
            ("audit", "审计日志"),
        ]
        
        for view_id, name in views_to_test:
            try:
                main_content.switch_to(view_id)
                await pilot.pause(0.2)
                
                # 触发视图的刷新
                current_view = main_content.views.get(view_id)
                if hasattr(current_view, 'on_mount'):
                    await current_view.on_mount()
                    await pilot.pause(0.3)
                
                print(f"✓ {name} 视图加载成功")
            except Exception as e:
                print(f"✗ {name} 视图失败: {e}")
        
        print("\n✓ 所有视图测试完成")

if __name__ == "__main__":
    asyncio.run(test_views())
