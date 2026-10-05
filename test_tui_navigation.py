"""测试 TUI 导航功能"""
import asyncio
from neo_agent.ui.v2.client import ServiceClient


async def test_navigation():
    """测试视图切换和数据加载"""
    client = ServiceClient()
    
    print("连接到服务...")
    await client.connect()
    print("✓ 连接成功\n")
    
    # 测试获取角色信息
    print("测试获取角色信息...")
    profile = await client.call("character.get_profile")
    print(f"✓ 角色: {profile.get('name', '未知')}\n")
    
    # 测试获取场景信息
    print("测试获取当前场景...")
    scene = await client.call("scene.get_current")
    print(f"✓ 当前场景: {scene.get('location', '未知')}\n")
    
    # 测试场景池
    print("测试场景池...")
    scenes = await client.call("scene.list_pool")
    print(f"✓ 场景数量: {len(scenes) if scenes else 0}\n")
    
    # 测试今日行程
    print("测试今日行程...")
    itinerary = await client.call("schedule.get_today_itinerary")
    print(f"✓ 行程数量: {len(itinerary) if itinerary else 0}\n")
    
    # 测试关系网络
    print("测试关系网络...")
    relationships = await client.call("relationship.list_all")
    print(f"✓ 关系数量: {len(relationships) if relationships else 0}\n")
    
    # 测试对话
    print("测试发送消息...")
    response = await client.call("session.send_message", text="你好")
    print(f"✓ 回复: {response.get('reply', '无回复')[:50]}...\n")
    
    await client.disconnect()
    print("✓ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_navigation())
