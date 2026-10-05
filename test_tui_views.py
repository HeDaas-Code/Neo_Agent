#!/usr/bin/env python3
"""测试 TUI 视图切换"""
import asyncio
from neo_agent.ui.v2.app_connected import NeoAgentApp

async def test_views():
    """测试视图创建"""
    from neo_agent.ui.v2.client import ServiceClient
    from neo_agent.ui.v2.views_connected import (
        ChatView, ItineraryView, ScenePoolView,
        MemoryView, RelationshipView, AuditView
    )
    
    client = ServiceClient()
    
    # 测试每个视图是否可以实例化
    views = {
        "chat": ChatView(client),
        "itinerary": ItineraryView(client),
        "scene": ScenePoolView(client),
        "memory": MemoryView(client),
        "relationship": RelationshipView(client),
        "audit": AuditView(client),
    }
    
    print("✓ 所有视图创建成功")
    
    # 检查 refresh 方法
    for name, view in views.items():
        if hasattr(view, 'refresh'):
            print(f"✓ {name} 有 refresh 方法")
        else:
            print(f"✗ {name} 缺少 refresh 方法")

if __name__ == "__main__":
    asyncio.run(test_views())
