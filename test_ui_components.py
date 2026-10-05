"""测试 UI 组件结构"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_modals():
    """测试模态窗口组件"""
    from neo_agent.ui.v2.modals import (
        ConfigModal, SceneDetailModal, 
        ItineraryDetailModal, CommandPalette
    )
    
    print("✓ ConfigModal 导入成功")
    print("✓ SceneDetailModal 导入成功")
    print("✓ ItineraryDetailModal 导入成功")
    print("✓ CommandPalette 导入成功")
    
    # 测试实例化
    scene_data = {
        "location": "测试地点",
        "description": "测试描述",
        "areas": ["区域1", "区域2"],
        "objects": ["物体1", "物体2"]
    }
    modal = SceneDetailModal(scene_data)
    print("✓ SceneDetailModal 实例化成功")
    
    itinerary_data = {
        "time": "10:00",
        "activity": "测试活动",
        "location": "测试地点",
        "owner": "agent"
    }
    modal = ItineraryDetailModal(itinerary_data)
    print("✓ ItineraryDetailModal 实例化成功")

def test_views():
    """测试视图组件"""
    from neo_agent.ui.v2.views import (
        ChatView, ItineraryView, ScenePoolView,
        MemoryView, RelationshipView, AuditView
    )
    
    print("✓ ChatView 导入成功")
    print("✓ ItineraryView 导入成功")
    print("✓ ScenePoolView 导入成功")
    print("✓ MemoryView 导入成功")
    print("✓ RelationshipView 导入成功")
    print("✓ AuditView 导入成功")

def test_app():
    """测试主应用"""
    from neo_agent.ui.v2.app import NeoAgentTUI, NavigationItem, StatusBar, TopBar
    
    print("✓ NeoAgentTUI 导入成功")
    print("✓ NavigationItem 导入成功")
    print("✓ StatusBar 导入成功")
    print("✓ TopBar 导入成功")
    
    # 测试导航项
    nav = NavigationItem("测试", "🔍", "test", count=5)
    print(f"✓ NavigationItem 实例化成功: {nav.label}")

if __name__ == '__main__':
    print("=" * 60)
    print("UI 组件结构测试")
    print("=" * 60)
    
    print("\n1. 测试模态窗口...")
    test_modals()
    
    print("\n2. 测试视图组件...")
    test_views()
    
    print("\n3. 测试主应用...")
    test_app()
    
    print("\n" + "=" * 60)
    print("所有组件结构测试通过！")
    print("=" * 60)
