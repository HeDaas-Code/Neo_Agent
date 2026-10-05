"""测试所有视图的数据加载"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentTUI

async def test_all_views():
    """测试所有视图"""
    app = NeoAgentTUI()
    
    views = [
        ("chat", "💬 对话"),
        ("itinerary", "📅 今日行程"),
        ("scenes", "🌍 场景池"),
        ("memory", "🧠 记忆与知识"),
        ("relationships", "💭 关系网络"),
        ("audit", "🔍 审计日志")
    ]
    
    async with app.run_test() as pilot:
        await pilot.pause(1.0)
        
        print("🧪 测试所有视图加载\n")
        
        for view_id, view_name in views:
            print(f"📋 测试视图: {view_name}")
            
            # 点击导航按钮
            await pilot.click(f"#nav_{view_id}")
            await pilot.pause(0.5)
            
            # 检查视图是否显示
            view = app.query_one(f"#view_{view_id}")
            is_visible = "hidden" not in view.classes
            
            if is_visible:
                print(f"  ✓ 视图已显示")
                print(f"  ✓ 当前视图ID: {app.current_view_id}")
            else:
                print(f"  ❌ 视图未显示")
            
            print()
        
        print("✅ 所有视图测试完成")

if __name__ == "__main__":
    asyncio.run(test_all_views())
