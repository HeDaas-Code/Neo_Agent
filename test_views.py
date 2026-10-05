"""测试各个视图的数据加载"""
import asyncio
from neo_agent.ui.v2.client import ServiceClient

async def test_all_views():
    """测试所有视图的数据加载"""
    client = ServiceClient()
    
    try:
        await client.connect()
        print("✓ 已连接到服务\n")
        
        # 测试角色信息
        print("=" * 60)
        print("测试角色信息")
        print("=" * 60)
        profile = await client.call("character.get_profile")
        print(f"角色名: {profile.get('name', 'N/A')}")
        print(f"年龄: {profile.get('age', 'N/A')}")
        print(f"性别: {profile.get('gender', 'N/A')}")
        
        # 测试会话上下文
        print("\n" + "=" * 60)
        print("测试会话上下文")
        print("=" * 60)
        context = await client.call("session.get_context")
        scene = context.get("current_scene", {})
        print(f"当前场景: {scene.get('location', {}).get('name', 'N/A')}")
        print(f"情绪: {context.get('emotion', {}).get('state', 'N/A')}")
        
        # 测试今日行程
        print("\n" + "=" * 60)
        print("测试今日行程")
        print("=" * 60)
        itinerary = await client.call("schedule.get_today_itinerary")
        if itinerary:
            print(f"共 {len(itinerary)} 个活动:")
            for item in itinerary[:3]:
                print(f"  - {item.get('time', 'N/A')}: {item.get('activity', 'N/A')}")
        else:
            print("暂无行程安排")
        
        # 测试场景池
        print("\n" + "=" * 60)
        print("测试场景池")
        print("=" * 60)
        scenes = await client.call("scene.list_pool")
        if scenes:
            print(f"共 {len(scenes)} 个场景:")
            for scene_item in scenes[:3]:
                print(f"  - {scene_item.get('name', 'N/A')}: {scene_item.get('description', 'N/A')[:30]}...")
        else:
            print("场景池为空")
        
        # 测试记忆搜索
        print("\n" + "=" * 60)
        print("测试记忆搜索")
        print("=" * 60)
        memory_results = await client.call("memory.search", {"query": ""})
        print(f"记忆条目数: {len(memory_results) if memory_results else 0}")
        
        # 测试记忆统计
        stats = await client.call("memory.get_stats")
        print(f"短期记忆: {stats.get('short_term', 0)}")
        print(f"长期记忆: {stats.get('long_term', 0)}")
        print(f"知识条目: {stats.get('knowledge', 0)}")
        
        # 测试关系列表
        print("\n" + "=" * 60)
        print("测试关系网络")
        print("=" * 60)
        relationships = await client.call("relationship.list_all")
        if relationships:
            print(f"共 {len(relationships)} 个关系:")
            for rel in relationships[:3]:
                print(f"  - {rel.get('entity', 'N/A')}: {rel.get('score', 0)} 分 ({rel.get('intimacy', 'N/A')})")
        else:
            print("暂无关系记录")
        
        # 测试审计日志
        print("\n" + "=" * 60)
        print("测试审计日志")
        print("=" * 60)
        logs = await client.call("audit.get_logs", {"filter": "all", "limit": 5})
        if logs:
            print(f"共 {len(logs)} 条日志:")
            for log in logs[:3]:
                print(f"  - [{log.get('risk_level', 'N/A')}] {log.get('action', 'N/A')}")
        else:
            print("暂无审计日志")
        
        # 测试对话历史
        print("\n" + "=" * 60)
        print("测试对话历史")
        print("=" * 60)
        history = await client.call("session.get_history", {"limit": 5})
        if history:
            print(f"共 {len(history)} 条对话:")
            for msg in history[:3]:
                role = msg.get('role', 'N/A')
                content = msg.get('content', '')
                print(f"  - {role}: {content[:40]}...")
        else:
            print("暂无对话历史")
        
        print("\n" + "=" * 60)
        print("✅ 所有视图数据测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_all_views())
