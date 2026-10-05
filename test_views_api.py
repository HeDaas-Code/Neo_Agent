"""测试所有视图的 API"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.client import AgentClient

async def test_all_views():
    client = AgentClient()
    await client.connect()
    
    print("=== 测试今日行程 API ===")
    try:
        result = await client.call("schedule.get_today_itinerary", {})
        print(f"✓ 今日行程: {result}")
    except Exception as e:
        print(f"✗ 今日行程失败: {e}")
    
    print("\n=== 测试场景池 API ===")
    try:
        result = await client.call("scene.list_pool", {})
        print(f"✓ 场景池: {result}")
    except Exception as e:
        print(f"✗ 场景池失败: {e}")
    
    print("\n=== 测试记忆搜索 API ===")
    try:
        result = await client.call("memory.search", {"query": "测试"})
        print(f"✓ 记忆搜索: {result}")
    except Exception as e:
        print(f"✗ 记忆搜索失败: {e}")
    
    print("\n=== 测试关系列表 API ===")
    try:
        result = await client.call("relationship.list_all", {})
        print(f"✓ 关系列表: {result}")
    except Exception as e:
        print(f"✗ 关系列表失败: {e}")
    
    print("\n=== 测试审计日志 API ===")
    try:
        result = await client.call("audit.list_recent", {"limit": 5})
        print(f"✓ 审计日志: {result}")
    except Exception as e:
        print(f"✗ 审计日志失败: {e}")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_all_views())
