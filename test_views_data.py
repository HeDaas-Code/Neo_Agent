"""测试视图数据加载"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.client import ServiceClient


async def test_all_views():
    """测试所有视图的数据加载"""
    client = ServiceClient()
    
    try:
        await client.connect()
        print("✓ 已连接到服务\n")
        
        # 1. 测试角色资料
        print("=== 1. 角色资料 ===")
        profile = await client.call("character.get_profile")
        print(f"角色名: {profile.get('name')}")
        print(f"年龄: {profile.get('age')}")
        print(f"性别: {profile.get('gender')}")
        print()
        
        # 2. 测试今日行程
        print("=== 2. 今日行程 ===")
        itinerary = await client.call("schedule.get_today_itinerary")
        print(f"行程数量: {len(itinerary)}")
        if itinerary:
            for item in itinerary[:3]:
                print(f"  - {item.get('time')}: {item.get('activity')}")
        else:
            print("  暂无行程")
        print()
        
        # 3. 测试场景池
        print("=== 3. 场景池 ===")
        scenes = await client.call("scene.list_pool")
        print(f"场景数量: {len(scenes)}")
        for scene in scenes:
            visited = "✓" if scene.get("visited") else "✗"
            print(f"  {visited} {scene.get('name')} ({scene.get('type')})")
        print()
        
        # 4. 测试当前场景
        print("=== 4. 当前场景 ===")
        current = await client.call("scene.get_current")
        loc = current.get("location", {})
        area = current.get("area", {})
        print(f"地点: {loc.get('name')}")
        print(f"区域: {area.get('name')}")
        print(f"描述: {current.get('description')}")
        print()
        
        # 5. 测试关系网络
        print("=== 5. 关系网络 ===")
        relationships = await client.call("relationship.list_all")
        print(f"关系数量: {len(relationships)}")
        for rel in relationships:
            print(f"  - {rel.get('entity')}: {rel.get('score')}分 ({rel.get('level')})")
        print()
        
        # 6. 测试记忆统计
        print("=== 6. 记忆统计 ===")
        stats = await client.call("memory.get_stats")
        print(f"总记忆数: {stats.get('total')}")
        print(f"近期记忆: {stats.get('recent_count')}")
        print()
        
        # 7. 测试对话历史
        print("=== 7. 对话历史 ===")
        history = await client.call("session.get_history", {"limit": 5})
        print(f"历史消息数: {len(history)}")
        for msg in history[-3:]:
            role = msg.get('role')
            content = msg.get('content')
            print(f"  [{role}]: {content[:50]}...")
        print()
        
        # 8. 测试审计日志
        print("=== 8. 审计日志 ===")
        logs = await client.call("audit.get_logs", {"filter": "all", "limit": 10})
        print(f"日志数量: {len(logs)}")
        for log in logs[:3]:
            print(f"  - {log.get('action')}: {log.get('result')}")
        print()
        
        # 9. 测试系统状态
        print("=== 9. 系统状态 ===")
        status = await client.call("system.get_status")
        print(f"运行状态: {status.get('uptime')}")
        print(f"场景worker: {status.get('scene_worker')}")
        print(f"角色已加载: {status.get('character_loaded')}")
        print(f"当前场景: {status.get('current_scene')}")
        print()
        
        print("✅ 所有视图数据测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_all_views())
